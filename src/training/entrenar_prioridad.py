"""Entrena el MLP de prioridad sobre los embeddings de la GRU y lo compara con referencias.

Ejecutar:  python -m src.training.entrenar_prioridad [--modelos models/v1]
Requiere haber ejecutado entrenar_clasificador (gru.pt y vocab.json). Escribe mlp_prioridad.pt y metricas_prioridad.json.
"""
import argparse
from pathlib import Path

import numpy as np
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from src.models.comun import CATEGORIAS, PRIORIDADES, RAIZ, SEMILLA, Vocabulario, cargar_split, guardar_json, metricas, texto_ticket
from src.models.gru_clasificador import GRUClasificador, predecir
from src.models.mlp_prioridad import construir_features, entrenar_mlp, predecir_proba
from src.models.base import entrenar_base
from src.models.comun import IMPACTOS, URGENCIAS

IDX = {p: i for i, p in enumerate(PRIORIDADES)}


def cargar_gru(directorio):
    directorio = Path(directorio)
    vocab = Vocabulario.cargar(directorio / "vocab.json")
    ck = torch.load(directorio / "gru.pt", map_location="cpu")
    m = GRUClasificador(ck["n_vocab"], dim_emb=ck["dim_emb"], dim_oculta=ck["dim_oculta"], capas=ck["capas"])
    m.load_state_dict(ck["estado"])
    m.eval()
    return vocab, m


def embeddings(vocab, gru, df):
    X, L = vocab.matriz(texto_ticket(df))
    logits, emb = predecir(gru, X, L)
    return emb.numpy(), torch.softmax(logits, 1).numpy()


def matriz_regla(df):
    """Prioridad que da la matriz impacto × urgencia (suma de niveles: 2-3 Baja, 4 Media, 5 Alta, 6 Crítica)."""
    s = df["impacto"].map({c: i for i, c in enumerate(IMPACTOS)}).to_numpy() + df["urgencia"].map({c: i for i, c in enumerate(URGENCIAS)}).to_numpy() + 2
    return np.where(s <= 3, 0, np.where(s == 4, 1, np.where(s == 5, 2, 3)))


def entrenar_y_evaluar(directorio, train, val, test, verbose=True):
    directorio = Path(directorio)
    vocab, gru = cargar_gru(directorio)
    (Etr, _), (Eva, _), (Ete, Pte) = (embeddings(vocab, gru, d) for d in (train, val, test))
    ytr, yva, yte = (d["prioridad"].map(IDX).to_numpy() for d in (train, val, test))
    real_va, real_te = val["real"].to_numpy(), test["real"].to_numpy()
    res = {}

    def evaluar(nombre, pred):
        res[nombre] = {"reales": metricas(yte[real_te], pred[real_te], PRIORIDADES), "todos": metricas(yte, pred, PRIORIDADES)}
        if verbose:
            r = res[nombre]["reales"]
            print(f"  {nombre:34s} F1 macro {r['f1_macro']:.4f} · exactitud {r['exactitud']:.4f} · recall Crítica {r['por_clase']['Crítica']['recall']:.3f}")

    # --- referencias
    evaluar("regla: matriz impacto × urgencia", matriz_regla(test))
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    Xtr_t, Xte_t = vec.fit_transform(texto_ticket(train)), vec.transform(texto_ticket(test))
    lr = LogisticRegression(C=10, class_weight="balanced", max_iter=3000, random_state=SEMILLA).fit(Xtr_t, ytr)
    evaluar("base: TF-IDF + LR (solo texto)", lr.predict(Xte_t))

    # --- MLP completo y ablaciones
    configuraciones = {
        "mlp completo": dict(usar_embedding=True, usar_impacto_urgencia=True),
        "mlp sin impacto/urgencia (texto)": dict(usar_embedding=True, usar_impacto_urgencia=False),
        "mlp sin embedding (tabular)": dict(usar_embedding=False, usar_impacto_urgencia=True),
    }
    modelos = {}
    for nombre, cfg in configuraciones.items():
        Xtr = construir_features(train, Etr, **cfg)
        Xva = construir_features(val, Eva, **cfg)
        Xte = construir_features(test, Ete, **cfg)
        mlp, hist = entrenar_mlp(Xtr, ytr, Xva, yva, real_va)
        modelos[nombre] = (mlp, hist, Xte.shape[1], cfg)
        evaluar(nombre, predecir_proba(mlp, Xte).argmax(1))
        if nombre == "mlp completo":
            # de extremo a extremo: la categoría llega como probabilidades de la GRU, no la etiqueta real
            Xte_e2e = construir_features(test, Ete, cat_probs=Pte, **cfg)
            evaluar("mlp completo (categoría predicha)", predecir_proba(mlp, Xte_e2e).argmax(1))
    mlp, hist, n_in, cfg = modelos["mlp completo"]
    torch.save({"estado": mlp.state_dict(), "n_entrada": n_in}, directorio / "mlp_prioridad.pt")
    res["historial_mlp_completo"] = hist
    guardar_json(res, directorio / "metricas_prioridad.json")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", default=str(RAIZ / "models" / "v1"))
    a = ap.parse_args()
    entrenar_y_evaluar(a.modelos, cargar_split("train"), cargar_split("val"), cargar_split("test"))


if __name__ == "__main__":
    main()
