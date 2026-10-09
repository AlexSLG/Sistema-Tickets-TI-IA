"""Paso 4 · Aumento por retrotraducción (es -> en -> es) de las categorías con menos de 600 tickets.

Lee data/processed/tickets_base.csv y escribe data/processed/tickets.csv. Las filas aumentadas conservan
las etiquetas del ticket real, llevan `origen_etiqueta = "aumento"` y el mismo `grupo` que el original:
la división train/val/test (paso 5) debe mantener cada grupo completo en un solo subconjunto.

Ejecutar (entorno con CUDA):  .venv-traduccion\\Scripts\\python -m src.data.aumentar
"""
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import MarianMTModel, MarianTokenizer

from src.data.traduccion import proteger, restaurar, trocear

RAIZ = Path(__file__).resolve().parents[2]
PROCESSED = RAIZ / "data" / "processed"
OBJETIVO_MINIMO = 600
MAX_VARIANTES_POR_TICKET = 4
PIVOTES = ["en", "de", "it", "en"]  # idioma intermedio de cada variante (más diversidad que usar solo inglés)
UMBRAL_PARECIDO = 0.88
SEMILLA = 42
MODELOS = {f"{a}-{b}": f"Helsinki-NLP/opus-mt-{a}-{b}" for a, b in
          [("es", "en"), ("en", "es"), ("es", "de"), ("de", "es"), ("es", "it"), ("it", "es")]}


class Modelo:
    def __init__(self, nombre, dispositivo):
        self.dispositivo = dispositivo
        self.tok = MarianTokenizer.from_pretrained(MODELOS[nombre])
        self.m = MarianMTModel.from_pretrained(MODELOS[nombre]).to(dispositivo).eval().half()

    @torch.inference_mode()
    def __call__(self, textos, lote=64, **gen):
        orden = sorted(range(len(textos)), key=lambda i: len(textos[i]))
        out = [None] * len(textos)
        for k in range(0, len(orden), lote):
            idx = orden[k:k + lote]
            enc = self.tok([textos[i] for i in idx], return_tensors="pt", padding=True, truncation=True,
                           max_length=256).to(self.dispositivo)
            res = self.tok.batch_decode(self.m.generate(**enc, max_new_tokens=300, **gen), skip_special_tokens=True)
            for i, t in zip(idx, res):
                out[i] = t
        return out


def retrotraducir(textos, es_en, en_es, semilla):
    """Cada texto se trocea en unidades; es->en con haz y en->es con muestreo (da variantes distintas)."""
    unidades, mapas, estructura = [], [], []
    for t in textos:
        piezas = trocear(t)
        estructura.append([])
        for u, sep in piezas:
            p, m = proteger(u)
            estructura[-1].append((len(unidades), sep))
            unidades.append(p)
            mapas.append(m)
    en = es_en(unidades, num_beams=4)
    torch.manual_seed(semilla)
    es = en_es(en, do_sample=True, top_p=0.92, temperature=0.9)
    res = []
    for est in estructura:
        partes = []
        for i, sep in est:
            tr, _ = restaurar(es[i], mapas[i])
            partes.append(tr + sep)
        res.append(re.sub(r"[ \t]+", " ", "".join(partes)).strip())
    return res


def similitud(a, b):
    ta, tb = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    return len(ta & tb) / max(1, len(ta | tb))


def main():
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    base = pd.read_csv(PROCESSED / "tickets_base.csv", keep_default_na=False)
    rng = np.random.default_rng(SEMILLA)
    modelos = {}

    def modelo(n):
        if n not in modelos:
            modelos[n] = Modelo(n, dispositivo)
        return modelos[n]

    nuevas, informe = [], []
    for cat, n in base["categoria"].value_counts().items():
        if n >= OBJETIVO_MINIMO:
            continue
        falta = OBJETIVO_MINIMO - n
        cand = base[(base["categoria"] == cat) & (base["descripcion"].str.split().str.len() >= 6)]
        por_ticket = min(MAX_VARIANTES_POR_TICKET, math.ceil(falta / len(cand)))
        generadas = []
        for k in range(por_ticket):
            ida, vuelta = modelo(f"es-{PIVOTES[k]}"), modelo(f"{PIVOTES[k]}-es")
            descs = retrotraducir(cand["descripcion"].tolist(), ida, vuelta, SEMILLA + k)
            titulos = retrotraducir(cand["titulo"].tolist(), ida, vuelta, SEMILLA + 100 + k)
            for r, d, t in zip(cand.itertuples(), descs, titulos):
                if 0.6 <= len(d.split()) / max(1, len(r.descripcion.split())) <= 1.6 and similitud(d, r.descripcion) < UMBRAL_PARECIDO:
                    fila = r._asdict()
                    fila.pop("Index")
                    fila.update(id=f"{r.id}-RT{k + 1}", titulo=t, descripcion=d, origen_etiqueta="aumento")
                    generadas.append(fila)
        generadas = pd.DataFrame(generadas)
        # variantes del mismo ticket que quedaron casi idénticas entre sí se descartan
        generadas = generadas.drop_duplicates(subset=["grupo", "descripcion"])
        if len(generadas) > falta:
            generadas = generadas.iloc[rng.permutation(len(generadas))[:falta]]
        nuevas.append(generadas)
        informe.append((cat, n, len(cand), por_ticket, len(generadas), n + len(generadas)))
        print(f"{cat}: {n} reales + {len(generadas)} aumentados = {n + len(generadas)}", flush=True)
    final = pd.concat([base] + nuevas, ignore_index=True) if nuevas else base
    final.to_csv(PROCESSED / "tickets.csv", index=False, encoding="utf-8")
    (RAIZ / "reports" / "aumento_resumen.md").write_text(
        "# Aumento por retrotraducción (paso 4)\n\n"
        "Retrotraducción con idioma intermedio inglés, alemán o italiano (MarianMT; ida con haz de 4, vuelta con muestreo top-p 0,92) "
        "de tickets **reales** de las categorías con menos de 600. Las variantes conservan las etiquetas del original, llevan "
        "`origen_etiqueta = aumento` y el mismo `grupo`. Se descartan las que cambian demasiado de longitud (fuera de 0,6–1,6×) "
        "o se parecen demasiado al original (Jaccard ≥ 0,88).\n\n"
        "| Categoría | Reales | Candidatos | Variantes por ticket | Aumentados | Total |\n|---|---:|---:|---:|---:|---:|\n"
        + "\n".join(f"| {c} | {n} | {k} | {p} | {a} | {t} |" for c, n, k, p, a, t in informe) + "\n", encoding="utf-8")
    print(final["categoria"].value_counts().to_dict(), len(final))


if __name__ == "__main__":
    main()
