"""Reentrenamiento con correcciones (aprendizaje continuo).

Une los datos de entrenamiento con data/correcciones.csv, reentrena a partir de los pesos de la versión vigente y la
evalúa contra un conjunto de referencia FIJO (test.csv, tickets reales). La versión nueva solo se publica si su F1 macro de
categoría iguala o supera al de la vigente; si no, se descarta y se registra. Cada versión queda en models/registry.json.

Ejecutar:  python -m src.training.reentrenar [--epocas 6]
"""
import argparse
import copy
import json
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.models.base import entrenar_base
from src.models.comun import CATEGORIAS, PRIORIDADES, PROCESSED, RAIZ, Vocabulario, cargar_split, guardar_json, texto_ticket
from src.models.gru_clasificador import entrenar_gru, predecir
from src.training import entrenar_asignacion, entrenar_clasificador, entrenar_prioridad, entrenar_similitud, registro
from src.training.entrenar_prioridad import cargar_gru

CORRECCIONES = RAIZ / "data" / "correcciones.csv"
COLUMNAS = ["titulo", "descripcion", "categoria_corregida", "prioridad_corregida", "tecnico_reasignado",
            "impacto", "urgencia", "usuarios_afectados", "fecha"]
PERFIL_PRIORIDAD = {"Baja": ("Bajo", "Media", 1), "Media": ("Medio", "Media", 10), "Alta": ("Alto", "Media", 100), "Crítica": ("Alto", "Alta", 100)}
PESO_CORRECCIONES = 3  # cada corrección se repite 3 veces en el entrenamiento (son pocas frente a miles de tickets)


def leer_correcciones():
    if not CORRECCIONES.exists():
        return pd.DataFrame(columns=COLUMNAS)
    df = pd.read_csv(CORRECCIONES, keep_default_na=False)
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = ""
    return df[COLUMNAS]


def correcciones_a_tickets(corr, repeticiones=PESO_CORRECCIONES):
    """Convierte las correcciones al formato de train.csv. Impacto, urgencia y usuarios, si faltan, se derivan de la prioridad."""
    filas = []
    for k, r in enumerate(corr.itertuples()):
        cat = r.categoria_corregida if r.categoria_corregida in CATEGORIAS else None
        pri = r.prioridad_corregida if r.prioridad_corregida in PRIORIDADES else None
        if cat is None or pri is None:
            continue  # sin ambas etiquetas la corrección no sirve para entrenar la GRU y el MLP de prioridad
        imp, urg, usu = PERFIL_PRIORIDAD[pri]
        filas.append({"id": f"CORR-{k + 1}", "fuente": "correccion", "idioma_original": "es", "texto_original": r.descripcion,
                      "titulo": r.titulo, "descripcion": r.descripcion, "categoria": cat, "prioridad": pri,
                      "impacto": r.impacto or imp, "urgencia": r.urgencia or urg,
                      "usuarios_afectados": int(r.usuarios_afectados) if str(r.usuarios_afectados).strip() else usu,
                      "solucion": "", "origen_etiqueta": "correccion", "grupo": f"CORR-{k + 1}", "real": True})
    base = pd.DataFrame(filas)
    return pd.concat([base] * repeticiones, ignore_index=True) if len(base) else base


def historial_con_correcciones(corr, tecnicos):
    """Añade al historial de entrenamiento las reasignaciones manuales (carga de referencia: 70 % del límite)."""
    h = pd.read_csv(PROCESSED / "historial_asignaciones.csv")
    ids = tecnicos["id_tecnico"].tolist()
    filas = []
    for r in corr.itertuples():
        if r.tecnico_reasignado not in ids or r.categoria_corregida not in CATEGORIAS or r.prioridad_corregida not in PRIORIDADES:
            continue
        fila = {"id_ticket": f"CORR-{len(filas) + 1}", "subconjunto": "train", "categoria": r.categoria_corregida,
                "prioridad": r.prioridad_corregida, "tecnico_inicial": r.tecnico_reasignado, "tecnico": r.tecnico_reasignado,
                "tiempo_resolucion_h": float(h["tiempo_resolucion_h"].median())}
        fila.update({f"carga_{t}": int(round(0.7 * lim)) for t, lim in zip(ids, tecnicos["limite_carga"])})
        filas.extend([fila] * PESO_CORRECCIONES)
    return pd.concat([h, pd.DataFrame(filas)], ignore_index=True) if filas else h


def f1_en_referencia(vocab, gru, test):
    X, L = vocab.matriz(texto_ticket(test))
    logits, _ = predecir(gru, X, L)
    pred = logits.argmax(1).numpy()
    y = test["categoria"].map({c: i for i, c in enumerate(CATEGORIAS)}).to_numpy()
    return entrenar_clasificador.evaluar_por_subconjuntos(y, pred, test)


