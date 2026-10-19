"""Construye los índices de similitud (tickets y frases de soluciones rápidas), calibra el umbral y evalúa.

Ejecutar:  python -m src.training.entrenar_similitud [--modelos models/v1]
Escribe indice_tickets.npz/_meta.csv, indice_soluciones.npz/_ids.json, umbral en config.json y metricas_similitud.json.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from src.models.comun import PROCESSED, RAIZ, cargar_split, guardar_json, texto_ticket
from src.models.similitud import IndiceTickets, PESO_TFIDF, SolucionesRapidas, normalizar, normalizar_texto
from src.training.entrenar_prioridad import cargar_gru
from src.models.gru_clasificador import predecir
import torch

COLUMNAS_META = ["id", "grupo", "fuente", "titulo", "descripcion", "categoria", "prioridad", "solucion"]


def embeddings_texto(vocab, gru, textos):
    X, L = vocab.matriz(textos)
    return predecir(gru, X, L)[1].numpy()


def evaluar_vecinos(S, cat_idx, grupo_idx, cat_q, grupo_q, k=5):
    """S: similitudes [consultas, índice]. Fracción de consultas con ≥ 3 de k vecinos de su misma categoría y precisión@k media.
    Se excluyen del índice los tickets del mismo grupo que la consulta."""
    ok3, prec = [], []
    for i in range(S.shape[0]):
        s = np.where(grupo_idx == grupo_q[i], -2, S[i])
        top = np.argsort(-s)[:k]
        mismos = (cat_idx[top] == cat_q[i]).sum()
        ok3.append(mismos >= 3)
        prec.append(mismos / k)
    return float(np.mean(ok3)), float(np.mean(prec))


def construir_y_evaluar(directorio, train, val, soluciones, verbose=True):
    directorio = Path(directorio)
    vocab, gru = cargar_gru(directorio)
    tr_real, va_real = train[train["real"]].drop_duplicates("id"), val[val["real"]]
    E_tr = embeddings_texto(vocab, gru, texto_ticket(tr_real))
    E_va = embeddings_texto(vocab, gru, texto_ticket(va_real))
    cat_tr, cat_va = tr_real["categoria"].to_numpy(), va_real["categoria"].to_numpy()
    res = {}

    # --- casos similares: índice de train, consultas de validación (tickets reales)
    g_tr, g_va = tr_real["grupo"].to_numpy(), va_real["grupo"].to_numpy()
    S_emb = normalizar(E_va) @ normalizar(E_tr).T
    ok3, p5 = evaluar_vecinos(S_emb, cat_tr, g_tr, cat_va, g_va)
    pos = np.random.default_rng(42).choice(len(va_real), 30, replace=False)  # muestra de 30 tickets de validación
    ok3_30, p5_30 = evaluar_vecinos(S_emb[pos], cat_tr, g_tr, cat_va[pos], g_va[pos])
    tf = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit(texto_ticket(tr_real))
    S_tf = (tf.transform(texto_ticket(va_real)) @ tf.transform(texto_ticket(tr_real)).T).toarray()
    ok3_tf, p5_tf = evaluar_vecinos(S_tf, cat_tr, g_tr, cat_va, g_va)
    res["casos_similares"] = {"val_reales": len(va_real), "criterio_3_de_5_misma_categoria": ok3, "precision_en_5": p5,
                              "muestra_30": {"criterio_3_de_5": ok3_30, "precision_en_5": p5_30},
                              "referencia_tfidf": {"criterio_3_de_5": ok3_tf, "precision_en_5": p5_tf}}

    # --- soluciones rápidas: híbrido GRU + TF-IDF de caracteres; calibración del umbral con leave-one-out
    textos_sr, ids, es_frase = [], [], []
    for s in soluciones:
        for f in s["frases_ejemplo"]:
            textos_sr.append(f); ids.append(s["id"]); es_frase.append(True)
        textos_sr.append(s["problema"]); ids.append(s["id"]); es_frase.append(False)  # el enunciado también se indexa
    ids, es_frase = np.array(ids), np.array(es_frase)
    E_f = embeddings_texto(vocab, gru, textos_sr)
    vec_sr = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit(
        [normalizar_texto(t) for t in texto_ticket(tr_real)] + [normalizar_texto(t) for t in textos_sr])
    T_f = vec_sr.transform([normalizar_texto(t) for t in textos_sr])
    En = normalizar(E_f)
    S = PESO_TFIDF * (T_f @ T_f.T).toarray() + (1 - PESO_TFIDF) * (En @ En.T)
    np.fill_diagonal(S, -2)
    q = np.where(es_frase)[0]                      # consultas: las frases de ejemplo; el índice es todo lo demás
    mejor, sim_mejor = S[q].argmax(1), S[q].max(1)
    acierta = ids[q] == ids[mejor]
    filas = []
    for u in np.arange(0.40, 0.91, 0.05):
        d = sim_mejor >= u
        filas.append({"umbral": round(float(u), 2), "cobertura": float(d.mean()), "precision": float(acierta[d].mean()) if d.any() else None})
    candidatos = [r for r in filas if r["precision"] is not None and r["precision"] >= 0.85 and r["cobertura"] >= 0.03]
    umbral = candidatos[0]["umbral"] if candidatos else 0.9
    sr_tmp = SolucionesRapidas(soluciones, E_f, ids, vec_sr, T_f, umbral)
    # tickets de validación: ¿cuántos disparan una solución y coincide la categoría?
    disp, coinc = 0, 0
    for k in range(len(va_real)):
        r = sr_tmp.consultar(E_va[k], texto_ticket(va_real.iloc[[k]])[0])
        if r:
            disp += 1
            coinc += r["categoria"] == cat_va[k]
    res["soluciones_rapidas"] = {
        "frases": int(es_frase.sum()), "textos_indexados": len(textos_sr), "entradas": len(soluciones), "peso_tfidf": PESO_TFIDF, "umbral": umbral,
        "leave_one_phrase_out": {"exactitud_top1": float(acierta.mean()), "curva_umbral": filas},
        "val": {"consultas": len(va_real), "fraccion_que_dispara": disp / len(va_real),
                "categoria_coincide_cuando_dispara": (coinc / disp) if disp else None},
    }

    # --- índices definitivos: tickets reales de train + val (los datos nuevos se añadirán al reentrenar)
    todos = pd.concat([tr_real, va_real])
    E_todos = np.vstack([E_tr, E_va])
    IndiceTickets(E_todos, todos[COLUMNAS_META].assign(solucion=todos["solucion"].replace("", None))).guardar(directorio)
    sr_tmp.guardar(directorio)
    cfg_ruta = directorio / "config.json"
    cfg = json.loads(cfg_ruta.read_text(encoding="utf-8")) if cfg_ruta.exists() else {}
    cfg["umbral_solucion_rapida"] = umbral
    guardar_json(cfg, cfg_ruta)
    guardar_json(res, directorio / "metricas_similitud.json")
    if verbose:
        c = res["casos_similares"]
        print(f"  casos similares: ≥3 de 5 de la misma categoría en {c['criterio_3_de_5_misma_categoria']:.1%} de {c['val_reales']} (muestra de 30: "
              f"{c['muestra_30']['criterio_3_de_5']:.1%}; TF-IDF {c['referencia_tfidf']['criterio_3_de_5']:.1%}); precisión@5 {c['precision_en_5']:.3f}")
        s = res["soluciones_rapidas"]
        print(f"  soluciones rápidas: leave-one-out top-1 {s['leave_one_phrase_out']['exactitud_top1']:.3f}; umbral {umbral}; "
              f"dispara en {s['val']['fraccion_que_dispara']:.1%} de {s['val']['consultas']} tickets de val; categoría coincide {s['val']['categoria_coincide_cuando_dispara']}")
    return res


def reconstruir_indice_soluciones(directorio, verbose=True):
    """Reconstruye solo el índice de soluciones rápidas (p. ej. tras añadir entradas a soluciones_rapidas.json) conservando los
    pesos de los modelos y el umbral ya calibrado de la versión. No toca el índice de tickets ni las métricas."""
    directorio = Path(directorio)
    vocab, gru = cargar_gru(directorio)
    cfg = json.loads((directorio / "config.json").read_text(encoding="utf-8"))
    soluciones = json.loads((PROCESSED / "soluciones_rapidas.json").read_text(encoding="utf-8"))
    train = cargar_split("train")
    tr_real = train[train["real"]].drop_duplicates("id")
    textos_sr, ids = [], []
    for s in soluciones:
        for f in s["frases_ejemplo"] + [s["problema"]]:
            textos_sr.append(f)
            ids.append(s["id"])
    E_f = embeddings_texto(vocab, gru, textos_sr)
    vec_sr = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit(
        [normalizar_texto(t) for t in texto_ticket(tr_real)] + [normalizar_texto(t) for t in textos_sr])
    T_f = vec_sr.transform([normalizar_texto(t) for t in textos_sr])
    SolucionesRapidas(soluciones, E_f, ids, vec_sr, T_f, cfg["umbral_solucion_rapida"]).guardar(directorio)
    if verbose:
        print(f"  índice de soluciones rápidas reconstruido: {len(soluciones)} entradas, {len(textos_sr)} textos, umbral {cfg['umbral_solucion_rapida']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", default=str(RAIZ / "models" / "v1"))
    ap.add_argument("--solo-soluciones", action="store_true", help="reconstruye solo el índice de soluciones rápidas")
    a = ap.parse_args()
    if a.solo_soluciones:
        return reconstruir_indice_soluciones(a.modelos)
    soluciones = json.loads((PROCESSED / "soluciones_rapidas.json").read_text(encoding="utf-8"))
    construir_y_evaluar(a.modelos, cargar_split("train"), cargar_split("val"), soluciones)


if __name__ == "__main__":
    main()
