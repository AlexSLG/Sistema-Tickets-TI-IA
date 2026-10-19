"""Pruebas del panel de métricas (fase 8): totales coherentes y permisos por rol."""
import pytest

from tests.ayudas import ADMIN, ANA, CORREO_CLAVE, LUIS, MARCELA, MONITOR, SERVIDOR, credencial_tecnico, entrar, registrar

pytestmark = pytest.mark.usefixtures("bd_limpia")


def test_panel_solo_para_administrador_y_soporte(cliente):
    assert cliente.get("/api/panel/resumen").status_code == 401
    assert cliente.get("/api/panel/resumen", headers=entrar(cliente, ANA)).status_code == 403
    assert cliente.get("/api/panel/resumen", headers=entrar(cliente, ADMIN)).status_code == 200


def test_panel_vacio(cliente):
    r = cliente.get("/api/panel/resumen", headers=entrar(cliente, ADMIN)).json()
    assert r["total"] == 0 and r["abiertos"] == 0 and r["tiempo_resolucion"]["promedio_horas"] is None
    assert r["sugerencias_ia"]["categoria_aceptada"] is None and len(r["por_dia"]) == 14 and len(r["carga_tecnicos"]) == 8


def test_panel_totales_coherentes(cliente):
    ha, hl = entrar(cliente, ANA), entrar(cliente, LUIS)
    t1 = registrar(cliente, ha, SERVIDOR)
    t2 = registrar(cliente, hl, MONITOR)
    registrar(cliente, ha, CORREO_CLAVE, resuelto_con_solucion_rapida=True)
    # resolver el primero y corregir el segundo
    ht = entrar(cliente, credencial_tecnico(t1["tecnico"]["id"]))
    cliente.put(f"/api/tickets/{t1['id']}/estado", headers=ht, json={"estado": "En progreso"})
    cliente.put(f"/api/tickets/{t1['id']}/estado", headers=ht, json={"estado": "Resuelto", "solucion": "Reinicio del switch"})
    h2 = entrar(cliente, credencial_tecnico(t2["tecnico"]["id"]))
    cat_nueva = "Software" if t2["categoria"] != "Software" else "Red"
    cliente.post(f"/api/tickets/{t2['id']}/corregir", headers=h2, json={"categoria": cat_nueva})

    r = cliente.get("/api/panel/resumen", headers=entrar(cliente, ADMIN)).json()
    assert r["total"] == 3 and sum(r["por_estado"].values()) == 3 and sum(r["por_categoria"].values()) == 3 and sum(r["por_prioridad"].values()) == 3
    assert r["por_estado"] == {"Abierto": 1, "En progreso": 0, "Resuelto": 1, "Cerrado": 1}
    assert r["abiertos"] == 1 and r["resueltos_con_solucion_rapida"] == 1
    assert sum(r["por_area"].values()) == 3
    assert r["tiempo_resolucion"]["resueltos"] == 1 and r["tiempo_resolucion"]["promedio_horas"] >= 0
    assert sum(x["resueltos"] for x in r["tiempo_resolucion"]["por_tecnico"]) == 1
    assert r["sugerencias_ia"]["analizados"] == 3 and r["sugerencias_ia"]["corregidos"] == 1
    assert abs(r["sugerencias_ia"]["categoria_aceptada"] - 2 / 3) < 1e-3
    assert sum(d["tickets"] for d in r["por_dia"]) == 3
    assert sum(x["carga"] for x in r["carga_tecnicos"]) == 1  # solo el del monitor sigue abierto


def test_soporte_ve_solo_lo_suyo(cliente):
    t = registrar(cliente, entrar(cliente, ANA))
    registrar(cliente, entrar(cliente, LUIS), MONITOR)
    asignado = t["tecnico"]["id"]
    r = cliente.get("/api/panel/resumen", headers=entrar(cliente, credencial_tecnico(asignado))).json()
    assert r["alcance"] == "propios" and r["total"] >= 1 and len(r["carga_tecnicos"]) == 1 and r["carga_tecnicos"][0]["id"] == asignado
    assert cliente.get("/api/panel/resumen", headers=entrar(cliente, ADMIN)).json()["total"] == 2
