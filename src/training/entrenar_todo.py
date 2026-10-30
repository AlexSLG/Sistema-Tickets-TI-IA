"""Entrena todos los modelos de una versión (categoría, prioridad, asignación, similitud) y la registra.

Ejecutar:  python -m src.training.entrenar_todo [--version v1] [--reutilizar-gru]
Con --reutilizar-gru no reentrena la GRU si ya existe models/<version>/gru.pt (solo los demás modelos e índices).
"""
import argparse
import json
from pathlib import Path

from src.models import catalogo_soluciones
from src.models.comun import PROCESSED, RAIZ, cargar_split, guardar_json
from src.training import entrenar_asignacion, entrenar_clasificador, entrenar_prioridad, entrenar_similitud, registro


def entrenar_todo(version, reutilizar_gru=False, epocas=40, nota="", activar=True, **kw_gru):
    d = RAIZ / "models" / version
    d.mkdir(parents=True, exist_ok=True)
    train, val, test = (cargar_split(s) for s in ("train", "val", "test"))
    if reutilizar_gru and (d / "gru.pt").exists() and (d / "metricas_categoria.json").exists():
        print(f"[{version}] se reutiliza la GRU existente")
    else:
        print(f"[{version}] 1/4 clasificador (base + GRU)")
        entrenar_clasificador.entrenar_y_evaluar(train, val, test, d, epocas, **kw_gru)
    print(f"[{version}] 2/4 MLP de prioridad")
    entrenar_prioridad.entrenar_y_evaluar(d, train, val, test)
    print(f"[{version}] 3/4 MLP de asignación")
    entrenar_asignacion.entrenar_y_evaluar(d)
    print(f"[{version}] 4/4 similitud y soluciones rápidas")
    soluciones = catalogo_soluciones.activas(catalogo_soluciones.leer())
    entrenar_similitud.construir_y_evaluar(d, train, val, soluciones)
    cfg_ruta = d / "config.json"
    cfg = json.loads(cfg_ruta.read_text(encoding="utf-8")) if cfg_ruta.exists() else {}
    import torch
    ck = torch.load(d / "gru.pt", map_location="cpu")
    cfg.update({"version": version, "max_len": 128, "gru": {"dim_emb": ck["dim_emb"], "dim_oculta": ck["dim_oculta"], "capas": ck["capas"]}})
    guardar_json(cfg, cfg_ruta)
    m = registro.resumen_metricas(d)
    registro.registrar(version, m, 0, "publicada", nota, activar=activar)
    print(f"[{version}] registrada: {m}")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    ap.add_argument("--reutilizar-gru", action="store_true")
    ap.add_argument("--epocas", type=int, default=40)
    ap.add_argument("--nota", default="Entrenamiento inicial sobre train.csv")
    a = ap.parse_args()
    entrenar_todo(a.version, a.reutilizar_gru, a.epocas, a.nota)


if __name__ == "__main__":
    main()
