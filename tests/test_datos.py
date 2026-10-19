"""Pruebas de integridad de los datos del Sprint 1 (pasos 4 a 6). Ejecutar: pytest tests/test_datos.py"""
import json
from pathlib import Path

import pandas as pd
import pytest

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
CATEGORIAS = {"Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"}
PRIORIDADES = {"Baja", "Media", "Alta", "Crítica"}
COLUMNAS = ["id", "fuente", "idioma_original", "texto_original", "titulo", "descripcion", "categoria", "prioridad", "impacto",
            "urgencia", "usuarios_afectados", "solucion", "origen_etiqueta", "grupo"]

pytestmark = pytest.mark.skipif(not (PROCESSED / "tickets.csv").exists(), reason="faltan los datos procesados")


def leer(nombre):
    return pd.read_csv(PROCESSED / nombre, keep_default_na=False)


def test_esquema_y_valores_validos():
    t = leer("tickets.csv")
    assert set(COLUMNAS) <= set(t.columns)
    assert set(t["categoria"]) == CATEGORIAS
    assert set(t["prioridad"]) <= PRIORIDADES
    assert set(t["impacto"]) <= {"Bajo", "Medio", "Alto"} and set(t["urgencia"]) <= {"Baja", "Media", "Alta"}
    assert t["id"].is_unique
    assert (t["titulo"].str.len() > 0).all() and (t["descripcion"].str.len() > 0).all()
    assert (t["usuarios_afectados"].astype(int) >= 1).all()


def test_balance_minimo_por_categoria():
    t = leer("tickets.csv")
    conteo = t["categoria"].value_counts()
    assert (conteo >= 400).all(), conteo.to_dict()  # Correo (≈ 440) es la más corta: ver reports/reglas_etiquetado.md


def test_division_sin_fuga_por_grupo():
    partes = {s: leer(f"{s}.csv") for s in ("train", "val", "test")}
    grupos = {s: set(p["grupo"]) for s, p in partes.items()}
    assert not (grupos["train"] & grupos["val"]) and not (grupos["train"] & grupos["test"]) and not (grupos["val"] & grupos["test"])
    todos = pd.concat(partes.values())
    assert todos["id"].is_unique and len(todos) == len(leer("tickets.csv"))
    for s, p in partes.items():
        assert abs(len(p) / len(todos) - {"train": 0.70, "val": 0.15, "test": 0.15}[s]) < 0.01


def test_variantes_aumentadas_comparten_grupo_y_etiqueta_con_el_original():
    t = leer("tickets.csv").set_index("id")
    aum = t[t["origen_etiqueta"] == "aumento"]
    assert len(aum) > 0
    originales = t.loc[aum["grupo"]]
    assert (originales["categoria"].values == aum["categoria"].values).all()
    assert (originales["prioridad"].values == aum["prioridad"].values).all()


def test_estratificacion_similar_entre_subconjuntos():
    for col in ("categoria", "prioridad"):
        prop = {s: leer(f"{s}.csv")[col].value_counts(normalize=True) for s in ("train", "val", "test")}
        for s in ("val", "test"):
            assert (prop[s].reindex(prop["train"].index).fillna(0) - prop["train"]).abs().max() < 0.02


def test_tecnicos_al_menos_dos_aptos_por_categoria():
    t = leer("tecnicos.csv")
    assert len(t) == 8
    for c in CATEGORIAS:
        col = f"aptitud_{c.lower()}"
        assert t[col].between(1, 5).all()
        assert (t[col] >= 4).sum() >= 2, c
    assert (t["limite_carga"] > 0).all()


def test_historial_coherente():
    h, t = leer("historial_asignaciones.csv"), leer("tecnicos.csv")
    assert len(h) == len(leer("tickets.csv")) and h["id_ticket"].is_unique
    assert set(h["tecnico"]) <= set(t["id_tecnico"]) and set(h["tecnico_inicial"]) <= set(t["id_tecnico"])
    assert (h["tiempo_resolucion_h"] > 0).all()
    assert h["saturado"].mean() < 0.15  # hay saturación (para el balanceo) pero no domina
    assert 0 < h["reasignado"].mean() < 0.10


def test_soluciones_rapidas():
    s = json.loads((PROCESSED / "soluciones_rapidas.json").read_text(encoding="utf-8"))
    assert len(s) >= 50
    assert {e["categoria"] for e in s} == CATEGORIAS
    for e in s:
        assert {"id", "categoria", "problema", "frases_ejemplo", "pasos"} <= set(e)
        assert 3 <= len(e["frases_ejemplo"]) <= 5 and len(e["pasos"]) >= 3
    assert len({e["id"] for e in s}) == len(s)
