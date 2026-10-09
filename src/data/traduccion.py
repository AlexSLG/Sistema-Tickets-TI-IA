"""Paso 3b · Traducción en/de/it -> es con MarianMT (preprocesamiento, no parte del sistema).

- Trocea cada texto en unidades (párrafos/frases, ≤ ~60 palabras) y las traduce por lotes en GPU.
- Caché en disco por unidad (data/interim/traducciones_cache.parquet): si se corta, se reanuda.
- Marcadores como <name>, <tel_num>, <acc_num> se sustituyen por fichas (NAME_1…) y se restauran.
- Verifica que los términos técnicos (VPN, Outlook, Wi-Fi, DNS…) sobrevivan.

Ejecutar (entorno con CUDA):  .venv-traduccion\\Scripts\\python -m src.data.traduccion
Medir velocidad:               python -m src.data.traduccion --benchmark 100 --dispositivo cpu|cuda
"""
import argparse
import hashlib
import random
import re
import time
from pathlib import Path

import pandas as pd
import torch
from transformers import MarianMTModel, MarianTokenizer

RAIZ = Path(__file__).resolve().parents[2]
INTERIM = RAIZ / "data" / "interim"
CACHE = INTERIM / "traducciones_cache.parquet"
LOG = INTERIM / "progreso_traduccion.log"
MODELOS = {"en": "Helsinki-NLP/opus-mt-en-es", "de": "Helsinki-NLP/opus-mt-de-es",
           "it": "Helsinki-NLP/opus-mt-it-es"}
SEMILLA = 42
MAX_PALABRAS_UNIDAD = 30
TERMINOS = ["VPN", "Outlook", "Wi-Fi", "WiFi", "DNS", "DHCP", "Windows", "Excel", "Word", "Teams", "Zoom", "Office",
            "Active Directory", "SQL", "Oracle", "Linux", "Wireless", "Bluetooth", "USB", "BIOS", "SharePoint", "OneDrive"]

# fuente -> (archivo, columna de idioma, columnas a traducir)
FUENTES = {
    "multilang": ("multilang_filtrado.csv", {"subject": "titulo_es", "body": "cuerpo_es", "answer": "solucion_es"}),
    "dataset_ticket": ("dataset_ticket_filtrado.csv", {"texto": "texto_es"}),
    "tech_support": ("tech_support_filtrado.csv", {"issue_description": "descripcion_es", "resolution_notes": "solucion_es"}),
}


# ---------------------------------------------------------------- idioma por unidad
# La columna `language` de la fuente principal no es fiable (≈40 % de las filas "de" están en inglés),
# así que el idioma se decide por unidad con palabras vacías; en empate se usa el de la fila.
_SW = {
    "en": {"the", "and", "is", "to", "of", "in", "for", "with", "that", "we", "our", "have", "has", "are", "was", "this",
           "on", "be", "not", "my", "you", "your", "as", "from", "been", "by", "or", "an", "can", "please", "i"},
    "de": {"der", "die", "das", "und", "ist", "nicht", "ich", "wir", "mit", "für", "von", "zu", "den", "ein", "eine", "auf",
           "dem", "des", "sie", "es", "im", "bei", "wurde", "haben", "sind", "bitte", "um", "auch", "oder", "unsere", "mein", "in", "aus", "nach", "zum", "zur", "über", "wie", "was", "wenn", "dass", "kann", "können"},
    "it": {"il", "lo", "la", "le", "di", "che", "non", "per", "una", "sono", "con", "della", "mi", "ho", "mio", "sto", "del",
           "nel", "ma", "più", "è", "dei", "delle", "gli", "dal", "alla", "un", "al", "e", "come", "sul", "nella"},
}


_COMUNES = (_SW["en"] & _SW["de"]) | (_SW["en"] & _SW["it"]) | (_SW["de"] & _SW["it"])
_SW = {i: sw - _COMUNES for i, sw in _SW.items()}  # palabras ambiguas (in, an…) no cuentan


