"""Evaluación de la versión activa de los modelos sobre el conjunto de prueba del equipo (HU35 · SCRUM-100).

Lee data/prueba_equipo/tickets_equipo.csv, lo valida (src/data/validar_prueba_equipo.py) y mide:
  · categoría: F1 macro y por clase de la GRU y del modelo base (TF-IDF + regresión logística)
  · prioridad: F1 macro, F1 por clase y recall de Crítica del MLP (con la categoría predicha, como en el sistema)
  · soluciones rápidas sugeridas y una tabla de errores (texto, real, predicho, probabilidad)
y compara con los umbrales del Sprint 1 y con el resultado en test.csv.

Ejecutar:  python -m src.training.evaluar_prueba_equipo [--archivo …] [--version v1] [--sin-filtro-solapamiento]
Salida:    reports/evaluacion_prueba_equipo.md, reports/metricas_prueba_equipo.json, reports/figuras/cm_prueba_equipo.png
"""
import argparse
import json
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data import validar_prueba_equipo as vpe
from src.models.base import predecir_base
from src.models.comun import CATEGORIAS, PRIORIDADES, RAIZ, guardar_json, metricas
from src.training import registro

UMBRALES = {"categoria_f1_macro": 0.85, "prioridad_f1_macro": 0.80, "recall_critica": 0.85}
INFORME = RAIZ / "reports" / "evaluacion_prueba_equipo.md"
METRICAS = RAIZ / "reports" / "metricas_prueba_equipo.json"
FIGURA = RAIZ / "reports" / "figuras" / "cm_prueba_equipo.png"


def figura_confusion(m, clases, titulo, ruta):
    M = np.array(m, dtype=float)
    norm = M / np.maximum(M.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(clases)), clases, rotation=35, ha="right")
    ax.set_yticks(range(len(clases)), clases)
    for i in range(len(clases)):
        for j in range(len(clases)):
            ax.text(j, i, int(M[i, j]), ha="center", va="center", color="white" if norm[i, j] > 0.5 else "black", fontsize=9)
    ax.set_xlabel("predicho"); ax.set_ylabel("real (equipo)"); ax.set_title(titulo)
    fig.tight_layout(); fig.savefig(ruta, bbox_inches="tight", dpi=110); plt.close(fig)


def evaluar(df, version=None):
    """Evalúa una versión (por defecto la activa) sobre un DataFrame con el formato de la plantilla. Devuelve un diccionario."""
    from src.service.inferencia import Servicio
    version = version or registro.cargar()["activa"]
    s = Servicio(version)
    filas = []
    for r in df.itertuples():
        a = s.analizar(r.titulo, r.descripcion, r.impacto, r.urgencia, int(r.usuarios_afectados))
        filas.append({"id": r.id, "titulo": r.titulo, "categoria_real": r.categoria, "prioridad_real": r.prioridad,
                      "categoria_pred": a["clasificacion"]["categoria"], "prob_categoria": a["clasificacion"]["probabilidades"][a["clasificacion"]["categoria"]],
                      "prob_real": a["clasificacion"]["probabilidades"][r.categoria],
                      "prioridad_pred": a["prioridad"]["prioridad"], "solucion_rapida": a["solucion_rapida"]["problema"] if a["solucion_rapida"] else None,
                      "tiempo_ms": a["tiempo_ms"]})
    p = pd.DataFrame(filas)
    yc = p["categoria_real"].map(CATEGORIAS.index).to_numpy()
    yp = p["prioridad_real"].map(PRIORIDADES.index).to_numpy()
    res = {"version": version, "n": len(p),
           "categoria_gru": metricas(yc, p["categoria_pred"].map(CATEGORIAS.index).to_numpy(), CATEGORIAS),
           "prioridad_mlp": metricas(yp, p["prioridad_pred"].map(PRIORIDADES.index).to_numpy(), PRIORIDADES)}
    base = RAIZ / "models" / version / "base_categoria.joblib"
    if base.exists():
        vec, clf = joblib.load(base)
        res["categoria_base"] = metricas(yc, predecir_base(vec, clf, df), CATEGORIAS)
    # prioridad que daría la matriz impacto × urgencia (referencia)
    res["prioridad_matriz"] = metricas(yp, np.array([PRIORIDADES.index(vpe.prioridad_matriz(i, u)) for i, u in zip(df["impacto"], df["urgencia"])]), PRIORIDADES)
    res["soluciones_rapidas"] = {"sugeridas": int(p["solucion_rapida"].notna().sum()),
                                 "ejemplos": p[p["solucion_rapida"].notna()][["id", "titulo", "categoria_real", "solucion_rapida"]].head(15).to_dict("records")}
    res["tiempo_ms"] = {"mediana": float(p["tiempo_ms"].median()), "p95": float(p["tiempo_ms"].quantile(0.95)), "max": float(p["tiempo_ms"].max())}
    res["errores_categoria"] = p[p["categoria_real"] != p["categoria_pred"]].sort_values("prob_categoria", ascending=False)[
        ["id", "titulo", "categoria_real", "categoria_pred", "prob_categoria", "prob_real"]].to_dict("records")
    res["errores_prioridad"] = p[p["prioridad_real"] != p["prioridad_pred"]][["id", "titulo", "prioridad_real", "prioridad_pred"]].to_dict("records")
    return res


