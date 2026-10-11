"""Entrena el modelo base (TF-IDF + regresión logística) y la GRU de categoría; evalúa en test.

Ejecutar:  python -m src.training.entrenar_clasificador [--salida models/v1] [--epocas 30]
Escribe en <salida>: vocab.json, gru.pt, base_categoria.joblib, metricas_categoria.json
"""
import argparse
import time
from pathlib import Path

import joblib
import numpy as np
import torch

from src.models.base import entrenar_base, predecir_base
from src.models.comun import CATEGORIAS, RAIZ, Vocabulario, cargar_split, guardar_json, metricas, texto_ticket
from src.models.gru_clasificador import entrenar_gru, predecir


def evaluar_por_subconjuntos(y_idx, pred, df):
    """Métricas sobre tickets reales (las que cuentan), sobre todos y por fuente."""
    real = df["real"].to_numpy()
    res = {"reales": metricas(y_idx[real], pred[real], CATEGORIAS), "todos": metricas(y_idx, pred, CATEGORIAS), "por_fuente": {}}
    for f in sorted(df["fuente"].unique()):
        m = real & (df["fuente"] == f).to_numpy()
        if m.sum() >= 20:
            res["por_fuente"][f] = {"n": int(m.sum()), "exactitud": float((y_idx[m] == pred[m]).mean()),
                                    "f1_macro": metricas(y_idx[m], pred[m], CATEGORIAS)["f1_macro"]}
    return res


def entrenar_y_evaluar(train, val, test, salida, epocas=30, verbose=True, **kw_gru):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    idx = {c: i for i, c in enumerate(CATEGORIAS)}
    y_te = test["categoria"].map(idx).to_numpy()

    t0 = time.time()
    vec, clf, info_base = entrenar_base(train, val)
    pred_base = predecir_base(vec, clf, test)
    res = {"base": {"hiperparametros": info_base, **evaluar_por_subconjuntos(y_te, pred_base, test)}}
    joblib.dump((vec, clf), salida / "base_categoria.joblib")
    if verbose:
        print(f"Base TF-IDF + LR: F1 macro test (reales) {res['base']['reales']['f1_macro']:.4f} ({time.time() - t0:.0f}s)")

    vocab = Vocabulario.construir(texto_ticket(train))
    vocab.guardar(salida / "vocab.json")
    t0 = time.time()
    if verbose:
        print(f"GRU: vocabulario {len(vocab)} palabras")
    modelo, hist = entrenar_gru(vocab, train, val, epocas=epocas, verbose=verbose, **kw_gru)
    torch.save({"estado": modelo.state_dict(), "n_vocab": len(vocab), "dim_emb": kw_gru.get("dim_emb", 128),
                "dim_oculta": kw_gru.get("dim_oculta", 128), "capas": kw_gru.get("capas", 1)}, salida / "gru.pt")
    Xte, Lte = vocab.matriz(texto_ticket(test))
    logits, _ = predecir(modelo, Xte, Lte)
    pred_gru = logits.argmax(1).numpy()
    res["gru"] = {"entrenamiento_s": time.time() - t0, "historial": hist, **evaluar_por_subconjuntos(y_te, pred_gru, test)}
    if verbose:
        print(f"GRU: F1 macro test (reales) {res['gru']['reales']['f1_macro']:.4f} · todos {res['gru']['todos']['f1_macro']:.4f}")
    guardar_json(res, salida / "metricas_categoria.json")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(RAIZ / "models" / "v1"))
    ap.add_argument("--epocas", type=int, default=30)
    ap.add_argument("--dim_emb", type=int, default=128)
    ap.add_argument("--dim_oculta", type=int, default=128)
    ap.add_argument("--capas", type=int, default=1)
    ap.add_argument("--paciencia", type=int, default=5)
    a = ap.parse_args()
    entrenar_y_evaluar(cargar_split("train"), cargar_split("val"), cargar_split("test"), a.salida, a.epocas,
                       dim_emb=a.dim_emb, dim_oculta=a.dim_oculta, capas=a.capas, paciencia=a.paciencia)


if __name__ == "__main__":
    main()
