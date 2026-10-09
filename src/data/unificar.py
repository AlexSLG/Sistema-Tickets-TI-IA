"""Paso 4 · Mapeo, depuración y unificación -> data/processed/tickets.csv

Une las cuatro fuentes con el esquema final, aplica las reglas de src/data/mapeo.py, depura
(duplicados, textos fuera de TI, sin etiqueta) y escribe reports/unificacion_resumen.md.
El aumento por retrotraducción (src/data/aumentar.py) se aplica después sobre este archivo.

Ejecutar:  python -m src.data.unificar
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from src.data.mapeo import (CATEGORIAS, PRIORIDAD_FUENTE, asignar_impacto_urgencia, categoria_por_reglas, es_ti,
                            normalizar, nuevo_rng, prioridad_critica, prioridad_matriz, puntaje_impacto,
                            puntaje_urgencia, usuarios_afectados, IMPACTOS, URGENCIAS)

RAIZ = Path(__file__).resolve().parents[2]
RAW, INTERIM, PROCESSED, REPORTS = (RAIZ / "data" / "raw", RAIZ / "data" / "interim",
                                    RAIZ / "data" / "processed", RAIZ / "reports")
UMBRAL_CASI_DUPLICADO = 0.88

# Mapeo directo de subcategorías de Dataset_ticket.xlsx (Internal Application se decide por texto: son permisos)
SUBCAT_A_CATEGORIA = {"CPU": "Hardware", "Disk": "Hardware", "Keyboard": "Hardware", "Memory": "Hardware",
                      "Monitor": "Hardware", "Mouse": "Hardware", "DHCP": "Red", "DNS": "Red", "IP Address": "Red",
                      "VPN": "Red", "Wireless": "Red", "Email": "Correo", "Antivirus": "Seguridad",
                      "Operating System": "Software", "DB2": "Software", "MS SQL Server": "Software",
                      "Oracle": "Software"}
TECH_A_CATEGORIA = {"software": "Software", "hardware": "Hardware", "network": "Red"}
# Revisión manual de las 18 filas "other" de tech-support: descripción (en) -> categoría o None (se descarta)
TECH_OTHER = {
    "Need assistance setting up advanced user permissions.": "Accesos",
    "Request for system access for new team member.": "Accesos",
    "Request for remote access setup.": "Red",
    "Request for account deletion for compliance.": "Accesos",
    "Requesting account deletion due to privacy concerns.": "Accesos",
    "Request for demo account.": None, "Inquiry about warranty coverage.": None,
    "Requesting product feature details.": None, "General inquiry about data privacy policies.": None,
    "Question about service level agreement.": None, "Inquiry about new product release timeline.": None,
    "Feedback on new support portal layout.": None, "Inquiry about GDPR compliance.": None,
    "Request for product documentation.": None, "Inquiry about security features.": None,
    "General feedback about support experience.": None, "Question about upgrade eligibility.": None,
}

# Normalizaciones de estilo detectadas en la revisión de la traducción (reports/calidad_traduccion.md)
NORMALIZACIONES = [
    (r"Estimado cliente de (?:atención|soporte)(?: al cliente)?", "Estimado equipo de soporte"),
    (r"[Mm]e estoy acercando para", "Me pongo en contacto para"),
    (r"(\w+)ónes\b", r"\1ones"),
    (r"\bse ha estrellado\b", "ha fallado"), (r"\bse estrelló\b", "falló"), (r"\bse estrella\b", "falla"),
    (r"\bse desploma\b", "se cae"),
    (r"\b[A-ZÁÉÍÓÚ]{3,}_\d\b", ""),
    (r"[ \t]+", " "), (r"\s*\n\s*", "\n"),
]


def limpiar_es(t):
    t = str(t)
    for pat, rep in NORMALIZACIONES:
        t = re.sub(pat, rep, t)
    return t.strip()


SALUDO = re.compile(r"^(?:estimad[oa]s?|hola|buenos|buenas|querid[oa]|saludos|a quien corresponda|atenci[oó]n al cliente|"
                    r"asistencia al cliente|servicio de atenci[oó]n al cliente|servicio al cliente|apoyo al cliente|soporte al cliente|"
                    r"equipo de (?:soporte|apoyo|atenci[oó]n)[^,\n]{0,30})[^,\n.:]{0,50}[,:.]?\s*", re.I)


def primera_oracion(t, maximo=110):
    t = t.strip()
    for _ in range(3):  # quita saludos encadenados ("Hola, atención al cliente, …")
        nuevo = SALUDO.sub("", t, count=1).strip()
        if nuevo == t or len(nuevo.split()) < 4:
            break
        t = nuevo
    o = re.split(r"(?<=[.!?:])\s+|\n", t.strip())[0].strip(" ,;")
    if len(o) > maximo:
        o = o[:maximo].rsplit(" ", 1)[0] + "…"
    return o


# ------------------------------------------------------------------ carga por fuente
def cargar_multilang():
    d = pd.read_csv(INTERIM / "multilang_traducido.csv", keep_default_na=False)
    filas = []
    for r in d.itertuples():
        desc = limpiar_es(r.cuerpo_es)
        titulo = limpiar_es(r.titulo_es) or primera_oracion(desc)
        orig = f"{r.subject}\n{r.body}".strip()
        filas.append(dict(id=f"ML-{r.id_fuente}", fuente="multilang", idioma_original=r.idioma, texto_original=orig,
                          titulo=titulo, descripcion=desc, solucion=limpiar_es(r.solucion_es),
                          etiquetas=[e for e in r.etiquetas.split("|") if e], prioridad_fuente=PRIORIDAD_FUENTE[r.priority],
                          categoria_fuente=None))
    return pd.DataFrame(filas)


def cargar_dataset_ticket():
    d = pd.read_csv(INTERIM / "dataset_ticket_traducido.csv", keep_default_na=False)
    filas = []
    for r in d.itertuples():
        desc = limpiar_es(r.texto_es)
        cat = SUBCAT_A_CATEGORIA.get(r.Subcategory, "")  # "" para Internal Application
        filas.append(dict(id=f"XL-{r.id_fuente}", fuente="dataset_ticket", idioma_original=r.idioma, texto_original=r.texto,
                          titulo=primera_oracion(desc), descripcion=desc, solucion="", etiquetas=[],
                          prioridad_fuente=None, categoria_fuente=cat, subcategoria=r.Subcategory))
    return pd.DataFrame(filas)


def cargar_tech_support():
    d = pd.read_csv(INTERIM / "tech_support_traducido.csv", keep_default_na=False)
    filas = []
    for r in d.itertuples():
        if r.issue_category == "other":
            cat = TECH_OTHER.get(r.issue_description)
            if cat is None:
                continue  # consulta comercial/administrativa, no es un ticket de TI
        else:
            cat = TECH_A_CATEGORIA[r.issue_category]
        desc = limpiar_es(r.descripcion_es)
        filas.append(dict(id=f"TS-{r.ticket_id}", fuente="tech_support", idioma_original="en", texto_original=r.issue_description,
                          titulo=primera_oracion(desc), descripcion=desc, solucion=limpiar_es(r.solucion_es), etiquetas=[],
                          prioridad_fuente=PRIORIDAD_FUENTE[r.priority], categoria_fuente=cat))
    return pd.DataFrame(filas)


def cargar_v1():
    d = pd.read_csv(RAW / "dataset_clean_es_812.csv", encoding="utf-8-sig")
    filas = []
    for r in d.itertuples():
        desc = limpiar_es(r.text)
        filas.append(dict(id=f"V1-{r.id}", fuente="v1", idioma_original="es", texto_original=r.text,
                          titulo=primera_oracion(desc), descripcion=desc, solucion="", etiquetas=[],
                          prioridad_fuente=PRIORIDAD_FUENTE[r.priority_original], categoria_fuente=None))
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ etiquetado
def etiquetar(df, rng):
    cats, origen_cat, prios, origen_prio, imp, urg, exc, usr, quedan = [], [], [], [], [], [], [], [], []
    descartes = {"fuera_de_TI": 0, "sin_etiqueta": 0}
    for r in df.itertuples():
        texto = f"{r.titulo}. {r.descripcion}"
        cat, _ = categoria_por_reglas(r.titulo, r.descripcion, r.etiquetas)
        if r.fuente == "tech_support":
            cat_final, o_cat = r.categoria_fuente, "fuente"
        elif r.fuente == "dataset_ticket" and isinstance(r.categoria_fuente, str) and r.categoria_fuente:
            cat_final, o_cat = r.categoria_fuente, "fuente"
        elif r.fuente == "dataset_ticket":  # Internal Application: peticiones de permisos y autorizaciones
            cat_final, o_cat = "Accesos", "fuente"
            if cat in ("Seguridad", "Correo", "Red"):
                cat_final, o_cat = cat, "regla"
        else:
            if not es_ti(r.titulo, r.descripcion, categoria_fuerte=cat in ("Seguridad", "Accesos", "Red", "Correo", "Hardware")):
                descartes["fuera_de_TI"] += 1
                quedan.append(False)
                cats.append(None); origen_cat.append(None); prios.append(None); origen_prio.append(None)
                imp.append(None); urg.append(None); exc.append(False); usr.append(None)
                continue
            if cat is None:
                cat = "Software"  # resto de fallos de aplicación (hay señal de TI pero ninguna específica)
            cat_final, o_cat = cat, "regla"

        # prioridad
        if r.prioridad_fuente:
            base, o_prio = r.prioridad_fuente, "fuente"
            if r.fuente in ("multilang", "v1"):
                nueva = prioridad_critica(texto, r.etiquetas, base)
                if nueva != base:
                    base, o_prio = nueva, "regla"
        else:  # sin prioridad en la fuente: matriz sobre el impacto y la urgencia que indica el texto
            i = IMPACTOS[int(np.clip(round(puntaje_impacto(texto)), 0, 2))]
            u = URGENCIAS[int(np.clip(round(puntaje_urgencia(texto)), 0, 2))]
            base, o_prio = prioridad_matriz(i, u), "regla"

        i, u, e = asignar_impacto_urgencia(texto, base, rng)
        cats.append(cat_final); origen_cat.append(o_cat); prios.append(base); origen_prio.append(o_prio)
        imp.append(i); urg.append(u); exc.append(e); usr.append(usuarios_afectados(texto, i, rng)); quedan.append(True)
    df = df.assign(categoria=cats, origen_categoria=origen_cat, prioridad=prios, origen_prioridad=origen_prio,
                   impacto=imp, urgencia=urg, excepcion_matriz=exc, usuarios_afectados=usr)
    return df[np.array(quedan)].copy(), descartes


# ------------------------------------------------------------------ depuración
def depurar(df):
    pasos = {}
    df = df.copy()
    df["_norm"] = (df["titulo"] + " " + df["descripcion"]).map(normalizar).str.replace(r"\W+", " ", regex=True).str.strip()
    # filas con muy poco texto
    n0 = len(df)
    df = df[df["descripcion"].str.split().str.len() >= 3]
    pasos["descripcion con menos de 3 palabras"] = n0 - len(df)
    # duplicados exactos
    rango = {"tech_support": 0, "multilang": 1, "dataset_ticket": 2, "v1": 3}
    df["_r"] = df["fuente"].map(rango)
    df = df.sort_values(["_r", "id"]).reset_index(drop=True)
    n0 = len(df)
    df = df.drop_duplicates("_norm").reset_index(drop=True)
    pasos["duplicados exactos"] = n0 - len(df)
    # casi duplicados: coseno TF-IDF (palabras 1-2) >= umbral; se conserva la fuente de mayor rango
    X = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit_transform(df["_norm"])
    quitar = np.zeros(len(df), bool)
    por_fuente = {"entre fuentes distintas": 0, "dentro de la misma fuente": 0}
    for ini in range(0, len(df), 1000):
        S = (X[ini:ini + 1000] @ X.T).tocsr()
        for k in range(S.shape[0]):
            i = ini + k
            if quitar[i]:
                continue
            fila = S.getrow(k)
            for j, s in zip(fila.indices, fila.data):
                if j > i and s >= UMBRAL_CASI_DUPLICADO and not quitar[j]:
                    quitar[j] = True
                    clave = "dentro de la misma fuente" if df.at[i, "fuente"] == df.at[j, "fuente"] else "entre fuentes distintas"
                    por_fuente[clave] += 1
    pasos["casi duplicados (coseno ≥ %.2f)" % UMBRAL_CASI_DUPLICADO] = int(quitar.sum())
    pasos["  de ellos, " + "entre fuentes distintas"] = por_fuente["entre fuentes distintas"]
    pasos["  de ellos, " + "dentro de la misma fuente"] = por_fuente["dentro de la misma fuente"]
    df = df[~quitar].drop(columns=["_norm", "_r"]).reset_index(drop=True)
    return df, pasos


def main():
    rng = nuevo_rng()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    partes = [cargar_multilang(), cargar_dataset_ticket(), cargar_tech_support(), cargar_v1()]
    bruto = pd.concat(partes, ignore_index=True)
    n_fuente = bruto["fuente"].value_counts().to_dict()
    etiquetado, descartes = etiquetar(bruto, rng)
    depurado, pasos = depurar(etiquetado)

    def origen(r):
        return "fuente" if (r.origen_categoria == "fuente" and r.origen_prioridad == "fuente") else "regla"

    depurado["origen_etiqueta"] = [origen(r) for r in depurado.itertuples()]
    depurado["grupo"] = depurado["id"]  # id del ticket original; el aumento por retrotraducción lo conserva
    cols = ["id", "fuente", "idioma_original", "texto_original", "titulo", "descripcion", "categoria", "prioridad",
            "impacto", "urgencia", "usuarios_afectados", "solucion", "origen_etiqueta", "origen_categoria",
            "origen_prioridad", "excepcion_matriz", "grupo"]
    depurado[cols].to_csv(PROCESSED / "tickets_base.csv", index=False, encoding="utf-8")

    # resumen
    f = depurado
    md = ["# Resumen de la unificación (paso 4)", "", "## Filas por etapa", "",
          f"- Entrada por fuente: {n_fuente}",
          f"- Descartadas por no ser de TI (sin ninguna señal técnica y con vocabulario comercial): {descartes['fuera_de_TI']}",
          "- Depuración:"] + [f"  - {k}: {v}" for k, v in pasos.items()] + [f"- **Tickets resultantes (antes del aumento): {len(f)}**", "",
          "## Distribución", "", "### Categoría × fuente", "", pd.crosstab(f.categoria, f.fuente, margins=True).to_markdown(), "",
          "### Prioridad", "", (f.prioridad.value_counts(normalize=True).reindex(["Baja", "Media", "Alta", "Crítica"]) * 100).round(1)
          .astype(str).add(" %").to_frame("porcentaje").to_markdown(), "",
          "### Prioridad × fuente", "", pd.crosstab(f.prioridad, f.fuente, margins=True).to_markdown(), "",
          "### Impacto × urgencia (cuenta)", "", pd.crosstab(f.impacto, f.urgencia).to_markdown(), "",
          f"Excepciones a la matriz impacto × urgencia: {f.excepcion_matriz.mean():.1%}", "",
          "### Origen de la etiqueta", "", f.origen_etiqueta.value_counts().to_frame("filas").to_markdown(), ""]
    (REPORTS / "unificacion_resumen.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
