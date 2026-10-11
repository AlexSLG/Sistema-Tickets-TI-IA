"""Pruebas de la API de inferencia (requieren models/registry.json con una versión activa). Ejecutar: pytest tests/test_api.py"""
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.training import registro

RAIZ = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (RAIZ / "models" / "registry.json").exists() or registro.version_activa() is None,
                                reason="no hay modelos entrenados (python -m src.training.entrenar_todo)")

TICKET_VPN = {"titulo": "No puedo conectarme a la VPN", "descripcion": "Desde esta mañana el cliente VPN da error al conectar desde casa y no puedo trabajar",
              "impacto": "Medio", "urgencia": "Alta", "usuarios_afectados": 1}


@pytest.fixture(scope="module")
def cliente():
    from src.service.app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def cargas_limpias(cliente):
    """Cada prueba parte de las cargas iniciales (40 % del límite)."""
    estado = cliente.get("/api/tecnicos").json()
    cliente.put("/api/tecnicos", json={"cargas": {t["id_tecnico"]: round(0.4 * t["limite_carga"]) for t in estado}})
    yield


def test_respuesta_valida_y_probabilidades(cliente):
    r = cliente.post("/api/analizar", json=TICKET_VPN)
    assert r.status_code == 200
    j = r.json()
    assert j["clasificacion"]["categoria"] in {"Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"}
    assert abs(sum(j["clasificacion"]["probabilidades"].values()) - 1) < 1e-3
    assert j["prioridad"]["prioridad"] in {"Baja", "Media", "Alta", "Crítica"}
    assert abs(sum(j["prioridad"]["probabilidades"].values()) - 1) < 1e-3
    assert len(j["tecnicos"]) == 8 and sum(t["recomendado"] for t in j["tecnicos"]) == 1 and j["tecnicos"][0]["recomendado"]
    assert len(j["similares"]) == 5 and j["version_modelos"]


@pytest.mark.parametrize("titulo,desc,esperada", [
    ("No puedo conectarme a la VPN", "El cliente VPN da error de conexión desde mi casa", "Red"),
    ("Olvidé mi contraseña", "No recuerdo la contraseña de mi cuenta y no puedo iniciar sesión", "Accesos"),
    ("Posible virus", "Mi computadora tiene un virus, aparece publicidad y el antivirus detectó malware", "Seguridad"),
    ("El monitor parpadea", "La pantalla de mi monitor parpadea y el teclado no responde", "Hardware"),
])
def test_categorias_de_ejemplos_claros(cliente, titulo, desc, esperada):
    r = cliente.post("/api/analizar", json={"titulo": titulo, "descripcion": desc, "impacto": "Bajo", "urgencia": "Media", "usuarios_afectados": 1})
    assert r.json()["clasificacion"]["categoria"] == esperada


def test_tiempo_de_respuesta_menor_a_2_segundos(cliente):
    cliente.post("/api/analizar", json=TICKET_VPN)  # calentamiento
    tiempos = []
    for _ in range(10):
        t0 = time.perf_counter()
        assert cliente.post("/api/analizar", json=TICKET_VPN).status_code == 200
        tiempos.append(time.perf_counter() - t0)
    assert max(tiempos) < 2.0, tiempos


def test_prioridad_sigue_la_matriz_impacto_urgencia(cliente):
    def prio(i, u):
        return cliente.post("/api/analizar", json={**TICKET_VPN, "impacto": i, "urgencia": u, "usuarios_afectados": 50}).json()["prioridad"]["prioridad"]
    assert prio("Alto", "Alta") == "Crítica"
    assert prio("Bajo", "Baja") == "Baja"


def test_balanceo_el_mas_apto_saturado_pasa_al_siguiente(cliente):
    base = cliente.post("/api/analizar", json=TICKET_VPN).json()
    primero = base["tecnicos"][0]
    estado = {t["id_tecnico"]: t for t in cliente.get("/api/tecnicos").json()}
    cliente.put("/api/tecnicos", json={"cargas": {primero["id_tecnico"]: estado[primero["id_tecnico"]]["limite_carga"]}})
    nuevo = cliente.post("/api/analizar", json=TICKET_VPN).json()
    assert nuevo["tecnicos"][0]["id_tecnico"] != primero["id_tecnico"]
    saturado = next(t for t in nuevo["tecnicos"] if t["id_tecnico"] == primero["id_tecnico"])
    assert saturado["saturado"] and not saturado["recomendado"]
    assert "límite" in (saturado["nota"] or "")                      # explica por qué se salta al más adecuado
    assert "capacidad" in (nuevo["tecnicos"][0]["nota"] or "")       # y qué técnico lo reemplaza


def test_balanceo_ningun_tecnico_supera_su_limite_si_hay_otro_con_capacidad(cliente):
    estado = cliente.get("/api/tecnicos").json()
    # saturar a todos menos al técnico T03
    cargas = {t["id_tecnico"]: t["limite_carga"] for t in estado}
    cargas["T03"] = 0
    cliente.put("/api/tecnicos", json={"cargas": cargas})
    for titulo, desc in [("VPN", "No conecta la VPN"), ("Contraseña", "Olvidé mi contraseña"), ("Monitor", "El monitor parpadea")]:
        j = cliente.post("/api/analizar", json={**TICKET_VPN, "titulo": titulo, "descripcion": desc}).json()
        assert j["tecnicos"][0]["id_tecnico"] == "T03" and not j["tecnicos"][0]["saturado"]


