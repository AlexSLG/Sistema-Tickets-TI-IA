"""Similitud entre tickets: casos similares (coseno entre embeddings de la GRU) y soluciones rápidas (híbrido con umbral).

Las soluciones rápidas combinan el coseno de los embeddings de la GRU con el coseno TF-IDF de caracteres (3–5-gramas),
porque el embedding de la GRU, entrenado para clasificar categorías, distingue mal problemas concretos de una misma categoría.
"""
import json
import unicodedata
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

UMBRAL_SOLUCION_RAPIDA = 0.70  # se recalibra en entrenar_similitud.py y se guarda en config.json
PESO_TFIDF = 0.7


def normalizar(E):
    E = np.asarray(E, dtype=np.float32)
    return E / np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-8)


def normalizar_texto(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    return "".join(c for c in t if not unicodedata.combining(c))


class IndiceTickets:
    """Índice de tickets ya atendidos (con su solución, si existe) para buscar casos similares."""

    def __init__(self, embeddings, meta):
        self.E = normalizar(embeddings)
        self.meta = meta.reset_index(drop=True)

    def buscar(self, emb, k=5, excluir_grupo=None):
        s = self.E @ normalizar(np.atleast_2d(emb))[0]
        if excluir_grupo is not None:
            s = np.where(self.meta["grupo"].to_numpy() == excluir_grupo, -2.0, s)
        idx = np.argsort(-s)[:k]
        return [{**self.meta.iloc[i].to_dict(), "similitud": float(s[i])} for i in idx]

    def guardar(self, directorio):
        directorio = Path(directorio)
        np.savez_compressed(directorio / "indice_tickets.npz", E=self.E.astype(np.float16))
        self.meta.to_csv(directorio / "indice_tickets_meta.csv", index=False, encoding="utf-8")

    @classmethod
    def cargar(cls, directorio):
        directorio = Path(directorio)
        E = np.load(directorio / "indice_tickets.npz")["E"].astype(np.float32)
        return cls(E, pd.read_csv(directorio / "indice_tickets_meta.csv", keep_default_na=False))


class SolucionesRapidas:
    """Índice de las `frases_ejemplo` (y del enunciado del problema) de soluciones_rapidas.json."""

    def __init__(self, soluciones, embeddings, ids, vectorizador, matriz_tfidf, umbral=UMBRAL_SOLUCION_RAPIDA, peso_tfidf=PESO_TFIDF):
        self.soluciones = {s["id"]: s for s in soluciones}
        self.E = normalizar(embeddings)
        self.ids = list(ids)
        self.vec = vectorizador
        self.T = matriz_tfidf
        self.umbral = umbral
        self.peso = peso_tfidf

    def similitudes(self, emb, texto):
        s_gru = self.E @ normalizar(np.atleast_2d(emb))[0]
        s_tf = (self.T @ self.vec.transform([normalizar_texto(texto)]).T).toarray().ravel()
        return self.peso * s_tf + (1 - self.peso) * s_gru

    def consultar(self, emb, texto, umbral=None):
        umbral = self.umbral if umbral is None else umbral
        s = self.similitudes(emb, texto)
        i = int(np.argmax(s))
        if s[i] < umbral:
            return None
        sol = self.soluciones[self.ids[i]]
        return {"id": sol["id"], "categoria": sol["categoria"], "problema": sol["problema"], "pasos": sol["pasos"], "similitud": float(s[i])}

    def guardar(self, directorio):
        directorio = Path(directorio)
        np.savez_compressed(directorio / "indice_soluciones.npz", E=self.E)
        (directorio / "indice_soluciones_ids.json").write_text(json.dumps(self.ids), encoding="utf-8")
        joblib.dump((self.vec, self.T), directorio / "indice_soluciones_tfidf.joblib")

    @classmethod
    def cargar(cls, directorio, soluciones, umbral=UMBRAL_SOLUCION_RAPIDA):
        directorio = Path(directorio)
        vec, T = joblib.load(directorio / "indice_soluciones_tfidf.joblib")
        return cls(soluciones, np.load(directorio / "indice_soluciones.npz")["E"],
                   json.loads((directorio / "indice_soluciones_ids.json").read_text(encoding="utf-8")), vec, T, umbral)