def comparacion_test(version):
    d = RAIZ / "models" / version
    cat = json.loads((d / "metricas_categoria.json").read_text(encoding="utf-8"))
    pri = json.loads((d / "metricas_prioridad.json").read_text(encoding="utf-8"))
    return {"categoria_gru": cat["gru"]["reales"]["f1_macro"], "categoria_base": cat["base"]["reales"]["f1_macro"],
            "prioridad_mlp": pri["mlp completo"]["reales"]["f1_macro"], "recall_critica": pri["mlp completo"]["reales"]["por_clase"]["Crítica"]["recall"]}


def informe(res, test, validacion):
    g, pm = res["categoria_gru"], res["prioridad_mlp"]
    rc = pm["por_clase"]["Crítica"]["recall"]
    f = lambda x: f"{x:.3f}".replace(".", ",")
    ok = lambda c: "cumple" if c else "**no cumple**"
    md = ["# Evaluación con el conjunto de prueba del equipo", "",
          f"Versión de los modelos: **{res['version']}** · tickets evaluados: **{res['n']}** (tras la validación: {validacion}).", "",
          "Tickets redactados a mano por el equipo, que los modelos no vieron al entrenar (se excluyeron los que se parecían a los datos del proyecto).", "",
          "## Resumen frente a los umbrales del Sprint 1", "",
          "| Métrica | Conjunto del equipo | test.csv | Umbral | |", "|---|---:|---:|---:|---|",
          f"| F1 macro categoría · GRU | {f(g['f1_macro'])} | {f(test['categoria_gru'])} | 0,85 | {ok(g['f1_macro'] >= 0.85)} |"]
    if "categoria_base" in res:
        md.append(f"| F1 macro categoría · modelo base | {f(res['categoria_base']['f1_macro'])} | {f(test['categoria_base'])} | (referencia) | |")
    md += [f"| F1 macro prioridad · MLP | {f(pm['f1_macro'])} | {f(test['prioridad_mlp'])} | 0,80 | {ok(pm['f1_macro'] >= 0.80)} |",
           f"| Recall de Crítica | {f(rc)} | {f(test['recall_critica'])} | 0,85 | {ok(rc >= 0.85)} |",
           f"| F1 macro prioridad · matriz impacto × urgencia | {f(res['prioridad_matriz']['f1_macro'])} | — | (referencia) | |", "",
           "## Categoría por clase (GRU)", "", "| Clase | n | Precisión | Recall | F1 |" + (" F1 base |" if "categoria_base" in res else ""),
           "|---|---:|---:|---:|---:|" + ("---:|" if "categoria_base" in res else "")]
    for c in CATEGORIAS:
        v = g["por_clase"][c]
        md.append(f"| {c} | {v['soporte']} | {f(v['precision'])} | {f(v['recall'])} | {f(v['f1'])} |" +
                  (f" {f(res['categoria_base']['por_clase'][c]['f1'])} |" if "categoria_base" in res else ""))
    md += ["", f"![Matriz de confusión](figuras/{FIGURA.name})", "", "## Prioridad por clase (MLP)", "", "| Clase | n | Precisión | Recall | F1 |", "|---|---:|---:|---:|---:|"]
    for c in PRIORIDADES:
        v = pm["por_clase"][c]
        md.append(f"| {c} | {v['soporte']} | {f(v['precision'])} | {f(v['recall'])} | {f(v['f1'])} |")
    sr = res["soluciones_rapidas"]
    md += ["", "## Soluciones rápidas", "", f"Se sugirió una solución rápida en **{sr['sugeridas']}** de {res['n']} tickets.", ""]
    md += [f"- {e['id']} · {e['titulo'][:70]} ({e['categoria_real']}) → «{e['solucion_rapida']}»" for e in sr["ejemplos"]]
    t = res["tiempo_ms"]
    md += ["", f"Tiempo de análisis: mediana {t['mediana']:.0f} ms, p95 {t['p95']:.0f} ms, máximo {t['max']:.0f} ms.", "",
           f"## Errores de categoría ({len(res['errores_categoria'])})", "", "| id | Texto | Real | Predicho | Prob. predicha | Prob. de la real |", "|---|---|---|---|---:|---:|"]
    md += [f"| {e['id']} | {e['titulo'][:70]} | {e['categoria_real']} | {e['categoria_pred']} | {f(e['prob_categoria'])} | {f(e['prob_real'])} |" for e in res["errores_categoria"]]
    md += ["", f"## Errores de prioridad ({len(res['errores_prioridad'])})", "", "| id | Texto | Real | Predicha |", "|---|---|---|---|"]
    md += [f"| {e['id']} | {e['titulo'][:70]} | {e['prioridad_real']} | {e['prioridad_pred']} |" for e in res["errores_prioridad"][:40]]
    return "\n".join(md) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", default=str(vpe.ARCHIVO))
    ap.add_argument("--version", default=None)
    ap.add_argument("--sin-filtro-solapamiento", action="store_true", help="no excluye tickets parecidos a los datos del proyecto (solo para probar el script)")
    ap.add_argument("--salida", default=None, help="carpeta alternativa para el informe (por defecto reports/)")
    a = ap.parse_args()
    if not Path(a.archivo).exists():
        print(f"No existe {a.archivo}: el equipo debe escribirlo (instrucciones en data/prueba_equipo/LEEME.md).")
        sys.exit(1)
    df = pd.read_csv(a.archivo, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    ref = None if a.sin_filtro_solapamiento else pd.read_csv(RAIZ / "data" / "processed" / "tickets.csv", keep_default_na=False, usecols=["id", "titulo", "descripcion"])
    validos, inf = vpe.validar(df, ref)
    if not len(validos):
        print("No hay tickets válidos para evaluar; revisa reports/prueba_equipo_validacion.md")
        sys.exit(1)
    res = evaluar(validos.reset_index(drop=True), a.version)
    test = comparacion_test(res["version"])
    salida = Path(a.salida) if a.salida else RAIZ / "reports"
    (salida / "figuras").mkdir(parents=True, exist_ok=True)
    figura_confusion(res["categoria_gru"]["matriz_confusion"], CATEGORIAS, "Categoría · conjunto del equipo", salida / "figuras" / FIGURA.name)
    guardar_json({**res, "test_csv": test, "umbrales": UMBRALES}, salida / METRICAS.name)
    (salida / INFORME.name).write_text(informe(res, test, f"{len(validos)} válidos de {inf['total']}"), encoding="utf-8")
    print(f"F1 categoría GRU {res['categoria_gru']['f1_macro']:.3f} · prioridad {res['prioridad_mlp']['f1_macro']:.3f} · "
          f"recall Crítica {res['prioridad_mlp']['por_clase']['Crítica']['recall']:.3f} · n={res['n']}")
    print(f"Informe: {(salida / INFORME.name)}")


if __name__ == "__main__":
    main()
