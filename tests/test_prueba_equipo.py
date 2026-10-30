"""Pruebas del validador del conjunto de prueba del equipo (fase 1 del Sprint 3)."""
import pandas as pd

from src.data import validar_prueba_equipo as vpe

FILA = {"id": "EQ-1", "titulo": "La impresora del segundo piso no imprime", "descripcion": "Mandé a imprimir tres veces y no sale nada, la luz parpadea en naranja",
        "impacto": "Bajo", "urgencia": "Media", "usuarios_afectados": "3", "categoria": "Hardware", "prioridad": "Baja", "autor": "Equipo"}


def tabla(*filas):
    return pd.DataFrame([{**FILA, **f} for f in filas], dtype=str)


def test_fila_correcta_es_valida():
    validos, inf = vpe.validar(tabla({}))
    assert len(validos) == 1 and inf["errores"] == []
    assert validos.iloc[0]["usuarios_afectados"] == 3


def test_valores_fuera_de_la_taxonomia_vacios_y_numeros_invalidos():
    validos, inf = vpe.validar(tabla({"id": "A", "categoria": "Impresoras"}, {"id": "B", "descripcion": "", "titulo": "Otro problema"},
                                     {"id": "C", "usuarios_afectados": "0", "titulo": "x y z", "descripcion": "algo distinto"},
                                     {"id": "D", "impacto": "Enorme", "descripcion": "otra cosa"}))
    assert len(validos) == 0 and len(inf["errores"]) == 4


def test_duplicados_por_id_y_descripcion():
    validos, inf = vpe.validar(tabla({"id": "A"}, {"id": "A", "descripcion": "texto diferente"}, {"id": "B"}))
    assert len(validos) == 1 and sum("duplicado" in e for e in inf["errores"]) == 2


def test_columnas_faltantes():
    validos, inf = vpe.validar(pd.DataFrame({"id": ["1"], "titulo": ["a"]}))
    assert len(validos) == 0 and "Faltan columnas" in inf["errores"][0]


def test_solapamiento_con_los_datos_del_proyecto_se_excluye():
    ref = pd.read_csv("data/processed/tickets.csv", keep_default_na=False, usecols=["id", "titulo", "descripcion"]).head(300)
    copia = ref.iloc[5]
    validos, inf = vpe.validar(tabla({}, {"id": "EQ-2", "titulo": copia["titulo"], "descripcion": copia["descripcion"]}), ref)
    assert list(validos["id"]) == ["EQ-1"]
    assert inf["excluidos_solapamiento"][0]["id"] == "EQ-2" and inf["excluidos_solapamiento"][0]["parecido_a"] == copia["id"]


def test_prioridad_segun_la_matriz_y_avisos_de_cobertura():
    assert vpe.prioridad_matriz("Alto", "Alta") == "Crítica" and vpe.prioridad_matriz("Bajo", "Baja") == "Baja"
    assert vpe.prioridad_matriz("Medio", "Media") == "Media" and vpe.prioridad_matriz("Alto", "Media") == "Alta"
    _, inf = vpe.validar(tabla({"prioridad": "Crítica"}))
    assert any("matriz" in a for a in inf["avisos"]) and any("mínimo acordado" in a for a in inf["avisos"])
