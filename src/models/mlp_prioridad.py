"""MLP de prioridad: [embedding del ticket + categoría + impacto + urgencia + log(usuarios)] -> 256 -> 128 -> 4."""
import copy

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score

from src.models.comun import CATEGORIAS, IMPACTOS, PRIORIDADES, URGENCIAS, fijar_semilla, pesos_clase

LOG_MAX = np.log1p(1000.0)


def construir_features(df, emb, cat_probs=None, usar_embedding=True, usar_impacto_urgencia=True):
    """Matriz de entrada. `cat_probs` [N, 6] sustituye al one-hot de la categoría real (inferencia de extremo a extremo)."""
    partes = []
    if usar_embedding:
        partes.append(np.asarray(emb, dtype=np.float32))
    if cat_probs is None:
        cat = np.eye(len(CATEGORIAS), dtype=np.float32)[df["categoria"].map({c: i for i, c in enumerate(CATEGORIAS)}).to_numpy()]
    else:
        cat = np.asarray(cat_probs, dtype=np.float32)
    partes.append(cat)
    if usar_impacto_urgencia:
        partes.append(np.eye(3, dtype=np.float32)[df["impacto"].map({c: i for i, c in enumerate(IMPACTOS)}).to_numpy()])
        partes.append(np.eye(3, dtype=np.float32)[df["urgencia"].map({c: i for i, c in enumerate(URGENCIAS)}).to_numpy()])
    partes.append((np.log1p(df["usuarios_afectados"].astype(float).to_numpy()) / LOG_MAX).astype(np.float32)[:, None])
    return np.concatenate(partes, axis=1)


class MLPPrioridad(nn.Module):
    def __init__(self, n_entrada, dropout=0.3):
        super().__init__()
        self.red = nn.Sequential(nn.Linear(n_entrada, 256), nn.ReLU(), nn.Dropout(dropout),
                                 nn.Linear(256, 128), nn.ReLU(), nn.Dropout(dropout), nn.Linear(128, len(PRIORIDADES)))

    def forward(self, x):
        return self.red(x)


@torch.no_grad()
def predecir_proba(modelo, X):
    modelo.eval()
    return torch.softmax(modelo(torch.from_numpy(X)), dim=1).numpy()


def entrenar_mlp(Xtr, ytr, Xva, yva, real_va, epocas=200, paciencia=20, lote=128, lr=1e-3, semilla=42, dropout=0.3):
    """Pesos por clase y parada temprana sobre el F1 macro de validación (tickets reales)."""
    fijar_semilla(semilla)
    modelo = MLPPrioridad(Xtr.shape[1], dropout)
    perdida = nn.CrossEntropyLoss(weight=torch.tensor(pesos_clase(ytr, len(PRIORIDADES))))
    opt = torch.optim.Adam(modelo.parameters(), lr=lr, weight_decay=1e-4)
    Xt, yt = torch.from_numpy(Xtr), torch.from_numpy(ytr.astype(np.int64))
    g = torch.Generator().manual_seed(semilla)
    mejor, estado, sin = -1.0, None, 0
    hist = []
    for ep in range(1, epocas + 1):
        modelo.train()
        perm = torch.randperm(len(Xt), generator=g)
        tot = 0.0
        for i in range(0, len(perm), lote):
            b = perm[i:i + lote]
            opt.zero_grad()
            loss = perdida(modelo(Xt[b]), yt[b])
            loss.backward()
            opt.step()
            tot += loss.item() * len(b)
        pred = predecir_proba(modelo, Xva).argmax(1)
        f1 = f1_score(yva[real_va], pred[real_va], average="macro")
        hist.append({"epoca": ep, "loss_train": tot / len(Xt), "f1_macro_val": float(f1)})
        if f1 > mejor:
            mejor, estado, sin = f1, copy.deepcopy(modelo.state_dict()), 0
        else:
            sin += 1
            if sin >= paciencia:
                break
    modelo.load_state_dict(estado)
    return modelo, hist
