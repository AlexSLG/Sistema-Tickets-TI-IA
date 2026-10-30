"""Validación del conjunto de prueba escrito por el equipo (SCRUM-100 · HU35).

Comprueba columnas, valores de la taxonomía, vacíos, duplicados y que ningún ticket se solape con los datos de
entrenamiento, validación o prueba (similitud TF-IDF ≥ 0,88 contra data/processed/tickets.csv → se informa y se excluye).

Ejecutar:  python -m src.data.validar_prueba_equipo [--archivo data/prueba_equipo/tickets_equipo.csv]
Salida:    reports/prueba_equipo_validacion.md y data/prueba_equipo/tickets_equipo_validos.csv
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "data" / "prueba_equipo"
ARCHIVO = CARPETA / "tickets_equipo.csv"
VALIDOS = CARPETA / "tickets_equipo_validos.csv"
INFORME = RAIZ / "reports" / "prueba_equipo_validacion.md"
COLUMNAS = ["id", "titulo", "descripcion", "impacto", "urgencia", "usuarios_afectados", "categoria", "prioridad", "autor"]
VALORES = {
    "categoria": ["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"],
    "prioridad": ["Baja", "Media", "Alta", "Crítica"],
    "impacto": ["Bajo", "Medio", "Alto"],
    "urgencia": ["Baja", "Media", "Alta"],
}
UMBRAL_SOLAPAMIENTO = 0.88
MINIMO_TOTAL, MINIMO_POR_CATEGORIA, MINIMO_CRITICA = 60, 10, 10


def prioridad_matriz(impacto, urgencia):
    s = VALORES["impacto"].index(impacto) + VALORES["urgencia"].index(urgencia) + 2
    return "Baja" if s <= 3 else "Media" if s == 4 else "Alta" if s == 5 else "Crítica"


def _texto(df):
    return (df["titulo"].astype(str) + " . " + df["descripcion"].astype(str)).str.lower().tolist()


def solapamiento(df, referencia):
    """Máxima similitud TF-IDF (palabras 1–2) de cada ticket del equipo contra los tickets de referencia."""
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit(_texto(referencia) + _texto(df))
    R, Q = vec.transform(_texto(referencia)), vec.transform(_texto(df))
    sim = np.zeros(len(df))
    idx = np.zeros(len(df), dtype=int)
    for i in range(0, len(df), 200):
        S = (Q[i:i + 200] @ R.T).toarray()
        sim[i:i + 200], idx[i:i + 200] = S.max(1), S.argmax(1)
    return sim, idx


def validar(df, referencia=None):
    """Devuelve (tickets_válidos, informe). `informe` es un diccionario con errores (filas excluidas) y avisos."""
    errores, avisos = [], []
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        return df.iloc[0:0], {"errores": [f"Faltan columnas: {', '.join(faltan)}"], "avisos": [], "excluidos_solapamiento": [], "total": len(df)}
    df = df[COLUMNAS].copy()
    for c in ("id", "titulo", "descripcion", "impacto", "urgencia", "categoria", "prioridad", "autor"):
        df[c] = df[c].fillna("").astype(str).str.strip()
    malas = set()
    for i, r in df.iterrows():
        fila = f"fila {i + 2} ({r['id'] or 'sin id'})"
        vacios = [c for c in COLUMNAS if c != "autor" and str(r[c]).strip() in ("", "nan")]
        if vacios:
            errores.append(f"{fila}: campos vacíos: {', '.join(vacios)}")
            malas.add(i)
            continue
        for c, permitidos in VALORES.items():
            if r[c] not in permitidos:
                errores.append(f"{fila}: «{r[c]}» no es un valor válido de {c} ({', '.join(permitidos)})")
                malas.add(i)
        try:
            if int(float(r["usuarios_afectados"])) < 1:
                raise ValueError
        except (TypeError, ValueError):
            errores.append(f"{fila}: usuarios_afectados debe ser un entero ≥ 1")
            malas.add(i)
        if len(r["titulo"]) < 3 or len(r["descripcion"]) < 3:
            errores.append(f"{fila}: título o descripción demasiado cortos")
            malas.add(i)
        if not r["autor"]:
            avisos.append(f"{fila}: sin autor")
    for col, nombre in (("id", "id"), ("descripcion", "descripción")):
        dup = df[df[col].str.lower().duplicated(keep="first") & (df[col] != "")]
        for i, r in dup.iterrows():
            errores.append(f"fila {i + 2} ({r['id']}): {nombre} duplicado")
            malas.add(i)
    validos = df.drop(index=list(malas)).copy()
    validos["usuarios_afectados"] = validos["usuarios_afectados"].astype(float).astype(int)

    # prioridad frente a la matriz (solo informativo)
    fuera = [(r["id"], r["impacto"], r["urgencia"], r["prioridad"]) for _, r in validos.iterrows()
             if r["prioridad"] != prioridad_matriz(r["impacto"], r["urgencia"])]
    if fuera:
        avisos.append(f"{len(fuera)} tickets con prioridad distinta a la que da la matriz impacto × urgencia (se aceptan; son criterio del autor): "
                      + ", ".join(f"{i} ({a}+{b}→{p})" for i, a, b, p in fuera[:15]) + (" …" if len(fuera) > 15 else ""))

    # solapamiento con los datos del proyecto
    excluidos = []
    if referencia is not None and len(validos):
        sim, idx = solapamiento(validos, referencia)
        for (i, r), s, j in zip(validos.iterrows(), sim, idx):
            if s >= UMBRAL_SOLAPAMIENTO:
                excluidos.append({"id": r["id"], "similitud": round(float(s), 3), "parecido_a": str(referencia.iloc[j]["id"]),
                                  "texto": r["titulo"][:80]})
        validos = validos[sim < UMBRAL_SOLAPAMIENTO]
        avisos.append(f"Similitud máxima contra los datos del proyecto: mediana {np.median(sim):.2f}, máximo {sim.max():.2f}.")

    # cobertura
    n = len(validos)
    if n < MINIMO_TOTAL:
        avisos.append(f"Solo {n} tickets válidos; el mínimo acordado es {MINIMO_TOTAL}.")
    for c in VALORES["categoria"]:
        k = int((validos["categoria"] == c).sum())
        if k < MINIMO_POR_CATEGORIA:
            avisos.append(f"Categoría {c}: {k} tickets (mínimo {MINIMO_POR_CATEGORIA}).")
    k = int((validos["prioridad"] == "Crítica").sum())
    if k < MINIMO_CRITICA:
        avisos.append(f"Prioridad Crítica: {k} tickets (mínimo {MINIMO_CRITICA}).")
    return validos, {"errores": errores, "avisos": avisos, "excluidos_solapamiento": excluidos, "total": len(df)}


def informe_md(validos, inf, archivo):
    md = ["# Validación del conjunto de prueba del equipo", "", f"Archivo: `{Path(archivo).relative_to(RAIZ) if Path(archivo).is_relative_to(RAIZ) else archivo}`", "",
          f"- Filas leídas: **{inf['total']}**", f"- Tickets válidos para evaluar: **{len(validos)}**",
          f"- Filas con errores (excluidas): {len(inf['errores'])}", f"- Excluidos por solapamiento con los datos del proyecto (similitud ≥ {UMBRAL_SOLAPAMIENTO}): {len(inf['excluidos_solapamiento'])}", ""]
    if len(validos):
        md += ["## Distribución de los tickets válidos", "",
               "| Categoría | Tickets |", "|---|---:|"] + [f"| {c} | {int((validos['categoria'] == c).sum())} |" for c in VALORES["categoria"]] + [""]
        md += ["| Prioridad | Tickets |", "|---|---:|"] + [f"| {p} | {int((validos['prioridad'] == p).sum())} |" for p in VALORES["prioridad"]] + [""]
        md += ["| Autor | Tickets |", "|---|---:|"] + [f"| {a or '—'} | {k} |" for a, k in validos["autor"].value_counts().items()] + [""]
    if inf["errores"]:
        md += ["## Errores (filas excluidas)", ""] + [f"- {e}" for e in inf["errores"]] + [""]
    if inf["excluidos_solapamiento"]:
        md += ["## Excluidos por solapamiento", "", "| id | Similitud | Parecido a | Título |", "|---|---:|---|---|"]
        md += [f"| {e['id']} | {e['similitud']} | {e['parecido_a']} | {e['texto']} |" for e in inf["excluidos_solapamiento"]] + [""]
    if inf["avisos"]:
        md += ["## Avisos", ""] + [f"- {a}" for a in inf["avisos"]] + [""]
    return "\n".join(md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", default=str(ARCHIVO))
    a = ap.parse_args()
    if not Path(a.archivo).exists():
        INFORME.write_text("# Validación del conjunto de prueba del equipo\n\n**Pendiente:** todavía no existe "
                           "`data/prueba_equipo/tickets_equipo.csv`. Instrucciones en `data/prueba_equipo/LEEME.md`.\n", encoding="utf-8")
        print(f"No existe {a.archivo}. Instrucciones en data/prueba_equipo/LEEME.md")
        sys.exit(1)
    df = pd.read_csv(a.archivo, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    referencia = pd.read_csv(RAIZ / "data" / "processed" / "tickets.csv", keep_default_na=False, usecols=["id", "titulo", "descripcion"])
    validos, inf = validar(df, referencia)
    salida = VALIDOS if Path(a.archivo).resolve() == ARCHIVO.resolve() else Path(a.archivo).with_name(Path(a.archivo).stem + "_validos.csv")
    validos.to_csv(salida, index=False, encoding="utf-8")
    INFORME.write_text(informe_md(validos, inf, a.archivo), encoding="utf-8")
    print(f"{len(validos)} tickets válidos de {inf['total']}; {len(inf['errores'])} errores; {len(inf['excluidos_solapamiento'])} excluidos por solapamiento.")
    print(f"Informe: {INFORME.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
