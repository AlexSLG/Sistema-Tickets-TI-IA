"""Pruebas de HU26: guardar, editar y desactivar soluciones rápidas; el índice se actualiza sin reiniciar."""
import shutil

import pytest

from src.models import catalogo_soluciones
from tests.ayudas import ADMIN, ANA, MONITOR, credencial_tecnico, entrar, registrar

pytestmark = pytest.mark.usefixtures("bd_limpia")

IMPRESORA = {"titulo": "La impresora del tercer piso imprime hojas con rayas moradas",
             "descripcion": "La impresora del tercer piso imprime hojas con rayas moradas en todas las copias", "impacto": "Bajo",
             "urgencia": "Baja", "usuarios_afectados": 3}
FRASE = "la impresora imprime rayas moradas en las hojas"


@pytest.fixture(autouse=True)
def catalogo_temporal(tmp_path, monkeypatch, cliente):
    """Copia del catálogo: las pruebas no modifican data/processed/soluciones_rapidas.json. Al terminar se vuelve a indexar el real."""
    from src.sistema import ia
    ruta = tmp_path / "soluciones_rapidas.json"
    shutil.copy(catalogo_soluciones.RUTA, ruta)
    monkeypatch.setattr(catalogo_soluciones, "RUTA", ruta)
    yield ruta
    monkeypatch.undo()
    ia.servicio().recargar_soluciones()


def resolver(cliente, datos):
    """Registra un ticket como Ana y su técnico lo resuelve. Devuelve (ticket, cabecera del técnico)."""
    t = registrar(cliente, entrar(cliente, ANA), datos)
    h = entrar(cliente, credencial_tecnico(t["tecnico"]["id"]))
    for estado, extra in (("En progreso", {}), ("Resuelto", {"solucion": "Se limpió el rodillo de la impresora.\nSe cambió el tóner morado."})):
        r = cliente.put(f"/api/tickets/{t['id']}/estado", headers=h, json={"estado": estado, **extra})
        assert r.status_code == 200, r.text
    return t, h


def test_solucion_guardada_desde_un_ticket_se_sugiere_de_inmediato(cliente):
    ana = entrar(cliente, ANA)
    antes = cliente.post("/api/tickets/analizar", headers=ana, json={**IMPRESORA, "titulo": FRASE, "descripcion": FRASE}).json()
    assert antes["solucion_rapida"] is None or "moradas" not in antes["solucion_rapida"]["problema"]
    t, h = resolver(cliente, IMPRESORA)
    r = cliente.post("/api/soluciones", headers=h, json={"problema": "La impresora imprime rayas moradas", "categoria": "Hardware",
                                                         "frases_ejemplo": [IMPRESORA["titulo"], FRASE, "salen rayas moradas al imprimir"],
                                                         "pasos": ["Limpia el rodillo de la impresora.", "Cambia el tóner morado.", "Si sigue, avisa a Soporte."],
                                                         "ticket_id": t["id"]})
    assert r.status_code == 201, r.text
    nueva = r.json()
    assert nueva["id"] == "SR-52" and nueva["ticket_origen"] == t["codigo"] and nueva["activa"]
    despues = cliente.post("/api/tickets/analizar", headers=ana, json={**IMPRESORA, "titulo": FRASE, "descripcion": FRASE}).json()
    assert despues["solucion_rapida"] and despues["solucion_rapida"]["id"] == "SR-52"
    detalle = cliente.get(f"/api/tickets/{t['id']}", headers=h).json()
    assert any(x["accion"] == "solución rápida" for x in detalle["historial"])
    # desactivar → deja de sugerirse; activar → vuelve
    adm = entrar(cliente, ADMIN)
    assert cliente.put("/api/soluciones/SR-52", headers=adm, json={"activa": False}).status_code == 200
    r = cliente.post("/api/tickets/analizar", headers=ana, json={**IMPRESORA, "titulo": FRASE, "descripcion": FRASE}).json()["solucion_rapida"]
    assert r is None or r["id"] != "SR-52"
    cliente.put("/api/soluciones/SR-52", headers=adm, json={"activa": True, "problema": "Rayas moradas al imprimir"})
    r = cliente.post("/api/tickets/analizar", headers=ana, json={**IMPRESORA, "titulo": FRASE, "descripcion": FRASE}).json()["solucion_rapida"]
    assert r["id"] == "SR-52" and r["problema"] == "Rayas moradas al imprimir"
    assert next(s for s in catalogo_soluciones.leer() if s["id"] == "SR-52")["activa"]


def test_permisos_y_validaciones(cliente):
    cuerpo = {"problema": "Problema de prueba", "categoria": "Red", "frases_ejemplo": ["frase"], "pasos": ["paso"]}
    assert cliente.get("/api/soluciones").status_code == 401
    assert cliente.get("/api/soluciones", headers=entrar(cliente, ANA)).status_code == 403
    assert cliente.post("/api/soluciones", headers=entrar(cliente, ANA), json=cuerpo).status_code == 403
    abierto = registrar(cliente, entrar(cliente, ANA), MONITOR)
    h_tec = entrar(cliente, credencial_tecnico(abierto["tecnico"]["id"]))
    assert cliente.put("/api/soluciones/SR-01", headers=h_tec, json={"activa": False}).status_code == 403   # editar: solo Administrador
    r = cliente.post("/api/soluciones", headers=h_tec, json={**cuerpo, "ticket_id": abierto["id"]})
    assert r.status_code == 422 and "Resuelto o Cerrado" in r.json()["detail"]
    adm = entrar(cliente, ADMIN)
    assert cliente.post("/api/soluciones", headers=adm, json={**cuerpo, "pasos": ["  "]}).status_code == 422
    assert cliente.post("/api/soluciones", headers=adm, json={**cuerpo, "categoria": "Otra"}).status_code == 422
    assert cliente.put("/api/soluciones/SR-999", headers=adm, json={"activa": False}).status_code == 404
    lista = cliente.get("/api/soluciones", headers=h_tec).json()
    assert len(lista) == 51 and all(s["activa"] for s in lista)
