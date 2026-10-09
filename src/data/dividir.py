"""Paso 5 · División estratificada 70/15/15 por grupo (semilla 42).

Cada `grupo` (un ticket real y sus variantes aumentadas) cae entero en un solo subconjunto, de modo que ninguna
variante aparece en un conjunto y su original en otro. Se estratifica por categoría y prioridad.
Salida: data/processed/train.csv, val.csv, test.csv y reports/division_resumen.md.

Ejecutar:  python -m src.data.dividir
"""
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

RAIZ = Path(__file__).resolve().parents[2]
PROCESSED = RAIZ / "data" / "processed"
SEMILLA = 42
PROPORCIONES = {"train": 0.70, "val": 0.15, "test": 0.15}


def asignar_grupos(df):
    """Reparte los grupos por estrato (categoría|prioridad) hacia el subconjunto con mayor déficit relativo."""
    rng = random.Random(SEMILLA)
    por_grupo = df.groupby("grupo").agg(categoria=("categoria", "first"), prioridad=("prioridad", "first"), n=("id", "size"))
    # los grupos deben ser homogéneos: las variantes heredan categoría y prioridad del original
    assert df.groupby("grupo")["categoria"].nunique().max() == 1 and df.groupby("grupo")["prioridad"].nunique().max() == 1
    asignacion = {}
    # ticket count global por split para compensar el redondeo entre estratos
    actual = {s: 0 for s in PROPORCIONES}
    total = por_grupo["n"].sum()
    for estrato, g in sorted(por_grupo.groupby(["categoria", "prioridad"]), key=lambda kv: len(kv[1])):
        grupos = list(g.index)
        rng.shuffle(grupos)
        grupos.sort(key=lambda k: -g.loc[k, "n"])  # primero los grupos grandes (variantes), luego los individuales
        objetivo = {s: g["n"].sum() * p for s, p in PROPORCIONES.items()}
        cur = {s: 0 for s in PROPORCIONES}
        for k in grupos:
            n = g.loc[k, "n"]
            # déficit relativo en el estrato; en empate manda el déficit global
            def deficit(s):
                return ((objetivo[s] - cur[s]) / objetivo[s], PROPORCIONES[s] * total - actual[s])
            s = max(PROPORCIONES, key=deficit)
            asignacion[k] = s
            cur[s] += n
            actual[s] += n
    return asignacion


def main():
    df = pd.read_csv(PROCESSED / "tickets.csv", keep_default_na=False)
    asign = asignar_grupos(df)
    df["subconjunto"] = df["grupo"].map(asign)
    partes = {s: df[df["subconjunto"] == s].drop(columns="subconjunto").sample(frac=1, random_state=SEMILLA) for s in PROPORCIONES}
    for s, p in partes.items():
        p.to_csv(PROCESSED / f"{s}.csv", index=False, encoding="utf-8")

    # --- comprobaciones
    grupos = {s: set(p["grupo"]) for s, p in partes.items()}
    solapes = {f"{a}∩{b}": len(grupos[a] & grupos[b]) for a, b in [("train", "val"), ("train", "test"), ("val", "test")]}
    assert all(v == 0 for v in solapes.values()), solapes
    ids = pd.concat([p["id"] for p in partes.values()])
    assert ids.is_unique and len(ids) == len(df)

    # parecido entre subconjuntos (informativo): fracción de val/test con un vecino en train de coseno ≥ 0.8
    tf = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit(df["descripcion"])
    Xtr = tf.transform(partes["train"]["descripcion"])
    vecinos = {}
    for s in ("val", "test"):
        reales = partes[s][partes[s]["origen_etiqueta"] != "aumento"]
        S = tf.transform(reales["descripcion"]) @ Xtr.T
        mx = np.asarray(S.max(axis=1).todense()).ravel()
        vecinos[s] = ((mx >= 0.8).mean(), (mx >= 0.9).mean(), len(reales))

    md = ["# División del conjunto (paso 5)", "",
          "División **70/15/15 por grupo**, estratificada por categoría y prioridad, semilla 42 (`src/data/dividir.py`).",
          "Un `grupo` reúne un ticket real y sus variantes aumentadas; cada grupo está completo en un solo subconjunto.", "",
          "## Tamaño", ""]
    filas = []
    for s, p in partes.items():
        filas.append((s, len(p), len(p) / len(df), int((p["origen_etiqueta"] != "aumento").sum()), int((p["origen_etiqueta"] == "aumento").sum()),
                      p["grupo"].nunique()))
    md += ["| Subconjunto | Tickets | % | Reales | Aumentados | Grupos |", "|---|---:|---:|---:|---:|---:|"]
    md += [f"| {s} | {n} | {pct:.1%} | {r} | {a} | {g} |" for s, n, pct, r, a, g in filas]
    md += ["", "## Categoría", "", pd.concat({s: p["categoria"].value_counts() for s, p in partes.items()}, axis=1)
           .fillna(0).astype(int).to_markdown(), "",
           "Porcentaje de cada categoría dentro de cada subconjunto:", "",
           (pd.concat({s: p["categoria"].value_counts(normalize=True) for s, p in partes.items()}, axis=1) * 100).round(1).to_markdown(), "",
           "## Prioridad", "", pd.concat({s: p["prioridad"].value_counts() for s, p in partes.items()}, axis=1)
           .reindex(["Baja", "Media", "Alta", "Crítica"]).fillna(0).astype(int).to_markdown(), "",
           (pd.concat({s: p["prioridad"].value_counts(normalize=True) for s, p in partes.items()}, axis=1)
            .reindex(["Baja", "Media", "Alta", "Crítica"]) * 100).round(1).to_markdown(), "",
           "## Comprobaciones", "",
           f"- Grupos compartidos entre subconjuntos: {solapes} (deben ser 0).",
           "- Ningún `id` está repetido y la unión de los tres subconjuntos es el conjunto completo.",
           f"- Tickets reales de val/test con un vecino en train de similitud TF-IDF ≥ 0,8: "
           f"val {vecinos['val'][0]:.1%}, test {vecinos['test'][0]:.1%} (≥ 0,9: val {vecinos['val'][1]:.1%}, test {vecinos['test'][1]:.1%}). "
           "Es parecido por plantilla, no repetición: los casi duplicados exactos ya se eliminaron en el paso 4 (umbral 0,88 dentro de la misma fuente).",
           "", "## Cómo evaluar", "",
           "Val y test contienen también variantes aumentadas (de los grupos que les tocaron). Para las métricas finales usa solo las filas con "
           "`origen_etiqueta != \"aumento\"`; `src/training/evaluar.py` hará ese filtrado y reportará además el resultado con todas las filas.", ""]
    (RAIZ / "reports" / "division_resumen.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