def test_balanceo_todos_al_limite_elige_el_de_menor_ocupacion(cliente):
    estado = cliente.get("/api/tecnicos").json()
    cargas = {t["id_tecnico"]: t["limite_carga"] + 3 for t in estado}
    cargas["T07"] = estado[6]["limite_carga"]  # la menor ocupación relativa: justo en el límite
    cliente.put("/api/tecnicos", json={"cargas": cargas})
    j = cliente.post("/api/analizar", json=TICKET_VPN).json()
    assert j["tecnicos"][0]["id_tecnico"] == "T07" and j["tecnicos"][0]["saturado"]
    assert "menor ocupación" in j["tecnicos"][0]["nota"]


def test_umbral_de_soluciones_rapidas(cliente):
    exacta = cliente.post("/api/analizar", json={"titulo": "mi equipo no tiene internet", "descripcion": "mi equipo no tiene internet",
                                                 "impacto": "Bajo", "urgencia": "Media", "usuarios_afectados": 1}).json()
    assert exacta["solucion_rapida"] is not None and len(exacta["solucion_rapida"]["pasos"]) >= 3
    assert exacta["solucion_rapida"]["similitud"] >= 0.65
    ajena = cliente.post("/api/analizar", json={"titulo": "Receta de paella", "descripcion": "Quiero la receta de una paella valenciana con mariscos",
                                                "impacto": "Bajo", "urgencia": "Baja", "usuarios_afectados": 1}).json()
    assert ajena["solucion_rapida"] is None


def test_similares(cliente):
    r = cliente.post("/api/similares", json={"texto": "El correo de Outlook no sincroniza en el móvil", "k": 3})
    assert r.status_code == 200 and len(r.json()["similares"]) == 3
    assert all(s["similitud"] <= 1.0001 for s in r.json()["similares"])


def test_validacion_de_entradas(cliente):
    assert cliente.post("/api/analizar", json={"titulo": "a", "descripcion": "b"}).status_code == 422
    assert cliente.post("/api/analizar", json={**TICKET_VPN, "impacto": "Enorme"}).status_code == 422
    assert cliente.put("/api/tecnicos", json={"cargas": {"T99": 1}}).status_code == 422
    assert cliente.put("/api/tecnicos", json={"cargas": {"T01": -2}}).status_code == 422


def test_correcciones_se_guardan(cliente, tmp_path, monkeypatch):
    import src.service.app as app_mod
    import src.training.reentrenar as re_mod
    ruta = tmp_path / "correcciones.csv"
    monkeypatch.setattr(app_mod, "CORRECCIONES", ruta)
    monkeypatch.setattr(re_mod, "CORRECCIONES", ruta)
    cuerpo = {"titulo": "Mi VPN falla", "descripcion": "La VPN no conecta", "categoria_corregida": "Red", "prioridad_corregida": "Media",
              "tecnico_reasignado": "T05"}
    r = cliente.post("/api/correcciones", json=cuerpo)
    assert r.status_code == 200 and r.json()["total_correcciones"] == 1
    assert cliente.post("/api/correcciones", json=cuerpo).json()["total_correcciones"] == 2
    assert "categoria_corregida" in ruta.read_text(encoding="utf-8").splitlines()[0]
    assert cliente.post("/api/correcciones", json={**cuerpo, "tecnico_reasignado": "T99"}).status_code == 422
    assert cliente.post("/api/correcciones", json={**cuerpo, "categoria_corregida": "Otra"}).status_code == 422


def test_modelos_y_metricas(cliente):
    m = cliente.get("/api/modelos").json()
    assert m["activa"] and any(v["version"] == m["activa"] for v in m["versiones"])
    j = cliente.get("/api/metricas").json()
    assert j["categoria"]["gru"]["reales"]["f1_macro"] > 0 and j["asignacion"]["top1"] > 0
    assert cliente.post("/api/modelos/activar", json={"version": "v999"}).status_code == 422


def test_pagina_y_documentacion(cliente):
    assert cliente.get("/").status_code == 200 and cliente.get("/laboratorio").status_code == 200
    assert cliente.get("/docs").status_code == 200


def test_registro_de_versiones(tmp_path, monkeypatch):
    monkeypatch.setattr(registro, "MODELOS", tmp_path)
    monkeypatch.setattr(registro, "REGISTRO", tmp_path / "registry.json")
    monkeypatch.setattr(registro, "RAIZ", tmp_path)
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "v1").mkdir()
    registro.registrar("v1", {"f1": 0.9}, 0, "publicada", activar=True)
    registro.registrar("v2", {"f1": 0.8}, 5, "descartada")
    assert registro.cargar()["activa"] == "v1" and registro.siguiente_version() == "v3"
    with pytest.raises(ValueError):
        registro.restaurar("v2")   # descartada
    with pytest.raises(ValueError):
        registro.restaurar("v7")   # inexistente
    registro.registrar("v3", {"f1": 0.95}, 5, "publicada", activar=True)
    assert registro.cargar()["activa"] == "v3"
