"""Evaluación final de la versión activa: reports/metricas.json y reports/figuras/*.png.

Toma las métricas calculadas al entrenar (models/<versión>/metricas_*.json, siempre sobre test con tickets reales),
las agrega en un solo archivo, comprueba los criterios de aceptación del plan y dibuja matrices de confusión y curvas de pérdida.

Ejecutar:  python -m src.training.evaluar [--version v1]
"""
import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.models.comun import CATEGORIAS, PRIORIDADES, RAIZ, guardar_json
from src.training import registro

FIGURAS = RAIZ / "reports" / "figuras"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 110})
C_GRU, C_BASE, C_MLP, C_REGLA = "#0072B2", "#E69F00", "#009E73", "#999999"


def leer(d, nombre):
    return json.loads((d / nombre).read_text(encoding="utf-8"))


def matriz_confusion(m, clases, titulo, nombre):
    M = np.array(m, dtype=float)
    norm = M / np.maximum(M.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(clases)), clases, rotation=35, ha="right")
    ax.set_yticks(range(len(clases)), clases)
    for i in range(len(clases)):
        for j in range(len(clases)):
            ax.text(j, i, f"{int(M[i, j])}", ha="center", va="center", color="white" if norm[i, j] > 0.5 else "black", fontsize=9)
    ax.set_xlabel("predicho"); ax.set_ylabel("real"); ax.set_title(titulo)
    ax.spines[:].set_visible(False)
    fig.tight_layout(); fig.savefig(FIGURAS / nombre, bbox_inches="tight"); plt.close(fig)


def f1_por_clase(cat):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = np.arange(len(CATEGORIAS))
    for k, (nombre, color) in enumerate([("base", C_BASE), ("gru", C_GRU)]):
        v = [cat[nombre]["reales"]["por_clase"][c]["f1"] for c in CATEGORIAS]
        ax.bar(x + (k - 0.5) * 0.38, v, 0.38, label="modelo base (TF-IDF + LR)" if nombre == "base" else "GRU", color=color)
    ax.axhline(0.85, color="#555", ls="--", lw=1); ax.text(len(CATEGORIAS) - 0.5, 0.855, "umbral 0,85", ha="right", fontsize=8, color="#555")
    ax.set_xticks(x, CATEGORIAS); ax.set_ylim(0.6, 1.0); ax.set_ylabel("F1"); ax.set_title("F1 por categoría en test (tickets reales)")
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout(); fig.savefig(FIGURAS / "metricas_f1_categoria.png", bbox_inches="tight"); plt.close(fig)


def curvas(cat, pri, asi):
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.4))
    h = cat["gru"]["historial"]
    ax[0].plot([e["epoca"] for e in h], [e["loss_train"] for e in h], color=C_GRU, label="entrenamiento")
    ax[0].plot([e["epoca"] for e in h], [e["loss_val"] for e in h], color=C_BASE, label="validación")
    a2 = ax[0].twinx(); a2.plot([e["epoca"] for e in h], [e["f1_macro_val"] for e in h], color=C_MLP, ls="--", label="F1 macro val"); a2.set_ylabel("F1 macro (val)")
    a2.spines["right"].set_visible(True)
    ax[0].set_title("GRU: pérdida y F1 de validación"); ax[0].set_xlabel("época"); ax[0].set_ylabel("pérdida"); ax[0].legend(frameon=False, fontsize=8)
    h = pri["historial_mlp_completo"]
    ax[1].plot([e["epoca"] for e in h], [e["loss_train"] for e in h], color=C_MLP); ax[1].set_title("MLP de prioridad: pérdida de entrenamiento"); ax[1].set_xlabel("época")
    h = asi["historial"]
    ax[2].plot([e["epoca"] for e in h], [e["top1_val"] for e in h], color=C_GRU); ax[2].set_title("MLP de asignación: top-1 en validación"); ax[2].set_xlabel("época")
    fig.tight_layout(); fig.savefig(FIGURAS / "curvas_entrenamiento.png", bbox_inches="tight"); plt.close(fig)


