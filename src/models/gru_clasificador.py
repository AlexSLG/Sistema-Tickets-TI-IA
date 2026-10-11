"""GRU bidireccional para clasificar la categoría del ticket y generar su embedding (512 dimensiones).

Palabras -> Embedding -> GRU bidireccional -> pooling máximo + medio (embedding del ticket) -> Dropout -> Dense -> 6 clases.
"""
import copy
import time

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

from src.models.comun import CATEGORIAS, MAX_LEN, PAD, fijar_semilla, pesos_clase, texto_ticket


class GRUClasificador(nn.Module):
    def __init__(self, n_vocab, n_clases=len(CATEGORIAS), dim_emb=128, dim_oculta=128, capas=1, dropout=0.4):
        super().__init__()
        self.emb = nn.Embedding(n_vocab, dim_emb, padding_idx=PAD)
        self.drop_emb = nn.Dropout(0.25)
        self.gru = nn.GRU(dim_emb, dim_oculta, num_layers=capas, batch_first=True, bidirectional=True,
                          dropout=dropout if capas > 1 else 0.0)
        self.drop = nn.Dropout(dropout)
        self.salida = nn.Linear(4 * dim_oculta, n_clases)
        self.dim_embedding = 4 * dim_oculta

    def embedding(self, ids, longitudes):
        """Embedding del ticket: concatenación de max y media de los estados de la GRU (4 × dim_oculta)."""
        x = self.drop_emb(self.emb(ids))
        paq = pack_padded_sequence(x, longitudes.clamp(min=1).cpu(), batch_first=True, enforce_sorted=False)
        out, _ = self.gru(paq)
        out, _ = pad_packed_sequence(out, batch_first=True, total_length=ids.shape[1])
        mascara = (ids != PAD).unsqueeze(-1)
        maximo = out.masked_fill(~mascara, -1e9).max(dim=1).values
        media = (out * mascara).sum(dim=1) / mascara.sum(dim=1).clamp(min=1)
        return torch.cat([maximo, media], dim=1)

    def forward(self, ids, longitudes):
        return self.salida(self.drop(self.embedding(ids, longitudes)))


def lotes_por_longitud(L, lote, generador=None, mezclar=False):
    """Índices agrupados por longitud similar (menos relleno). En entrenamiento se mezclan los lotes."""
    n = len(L)
    if mezclar:
        perm = torch.randperm(n, generator=generador)
        grupos = [perm[i:i + lote * 20] for i in range(0, n, lote * 20)]
        grupos = [g[torch.argsort(L[g])] for g in grupos]
    else:
        grupos = [torch.argsort(L)]
    lotes = [g[i:i + lote] for g in grupos for i in range(0, len(g), lote)]
    if mezclar:
        orden = torch.randperm(len(lotes), generator=generador).tolist()
        lotes = [lotes[i] for i in orden]
    return lotes


@torch.no_grad()
def predecir(modelo, X, L, lote=256):
    modelo.eval()
    logits = torch.zeros(len(X), modelo.salida.out_features)
    embs = torch.zeros(len(X), modelo.dim_embedding)
    for b in lotes_por_longitud(L, lote):
        m = int(L[b].max())
        e = modelo.embedding(X[b][:, :m], L[b])
        embs[b] = e
        logits[b] = modelo.salida(e)
    return logits, embs


def entrenar_gru(vocab, train, val, epocas=30, paciencia=5, lote=64, lr=2e-3, dim_emb=128, dim_oculta=128, capas=1,
                 semilla=42, verbose=True, modelo_inicial=None):
    """Entrena con parada temprana sobre el F1 macro de validación (solo tickets reales). Devuelve (modelo, historial).
    Con `modelo_inicial` continúa el entrenamiento de esos pesos (reentrenamiento incremental)."""
    fijar_semilla(semilla)
    torch.set_num_threads(max(1, torch.get_num_threads()))
    idx = {c: i for i, c in enumerate(CATEGORIAS)}
    Xtr, Ltr = vocab.matriz(texto_ticket(train))
    Xva, Lva = vocab.matriz(texto_ticket(val))
    ytr = torch.tensor(train["categoria"].map(idx).to_numpy())
    yva = val["categoria"].map(idx).to_numpy()
    real = val["real"].to_numpy()
    modelo = modelo_inicial or GRUClasificador(len(vocab), dim_emb=dim_emb, dim_oculta=dim_oculta, capas=capas)
    perdida = nn.CrossEntropyLoss(weight=torch.tensor(pesos_clase(ytr.numpy(), len(CATEGORIAS))), label_smoothing=0.05)
    opt = torch.optim.Adam(modelo.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="max", factor=0.5, patience=2)
    g = torch.Generator().manual_seed(semilla)
    mejor, mejor_estado, sin_mejora = -1.0, None, 0
    historial = []
    for ep in range(1, epocas + 1):
        modelo.train()
        t0 = time.time()
        total = 0.0
        for b in lotes_por_longitud(Ltr, lote, g, mezclar=True):
            opt.zero_grad()
            loss = perdida(modelo(Xtr[b][:, :int(Ltr[b].max())], Ltr[b]), ytr[b])
            loss.backward()
            nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            opt.step()
            total += loss.item() * len(b)
        logits, _ = predecir(modelo, Xva, Lva)
        pred = logits.argmax(1).numpy()
        f1 = f1_score(yva[real], pred[real], average="macro")
        loss_val = float(nn.functional.cross_entropy(logits, torch.tensor(yva)))
        sched.step(f1)
        historial.append({"epoca": ep, "loss_train": total / len(Xtr), "loss_val": loss_val, "f1_macro_val": float(f1)})
        if verbose:
            print(f"  época {ep:2d} · loss {total / len(Xtr):.3f} · loss val {loss_val:.3f} · F1 macro val {f1:.4f} · {time.time() - t0:.0f}s", flush=True)
        if f1 > mejor:
            mejor, mejor_estado, sin_mejora = f1, copy.deepcopy(modelo.state_dict()), 0
        else:
            sin_mejora += 1
            if sin_mejora >= paciencia:
                break
    modelo.load_state_dict(mejor_estado)
    return modelo, historial