def idioma_unidad(unidad, idioma_fila):
    palabras = re.findall(r"[a-zäöüßàèéìòù]+", unidad.lower())
    puntaje = {i: sum(p in sw for p in palabras) for i, sw in _SW.items()}
    mejor = max(puntaje.values())
    if mejor == 0:  # sin palabras vacías (p. ej. títulos): alemán si hay diéresis/ß o compuestos largos
        if idioma_fila == "it":
            return "it"
        return "de" if re.search(r"[äöüß]", unidad.lower()) or any(len(p) >= 13 for p in palabras) else "en"
    candidatos = [i for i, v in puntaje.items() if v == mejor]
    return idioma_fila if idioma_fila in candidatos else candidatos[0]


def caso_oracion(u):
    """Pasa un título en Title Case a minúsculas (salvo siglas y nombres con mayúsculas internas):
    el modelo deja sin traducir los títulos escritos así."""
    out = []
    for i, w in enumerate(u.split()):
        mixto = any(ch.isupper() for ch in w[1:]) or any(ch.isdigit() for ch in w)
        out.append(w if mixto else (w[0].upper() + w[1:].lower() if i == 0 else w.lower()))
    return " ".join(out)


def pegar_espacios(t):
    """Arregla "frase.Otra" que a veces produce el modelo."""
    return re.sub(r"([a-záéíóúñ\)])([.!?;])([A-ZÁÉÍÓÚÑ¿¡])", r"\1\2 \3", t)


# ---------------------------------------------------------------- troceado y protección
def trocear(texto):
    """Devuelve lista de (unidad, separador_posterior). Separador: ' ' entre frases, '\\n' entre párrafos."""
    piezas = []
    parrafos = [p.strip() for p in texto.split("\n") if p.strip()]
    for i, p in enumerate(parrafos):
        frases = re.split(r"(?<=[.!?])\s+", p)
        actual, n = [], 0
        grupos = []
        for f in frases:
            w = len(f.split())
            if actual and n + w > MAX_PALABRAS_UNIDAD:
                grupos.append(" ".join(actual))
                actual, n = [], 0
            actual.append(f)
            n += w
        if actual:
            grupos.append(" ".join(actual))
        for j, g in enumerate(grupos):
            sep = "\n" if (j == len(grupos) - 1 and i < len(parrafos) - 1) else " "
            piezas.append((g, sep))
    return piezas


def proteger(unidad):
    """<name> -> NAME_1 ... Devuelve (texto_protegido, {ficha: etiqueta_original})."""
    mapa, cuentas = {}, {}

    def sustituir(m):
        base = re.sub(r"[^A-Za-z]", "", m.group(1)).upper() or "TAG"
        cuentas[base] = cuentas.get(base, 0) + 1
        ficha = f"{base}_{cuentas[base]}"
        mapa[ficha] = m.group(0)
        return ficha

    return re.sub(r"<([A-Za-z_\-]{2,20})>", sustituir, unidad), mapa


ALIAS = {"NAME": "NOMBRE"}  # el modelo a veces traduce la ficha


def restaurar(traduccion, mapa):
    perdidas = 0
    for ficha, original in mapa.items():
        base, num = ficha.rsplit("_", 1)
        patron = "|".join(re.escape(b + "_" + num) for b in (base, ALIAS.get(base, base)))
        nuevo, n = re.subn(rf"\b(?:{patron})\b", original, traduccion, flags=re.I)
        if n == 0:
            perdidas += 1
        traduccion = nuevo
    return traduccion, perdidas


