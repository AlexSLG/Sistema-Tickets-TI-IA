"""Utilidades comunes de los modelos: datos, vocabulario, semillas y métricas."""
import json
import random
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix, f1_score

RAIZ = Path(__file__).resolve().parents[2]
PROCESSED = RAIZ / "data" / "processed"
CATEGORIAS = ["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"]
PRIORIDADES = ["Baja", "Media", "Alta", "Crítica"]
IMPACTOS = ["Bajo", "Medio", "Alto"]
URGENCIAS = ["Baja", "Media", "Alta"]
SEMILLA = 42
MAX_LEN = 128
PAD, UNK = 0, 1


def fijar_semilla(s=SEMILLA):
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)


def cargar_split(nombre):
    df = pd.read_csv(PROCESSED / f"{nombre}.csv", keep_default_na=False)
    df["real"] = df["origen_etiqueta"] != "aumento"
    return df


def texto_ticket(df):
    """Título y descripción en un solo texto."""
    return (df["titulo"].astype(str) + " . " + df["descripcion"].astype(str)).tolist()


def tokenizar(texto):
    return re.findall(r"\w+", texto.lower())


class Vocabulario:
    def __init__(self, palabras):
        self.itos = ["<pad>", "<unk>"] + list(palabras)
        self.stoi = {w: i for i, w in enumerate(self.itos)}

    @classmethod
    def construir(cls, textos, min_freq=2, max_tam=12000):
        cuenta = Counter(w for t in textos for w in tokenizar(t))
        palabras = [w for w, n in cuenta.most_common(max_tam) if n >= min_freq]
        return cls(palabras)

    def codificar(self, texto, max_len=MAX_LEN):
        ids = [self.stoi.get(w, UNK) for w in tokenizar(texto)][:max_len]
        return ids or [UNK]

    def matriz(self, textos, max_len=MAX_LEN):
        """Devuelve (ids [N, max_len] rellenos con PAD, longitudes [N])."""
        X = np.zeros((len(textos), max_len), dtype=np.int64)
        L = np.zeros(len(textos), dtype=np.int64)
        for i, t in enumerate(textos):
            ids = self.codificar(t, max_len)
            X[i, :len(ids)] = ids
            L[i] = len(ids)
        return torch.from_numpy(X), torch.from_numpy(L)

    def guardar(self, ruta):
        Path(ruta).write_text(json.dumps(self.itos, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def cargar(cls, ruta):
        v = cls([])
        v.itos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        v.stoi = {w: i for i, w in enumerate(v.itos)}
        return v

    def __len__(self):
        return len(self.itos)


def metricas(y_real, y_pred, clases):
    """F1, precisión y recall por clase, F1 macro, exactitud y matriz de confusión."""
    idx = list(range(len(clases)))
    rep = classification_report(y_real, y_pred, labels=idx, target_names=clases, output_dict=True, zero_division=0)
    return {
        "f1_macro": float(rep["macro avg"]["f1-score"]),
        "exactitud": float(rep["accuracy"]) if "accuracy" in rep else float((np.asarray(y_real) == np.asarray(y_pred)).mean()),
        "por_clase": {c: {"precision": float(rep[c]["precision"]), "recall": float(rep[c]["recall"]), "f1": float(rep[c]["f1-score"]),
                          "soporte": int(rep[c]["support"])} for c in clases},
        "matriz_confusion": confusion_matrix(y_real, y_pred, labels=idx).tolist(),
    }


def guardar_json(obj, ruta):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    Path(ruta).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def pesos_clase(y, k, tope=3.0):
    cuenta = np.bincount(y, minlength=k).astype(float)
    w = len(y) / (k * np.maximum(cuenta, 1))
    return np.minimum(w / w.mean(), tope).astype(np.float32)
