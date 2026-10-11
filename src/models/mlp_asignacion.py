"""MLP de asignación: puntaje de adecuación por cada par (ticket, técnico) + reglas de balanceo de carga.

Entrada por par: [categoría (one-hot 6), prioridad (one-hot 4), aptitud del técnico en esa categoría / 5,
carga / límite, tiempo medio histórico del técnico en esa categoría / 24 h]  ->  64 -> 32 -> puntaje.
Se entrena como clasificación sobre los técnicos candidatos (softmax de los puntajes de los 8 pares de un ticket).
"""
import copy

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from src.models.comun import CATEGORIAS, PRIORIDADES, fijar_semilla

N_ENTRADA = len(CATEGORIAS) + len(PRIORIDADES) + 3
ESCALA_HORAS = 24.0


class MLPAsignacion(nn.Module):
    def __init__(self, n_entrada=N_ENTRADA):
        super().__init__()
        self.red = nn.Sequential(nn.Linear(n_entrada, 64), nn.ReLU(), nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, x):  # x: [B, técnicos, n_entrada] -> puntajes [B, técnicos]
        return self.red(x).squeeze(-1)


def aptitudes_matriz(tecnicos):
    """[técnicos, categorías] con la aptitud (1–5) de cada técnico en cada categoría."""
    return np.stack([tecnicos[f"aptitud_{c.lower()}"].to_numpy() for c in CATEGORIAS], axis=1).astype(np.float32)


def tiempos_medios(historial, tecnicos, global_h=None):
    """Tiempo medio de resolución (h) por técnico y categoría, a partir de un historial (solo entrenamiento)."""
    ids = tecnicos["id_tecnico"].tolist()
    g = historial.groupby(["tecnico", "categoria"])["tiempo_resolucion_h"].mean()
    base = float(historial["tiempo_resolucion_h"].mean()) if global_h is None else global_h
    return np.array([[g.get((t, c), base) for c in CATEGORIAS] for t in ids], dtype=np.float32)


def features_batch(cat_idx, prio_idx, cargas, limites, aptitudes, tiempos):
    """cat_idx, prio_idx: [B]; cargas: [B, T]; limites: [T]; aptitudes y tiempos: [T, C]. Devuelve [B, T, N_ENTRADA]."""
    B, T = cargas.shape
    cat = np.eye(len(CATEGORIAS), dtype=np.float32)[cat_idx]                       # [B, 6]
    pri = np.eye(len(PRIORIDADES), dtype=np.float32)[prio_idx]                     # [B, 4]
    X = np.zeros((B, T, N_ENTRADA), dtype=np.float32)
    X[:, :, :6] = cat[:, None, :]
    X[:, :, 6:10] = pri[:, None, :]
    X[:, :, 10] = aptitudes[:, cat_idx].T / 5.0                                    # [B, T]
    X[:, :, 11] = cargas / limites[None, :]
    X[:, :, 12] = tiempos[:, cat_idx].T / ESCALA_HORAS
    return X


def balancear(puntajes, cargas, limites):
    """Reglas de balanceo. Ordena los técnicos por puntaje; los que ya alcanzaron su límite pasan al final
    (entre ellos, el de menor ocupación primero). Devuelve la lista de índices en el orden de asignación y el
    índice elegido: el mejor puntaje que no supere su límite o, si todos están al límite, el de menor ocupación."""
    puntajes, cargas, limites = map(np.asarray, (puntajes, cargas, limites))
    saturado = cargas >= limites
    libres = [i for i in np.argsort(-puntajes) if not saturado[i]]
    llenos = sorted(np.where(saturado)[0], key=lambda i: (cargas[i] / limites[i], -puntajes[i]))
    orden = libres + llenos
    return orden, int(orden[0])


@torch.no_grad()
def puntuar(modelo, X):
    modelo.eval()
    return modelo(torch.from_numpy(X)).numpy()


def entrenar_asignacion(Xtr, ytr, Xva, yva, epocas=150, paciencia=15, lote=128, lr=2e-3, semilla=42):
    """Entropía cruzada sobre los técnicos candidatos; parada temprana por exactitud top-1 en validación."""
    fijar_semilla(semilla)
    modelo = MLPAsignacion(Xtr.shape[-1])
    opt = torch.optim.Adam(modelo.parameters(), lr=lr, weight_decay=1e-5)
    Xt, yt = torch.from_numpy(Xtr), torch.from_numpy(ytr.astype(np.int64))
    g = torch.Generator().manual_seed(semilla)
    mejor, estado, sin, hist = -1.0, None, 0, []
    for ep in range(1, epocas + 1):
        modelo.train()
        perm = torch.randperm(len(Xt), generator=g)
        tot = 0.0
        for i in range(0, len(perm), lote):
            b = perm[i:i + lote]
            opt.zero_grad()
            loss = nn.functional.cross_entropy(modelo(Xt[b]), yt[b])
            loss.backward()
            opt.step()
            tot += loss.item() * len(b)
        acc = float((puntuar(modelo, Xva).argmax(1) == yva).mean())
        hist.append({"epoca": ep, "loss_train": tot / len(Xt), "top1_val": acc})
        if acc > mejor:
            mejor, estado, sin = acc, copy.deepcopy(modelo.state_dict()), 0
        else:
            sin += 1
            if sin >= paciencia:
                break
    modelo.load_state_dict(estado)
    return modelo, hist