def clave(idioma, unidad):
    return hashlib.sha1(f"{idioma}\x00{unidad}".encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- modelo
class Traductor:
    def __init__(self, idioma, dispositivo="cpu"):
        self.dispositivo = dispositivo
        self.tok = MarianTokenizer.from_pretrained(MODELOS[idioma])
        self.modelo = MarianMTModel.from_pretrained(MODELOS[idioma]).to(dispositivo).eval()
        if dispositivo == "cuda":
            self.modelo = self.modelo.half()

    @torch.inference_mode()
    def traducir_lote(self, textos):
        enc = self.tok(textos, return_tensors="pt", padding=True, truncation=True, max_length=256).to(self.dispositivo)
        gen = self.modelo.generate(**enc, num_beams=2, max_new_tokens=300)
        return self.tok.batch_decode(gen, skip_special_tokens=True)

    def traducir(self, textos, lote=16):
        orden = sorted(range(len(textos)), key=lambda i: len(textos[i]))
        salida = [None] * len(textos)
        for k in range(0, len(orden), lote):
            idx = orden[k:k + lote]
            for i, t in zip(idx, self.traducir_lote([textos[i] for i in idx])):
                salida[i] = t
        return salida


# ---------------------------------------------------------------- caché
def cargar_cache():
    if CACHE.exists():
        return pd.read_parquet(CACHE).set_index("clave")["traduccion"].to_dict()
    return {}


def guardar_cache(cache, idiomas):
    df = pd.DataFrame({"clave": list(cache), "traduccion": list(cache.values()),
                       "idioma": [idiomas.get(k, "") for k in cache]})
    tmp = CACHE.with_suffix(".tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(CACHE)


def log(msg):
    print(msg, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ---------------------------------------------------------------- pipeline completo
def traducir_todo(dispositivo="cuda", lote=64):
    INTERIM.mkdir(parents=True, exist_ok=True)
    tablas, trabajo = {}, {}  # trabajo: idioma -> {clave: unidad_protegida}
    for fuente, (archivo, cols) in FUENTES.items():
        df = pd.read_csv(INTERIM / archivo, keep_default_na=False)
        tablas[fuente] = df
        for col in cols:
            for idioma, texto in zip(df["idioma"], df[col].astype(str)):
                for unidad, _ in trocear(texto):
                    prot, _ = proteger(unidad)
                    iu = idioma_unidad(prot, idioma)
                    trabajo.setdefault(iu, {})[clave(iu, prot)] = prot

    cache = cargar_cache()
    idiomas_clave = {k: i for i, d in trabajo.items() for k in d}
    pendientes = {i: {k: u for k, u in d.items() if k not in cache} for i, d in trabajo.items()}
    total = sum(len(d) for d in trabajo.values())
    total_pend = sum(len(d) for d in pendientes.values())
    log(f"Unidades totales: {total} · en caché: {total - total_pend} · por traducir: {total_pend}")

    hechas, t0 = 0, time.perf_counter()
    for idioma, d in pendientes.items():
        if not d:
            continue
        trad = Traductor(idioma, dispositivo)
        claves = sorted(d, key=lambda k: len(d[k]))
        for n, k0 in enumerate(range(0, len(claves), lote)):
            ks = claves[k0:k0 + lote]
            for k, t in zip(ks, trad.traducir_lote([d[k] for k in ks])):
                cache[k] = t
            hechas += len(ks)
            if n % 10 == 0:
                dt = time.perf_counter() - t0
                eta = dt / hechas * (total_pend - hechas)
                log(f"[{idioma}] {hechas}/{total_pend} unidades ({hechas / total_pend:.0%}) · "
                    f"{hechas / dt:.1f} u/s · quedan ~{eta / 60:.1f} min")
            if n % 40 == 39:
                guardar_cache(cache, idiomas_clave)
        guardar_cache(cache, idiomas_clave)
        del trad
        torch.cuda.empty_cache()
    log(f"Traducción terminada en {(time.perf_counter() - t0) / 60:.1f} min")

    # reparación 1: unidades que el modelo devolvió idénticas (títulos en Title Case o idioma mal detectado).
    # Intento 1: mismo idioma con el texto en minúsculas; intento 2: el otro idioma (en <-> de).
    iguales = {k: u for d in trabajo.values() for k, u in d.items()
               if cache[k].strip().lower() == u.strip().lower() and len(u.split()) >= 1 and len(u) >= 4}
    log(f"Unidades devueltas sin cambios: {len(iguales)}; reintentando")
    intentos = [lambda k: (idiomas_clave[k], caso_oracion(iguales[k]) if idiomas_clave[k] != "de" else iguales[k]),
                lambda k: ("de", iguales[k]) if idiomas_clave[k] != "de" else ("en", caso_oracion(iguales[k]))]
    for intento in intentos:
        plan = {}
        for k in list(iguales):
            idioma, texto = intento(k)
            plan.setdefault(idioma, []).append((k, texto))
        for idioma, items in plan.items():
            trad = Traductor(idioma, dispositivo)
            for i in range(0, len(items), lote):
                lote_i = items[i:i + lote]
                for (k, _), t in zip(lote_i, trad.traducir_lote([x for _, x in lote_i])):
                    if t.strip().lower() != iguales[k].strip().lower():
                        cache[k] = t
                        iguales.pop(k)
            del trad
    log(f"Quedan sin traducir {len(iguales)} (nombres de producto, siglas…)")
    guardar_cache(cache, idiomas_clave)

    # reparación: si el modelo omitió una frase, se retraduce frase por frase
    reparar = {}
    for k, u in ((k, u) for d in trabajo.values() for k, u in d.items()):
        tr = cache[k]
        if len(u.split()) >= 8 and len(tr.split()) < 0.55 * len(u.split()):
            reparar.setdefault(idiomas_clave[k], {})[k] = u
    for idioma, d in reparar.items():
        trad = Traductor(idioma, dispositivo)
        for k, u in d.items():
            frases = [s for s in re.split(r"(?<=[.!?])\s+", u) if s.strip()]
            cache[k] = " ".join(trad.traducir_lote(frases)) if len(frases) > 1 else cache[k]
        del trad
    log(f"Unidades reparadas frase por frase: {sum(len(d) for d in reparar.values())}")
    guardar_cache(cache, idiomas_clave)

    # ensamblado
    perdidas_marcadores, terminos_perdidos, sin_traducir, posibles_omisiones = 0, {}, 0, 0
    for fuente, (archivo, cols) in FUENTES.items():
        df = tablas[fuente].copy()
        for col, nueva in cols.items():
            res = []
            for idioma, texto in zip(df["idioma"], df[col].astype(str)):
                partes = []
                for unidad, sep in trocear(texto):
                    prot, mapa = proteger(unidad)
                    iu = idioma_unidad(prot, idioma)
                    tr = cache[clave(iu, prot)]
                    if tr.strip().lower() == prot.strip().lower() and len(prot.split()) >= 4:
                        sin_traducir += 1
                    if len(prot.split()) >= 8 and len(tr.split()) < 0.55 * len(prot.split()):
                        posibles_omisiones += 1
                    tr, p = restaurar(pegar_espacios(tr), mapa)
                    perdidas_marcadores += p
                    for term in TERMINOS:
                        if re.search(rf"\b{re.escape(term)}\b", unidad, flags=re.I) and \
                                not re.search(rf"\b{re.escape(term)}\b", tr, flags=re.I):
                            terminos_perdidos[term] = terminos_perdidos.get(term, 0) + 1
                    partes.append(tr + sep)
                res.append("".join(partes).strip())
            df[nueva] = res
        df.to_csv(INTERIM / f"{fuente}_traducido.csv", index=False, encoding="utf-8")
        log(f"Escrito data/interim/{fuente}_traducido.csv ({len(df)} filas)")
    log(f"Unidades sin traducir: {sin_traducir} · posibles omisiones (salida < 55 % de la entrada): {posibles_omisiones}")
    log(f"Marcadores perdidos: {perdidas_marcadores} · términos técnicos ausentes en la salida: {terminos_perdidos}")


# ---------------------------------------------------------------- benchmark
def benchmark(n, dispositivo, lote):
    df = pd.read_csv(INTERIM / "multilang_filtrado.csv", keep_default_na=False).sample(frac=1, random_state=SEMILLA)
    total_t = total_n = 0
    for idioma in ("en", "de"):
        textos = df[df["idioma"] == idioma]["body"].tolist()[: n // 2]
        t = Traductor(idioma, dispositivo)
        t.traducir(textos[:4], lote=4)
        t0 = time.perf_counter()
        t.traducir(textos, lote=lote)
        dt = time.perf_counter() - t0
        total_t += dt
        total_n += len(textos)
        print(f"{idioma}: {len(textos) / dt:.2f} textos/s")
    print(f"TOTAL {dispositivo}: {total_n / total_t:.2f} textos/s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", type=int, default=0)
    ap.add_argument("--dispositivo", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--lote", type=int, default=64)
    a = ap.parse_args()
    random.seed(SEMILLA)
    if a.benchmark:
        benchmark(a.benchmark, a.dispositivo, a.lote)
    else:
        traducir_todo(a.dispositivo, a.lote)
