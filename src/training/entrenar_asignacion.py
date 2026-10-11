"""Entrena el MLP de asignación sobre data/processed/historial_asignaciones.csv y evalúa las reglas de balanceo.

Ejecutar:  python -m src.training.entrenar_asignacion [--modelos models/v1]
Escribe mlp_asignacion.pt, tiempos_medios.npy y metricas_asignacion.json.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.models.comun import CATEGORIAS, PRIORIDADES, PROCESSED, RAIZ, guardar_json
from src.models.mlp_asignacion import (aptitudes_matriz, balancear, entrenar_asignacion, features_batch, puntuar, tiempos_medios)


def preparar(h, ids, tecnicos, tiempos):
    cat = h["categoria"].map({c: i for i, c in enumerate(CATEGORIAS)}).to_numpy()
    pri = h["prioridad"].map({p: i for i, p in enumerate(PRIORIDADES)}).to_numpy()
    cargas = h[[f"carga_{i}" for i in ids]].to_numpy().astype(np.float32)
    y = h["tecnico_inicial"].map({t: i for i, t in enumerate(ids)}).to_numpy()
    X = features_batch(cat, pri, cargas, tecnicos["limite_carga"].to_numpy().astype(np.float32), aptitudes_matriz(tecnicos), tiempos)
    return X, y, cat, cargas


def entrenar_y_evaluar(directorio, historial=None, tecnicos=None, verbose=True):
    directorio = Path(directorio)
    tecnicos = pd.read_csv(PROCESSED / "tecnicos.csv") if tecnicos is None else tecnicos
    h = pd.read_csv(PROCESSED / "historial_asignaciones.csv") if historial is None else historial
    ids = tecnicos["id_tecnico"].tolist()
    limites = tecnicos["limite_carga"].to_numpy().astype(np.float32)
    apt = aptitudes_matriz(tecnicos)
    tr, va, te = (h[h["subconjunto"] == s].reset_index(drop=True) for s in ("train", "val", "test"))
    tiempos = tiempos_medios(tr, tecnicos)  # solo con el historial de entrenamiento
    np.save(directorio / "tiempos_medios.npy", tiempos)
    (Xtr, ytr, _, _), (Xva, yva, _, _), (Xte, yte, cat_te, car_te) = (preparar(d, ids, tecnicos, tiempos) for d in (tr, va, te))
    modelo, hist = entrenar_asignacion(Xtr, ytr, Xva, yva)
    torch.save({"estado": modelo.state_dict(), "n_entrada": Xtr.shape[-1]}, directorio / "mlp_asignacion.pt")

    P = puntuar(modelo, Xte)
    top1 = float((P.argmax(1) == yte).mean())
    top3 = float(np.mean([yte[i] in np.argsort(-P[i])[:3] for i in range(len(yte))]))
    # con reglas de balanceo
    elegidos = np.array([balancear(P[i], car_te[i], limites)[1] for i in range(len(yte))])
    top1_bal = float((elegidos == yte).mean())
    # propiedad: ningún técnico supera su límite si hay otro que no lo supera
    hay_libre = (car_te < limites[None, :]).any(axis=1)
    excede = car_te[np.arange(len(yte)), elegidos] >= limites[elegidos]
    viola = int((hay_libre & excede).sum())
    sin_balanceo_excede = int((hay_libre & (car_te[np.arange(len(yte)), P.argmax(1)] >= limites[P.argmax(1)])).sum())
    # referencias
    base_apt = float((np.argmax(apt[:, cat_te].T, axis=1) == yte).mean())  # el más apto, sin mirar la carga (empate: el primero)
    sat = ~hay_libre
    res = {
        "n_test": int(len(yte)), "top1": top1, "top3": top3, "top1_con_balanceo": top1_bal,
        "referencia_mas_apto_sin_carga": base_apt,
        "violaciones_de_limite_con_balanceo": viola, "violaciones_de_limite_sin_balanceo": sin_balanceo_excede,
        "casos_con_todos_saturados": int(sat.sum()),
        "top1_por_categoria": {c: float((P.argmax(1)[cat_te == i] == yte[cat_te == i]).mean()) for i, c in enumerate(CATEGORIAS)},
        "historial": hist,
    }
    guardar_json(res, directorio / "metricas_asignacion.json")
    if verbose:
        print(f"  asignación: top-1 {top1:.4f} · top-3 {top3:.4f} · con balanceo {top1_bal:.4f} · "
              f"violaciones de límite {viola} (sin balanceo: {sin_balanceo_excede}) · referencia 'más apto' {base_apt:.4f}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", default=str(RAIZ / "models" / "v1"))
    entrenar_y_evaluar(ap.parse_args().modelos)


if __name__ == "__main__":
    main()