def prioridad_comparacion(pri):
    nombres = [("regla: matriz impacto × urgencia", "matriz\nimpacto × urgencia", C_REGLA), ("mlp completo", "MLP\ncompleto", C_MLP),
               ("base: TF-IDF + LR (solo texto)", "TF-IDF + LR\n(solo texto)", C_BASE), ("mlp sin impacto/urgencia (texto)", "MLP sin\nimpacto/urgencia", C_GRU)]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    v = [pri[k]["reales"]["f1_macro"] for k, _, _ in nombres]
    ax.bar([n for _, n, _ in nombres], v, color=[c for _, _, c in nombres])
    for i, x in enumerate(v):
        ax.text(i, x + 0.01, f"{x:.3f}".replace(".", ","), ha="center", fontsize=9)
    ax.axhline(0.80, color="#555", ls="--", lw=1); ax.text(3.45, 0.81, "umbral 0,80", ha="right", fontsize=8, color="#555")
    ax.set_ylim(0, 1.05); ax.set_ylabel("F1 macro"); ax.set_title("Prioridad: el MLP depende de impacto y urgencia")
    fig.tight_layout(); fig.savefig(FIGURAS / "metricas_prioridad.png", bbox_inches="tight"); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None)
    a = ap.parse_args()
    reg = registro.cargar()
    version = a.version or reg["activa"]
    d = RAIZ / "models" / version
    cat, pri, asi, sim = (leer(d, f"metricas_{n}.json") for n in ("categoria", "prioridad", "asignacion", "similitud"))
    FIGURAS.mkdir(parents=True, exist_ok=True)
    matriz_confusion(cat["gru"]["reales"]["matriz_confusion"], CATEGORIAS, "Categoría · GRU (test, reales)", "cm_categoria_gru.png")
    matriz_confusion(cat["base"]["reales"]["matriz_confusion"], CATEGORIAS, "Categoría · modelo base (test, reales)", "cm_categoria_base.png")
    matriz_confusion(pri["mlp completo"]["reales"]["matriz_confusion"], PRIORIDADES, "Prioridad · MLP (test, reales)", "cm_prioridad_mlp.png")
    f1_por_clase(cat)
    curvas(cat, pri, asi)
    prioridad_comparacion(pri)

    gru, base, mlp = cat["gru"]["reales"], cat["base"]["reales"], pri["mlp completo"]["reales"]
    criterios = {
        "gru_f1_macro_ge_0.85": {"valor": gru["f1_macro"], "cumple": gru["f1_macro"] >= 0.85},
        "gru_mejor_que_base": {"valor": gru["f1_macro"] - base["f1_macro"], "cumple": gru["f1_macro"] > base["f1_macro"]},
        "mlp_prioridad_f1_macro_ge_0.80": {"valor": mlp["f1_macro"], "cumple": mlp["f1_macro"] >= 0.80},
        "mlp_prioridad_recall_critica_ge_0.85": {"valor": mlp["por_clase"]["Crítica"]["recall"], "cumple": mlp["por_clase"]["Crítica"]["recall"] >= 0.85},
        "asignacion_top1_ge_0.80": {"valor": asi["top1"], "cumple": asi["top1"] >= 0.80},
        "balanceo_sin_violaciones_de_limite": {"valor": asi["violaciones_de_limite_con_balanceo"], "cumple": asi["violaciones_de_limite_con_balanceo"] == 0},
        "similares_3_de_5_misma_categoria_muestra_30": {"valor": sim["casos_similares"]["muestra_30"]["criterio_3_de_5"],
                                                         "cumple": sim["casos_similares"]["muestra_30"]["criterio_3_de_5"] >= 0.6},
    }
    resumen = {"version": version, "evaluado_sobre": "test.csv, solo tickets reales", "criterios": criterios,
               "categoria": {"gru": {k: gru[k] for k in ("f1_macro", "exactitud", "por_clase")}, "base": {k: base[k] for k in ("f1_macro", "exactitud", "por_clase")},
                             "por_fuente_gru": cat["gru"]["por_fuente"], "por_fuente_base": cat["base"]["por_fuente"]},
               "prioridad": {k: {m: v["reales"][m] for m in ("f1_macro", "exactitud")} | {"recall_critica": v["reales"]["por_clase"]["Crítica"]["recall"]}
                             for k, v in pri.items() if k != "historial_mlp_completo"},
               "prioridad_por_clase_mlp": mlp["por_clase"],
               "asignacion": {k: v for k, v in asi.items() if k not in ("historial", "top1_por_categoria")} | {"top1_por_categoria": asi["top1_por_categoria"]},
               "similitud": {"casos_similares": sim["casos_similares"], "soluciones_rapidas": {k: v for k, v in sim["soluciones_rapidas"].items() if k != "leave_one_phrase_out"}
                             | {"leave_one_out_top1": sim["soluciones_rapidas"]["leave_one_phrase_out"]["exactitud_top1"]}}}
    guardar_json(resumen, RAIZ / "reports" / "metricas.json")
    for k, v in criterios.items():
        print(("CUMPLE   " if v["cumple"] else "NO CUMPLE"), k, round(v["valor"], 4))
    print("Escritos reports/metricas.json y", len(list(FIGURAS.glob('*.png'))), "figuras en reports/figuras")


if __name__ == "__main__":
    main()