def reentrenar(epocas=6, lr=5e-4, desde_cero=False, progreso=print):
    t0 = time.time()
    reg = registro.cargar()
    vig = registro.version_activa(reg)
    if vig is None:
        raise RuntimeError("No hay una versión activa en models/registry.json: ejecuta primero entrenar_todo.")
    corr = leer_correcciones()
    tickets_corr = correcciones_a_tickets(corr)
    if tickets_corr.empty:
        return {"publicada": False, "motivo": "No hay correcciones válidas en data/correcciones.csv (se necesitan categoría y prioridad corregidas).",
                "n_correcciones": len(corr)}
    n_validas = len(tickets_corr) // PESO_CORRECCIONES
    d_vig = RAIZ / vig["directorio"]
    train, val, test = (cargar_split(s) for s in ("train", "val", "test"))
    nuevo_train = pd.concat([train, tickets_corr.reindex(columns=train.columns)], ignore_index=True)
    vocab_v, gru_v = cargar_gru(d_vig)

    progreso(f"Versión vigente {vig['version']}: evaluando en el conjunto de referencia (test, tickets reales)…")
    ref_vig = f1_en_referencia(vocab_v, gru_v, test)
    f1_vig = ref_vig["reales"]["f1_macro"]

    version = registro.siguiente_version(reg)
    d = RAIZ / "models" / version
    d.mkdir(parents=True, exist_ok=True)
    try:
        progreso(f"Entrenando {version} con {len(train)} tickets + {n_validas} correcciones (×{PESO_CORRECCIONES}), {epocas} épocas máx.…")
        if desde_cero:
            vocab = Vocabulario.construir(texto_ticket(nuevo_train))
            ck = torch.load(d_vig / "gru.pt", map_location="cpu")
            modelo, hist = entrenar_gru(vocab, nuevo_train, val, epocas=epocas, paciencia=3, lr=1e-3,
                                        dim_emb=ck["dim_emb"], dim_oculta=ck["dim_oculta"], capas=ck["capas"], verbose=False)
        else:
            vocab = vocab_v
            modelo, hist = entrenar_gru(vocab, nuevo_train, val, epocas=epocas, paciencia=3, lr=lr, verbose=False,
                                        modelo_inicial=copy.deepcopy(gru_v))
        ref_nueva = f1_en_referencia(vocab, modelo, test)
        f1_nueva = ref_nueva["reales"]["f1_macro"]
        publicar = f1_nueva >= f1_vig
        comparacion = {"vigente": {"version": vig["version"], "f1_macro": f1_vig}, "nueva": {"version": version, "f1_macro": f1_nueva},
                       "diferencia": f1_nueva - f1_vig, "n_correcciones": n_validas, "referencia": "test.csv (tickets reales)",
                       "recall_por_clase_vigente": {c: ref_vig["reales"]["por_clase"][c]["recall"] for c in CATEGORIAS},
                       "recall_por_clase_nueva": {c: ref_nueva["reales"]["por_clase"][c]["recall"] for c in CATEGORIAS}}
        if not publicar:
            shutil.rmtree(d, ignore_errors=True)
            registro.registrar(version, {"f1_macro_categoria_gru": f1_nueva, "f1_referencia_vigente": f1_vig}, n_validas, "descartada",
                               f"F1 macro {f1_nueva:.4f} < vigente {f1_vig:.4f}: no se publica.")
            progreso(f"{version} descartada: F1 macro {f1_nueva:.4f} < {f1_vig:.4f} de {vig['version']}.")
            return {**comparacion, "publicada": False, "motivo": f"La versión nueva empeora el F1 macro ({f1_nueva:.4f} frente a {f1_vig:.4f}); se descarta.",
                    "segundos": time.time() - t0}

        progreso(f"{version} publicable (F1 macro {f1_nueva:.4f} ≥ {f1_vig:.4f}). Reentrenando MLP de prioridad, asignación e índices…")
        vocab.guardar(d / "vocab.json")
        ck = torch.load(d_vig / "gru.pt", map_location="cpu")
        torch.save({"estado": modelo.state_dict(), "n_vocab": len(vocab), "dim_emb": ck["dim_emb"], "dim_oculta": ck["dim_oculta"],
                    "capas": ck["capas"]}, d / "gru.pt")
        vec, clf, info = entrenar_base(nuevo_train, val)
        import joblib
        joblib.dump((vec, clf), d / "base_categoria.joblib")
        from src.models.base import predecir_base
        y_te = test["categoria"].map({c: i for i, c in enumerate(CATEGORIAS)}).to_numpy()
        guardar_json({"base": {"hiperparametros": info, **entrenar_clasificador.evaluar_por_subconjuntos(y_te, predecir_base(vec, clf, test), test)},
                      "gru": {"historial": hist, **ref_nueva}}, d / "metricas_categoria.json")
        entrenar_prioridad.entrenar_y_evaluar(d, nuevo_train, val, test, verbose=False)
        tecnicos = pd.read_csv(PROCESSED / "tecnicos.csv")
        entrenar_asignacion.entrenar_y_evaluar(d, historial_con_correcciones(corr, tecnicos), tecnicos, verbose=False)
        soluciones = json.loads((PROCESSED / "soluciones_rapidas.json").read_text(encoding="utf-8"))
        entrenar_similitud.construir_y_evaluar(d, nuevo_train, val, soluciones, verbose=False)
        cfg = json.loads((d_vig / "config.json").read_text(encoding="utf-8")) if (d_vig / "config.json").exists() else {}
        cfg.update({"version": version, "base": vig["version"], "n_correcciones": n_validas})
        cfg_sim = json.loads((d / "config.json").read_text(encoding="utf-8"))
        cfg["umbral_solucion_rapida"] = cfg_sim["umbral_solucion_rapida"]
        guardar_json(cfg, d / "config.json")
        m = registro.resumen_metricas(d)
        registro.registrar(version, m, n_validas, "publicada", f"Reentrenada desde {vig['version']} con {n_validas} correcciones.", activar=True)
        progreso(f"{version} publicada y activa.")
        return {**comparacion, "publicada": True, "motivo": "La versión nueva iguala o supera el F1 macro de la vigente.", "segundos": time.time() - t0}
    except Exception:
        shutil.rmtree(d, ignore_errors=True)
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=6)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--desde-cero", action="store_true")
    a = ap.parse_args()
    r = reentrenar(a.epocas, a.lr, a.desde_cero)
    print(json.dumps({k: v for k, v in r.items() if not k.startswith("recall")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
