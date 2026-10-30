"""Pruebas de administración (fase 7): técnicos, efecto en la asignación de la IA y endpoints de modelos."""
import pytest

from tests.ayudas import ADMIN, ANA, LUIS, MARCELA, MONITOR, SERVIDOR, entrar, registrar

pytestmark = pytest.mark.usefixtures("bd_limpia")


def test_solo_el_administrador_gestiona_tecnicos(cliente):
    assert cliente.get("/api/admin/tecnicos", headers=entrar(cliente, ANA)).status_code == 403
    assert cliente.get("/api/admin/tecnicos", headers=entrar(cliente, MARCELA)).status_code == 403
    assert cliente.put("/api/admin/tecnicos/T01", headers=entrar(cliente, MARCELA), json={"limite_carga": 3}).status_code == 403
    assert cliente.get("/api/admin/tecnicos").status_code == 401
    lista = cliente.get("/api/admin/tecnicos", headers=entrar(cliente, ADMIN)).json()
    assert len(lista) == 8 and lista[0]["id"] == "T01" and lista[0]["carga"] == 0 and lista[0]["aptitudes"]["Hardware"] == 5


def test_editar_limite_disponibilidad_y_aptitudes(cliente):
    h = entrar(cliente, ADMIN)
    r = cliente.put("/api/admin/tecnicos/T03", headers=h, json={"limite_carga": 2, "disponible": False, "aptitudes": {"Red": 4}})
    assert r.status_code == 200 and r.json()["limite_carga"] == 2 and r.json()["disponible"] is False
    assert r.json()["aptitudes"]["Red"] == 4 and r.json()["aptitudes"]["Software"] == 5  # el resto no cambia
    assert cliente.put("/api/admin/tecnicos/T03", headers=h, json={"limite_carga": 0}).status_code == 422
    assert cliente.put("/api/admin/tecnicos/T03", headers=h, json={"aptitudes": {"Red": 9}}).status_code == 422
    assert cliente.put("/api/admin/tecnicos/T03", headers=h, json={"aptitudes": {"Inventada": 3}}).status_code == 422
    assert cliente.put("/api/admin/tecnicos/T99", headers=h, json={"limite_carga": 3}).status_code == 404


def test_marcar_no_disponible_al_mas_apto_hace_que_el_ticket_pase_al_siguiente(cliente):
    """Paso 5 del guion de demostración."""
    h = entrar(cliente, ADMIN)
    mejor = registrar(cliente, entrar(cliente, ANA))["tecnico"]["id"]
    cliente.put(f"/api/admin/tecnicos/{mejor}", headers=h, json={"disponible": False})
    t2 = registrar(cliente, entrar(cliente, LUIS))
    assert t2["tecnico"]["id"] != mejor
    ranking = cliente.get(f"/api/tickets/{t2['id']}", headers=h).json()["analisis"]["tecnicos_sugeridos"]
    anulado = next(x for x in ranking if x["id_tecnico"] == mejor)
    assert anulado["saturado"] and "no está disponible" in anulado["nota"]
    # y bajar el límite al mínimo también lo aparta cuando ya tiene un ticket abierto
    cliente.put(f"/api/admin/tecnicos/{mejor}", headers=h, json={"disponible": True, "limite_carga": 1})
    t3 = registrar(cliente, entrar(cliente, LUIS))
    assert t3["tecnico"]["id"] != mejor


def test_cambiar_aptitudes_cambia_la_asignacion(cliente):
    h = entrar(cliente, ADMIN)
    antes = registrar(cliente, entrar(cliente, ANA))["tecnico"]["id"]
    # quien no era el elegido pasa a ser experto en Red y el anterior deja de serlo
    otro = "T08" if antes != "T08" else "T07"
    cliente.put(f"/api/admin/tecnicos/{otro}", headers=h, json={"aptitudes": {"Red": 5}})
    cliente.put(f"/api/admin/tecnicos/{antes}", headers=h, json={"aptitudes": {"Red": 1}})
    despues = registrar(cliente, entrar(cliente, LUIS))["tecnico"]["id"]
    assert despues != antes


def test_endpoints_de_modelos_siguen_disponibles(cliente):
    assert cliente.get("/api/modelos").json()["activa"]
    assert cliente.get("/api/metricas").json()["categoria"]["gru"]["reales"]["f1_macro"] > 0.8
    assert cliente.get("/api/reentrenar/estado").json()["estado"] in ("inactivo", "terminado", "error", "ejecutando")
    assert cliente.get("/api/correcciones").status_code == 200
    assert cliente.get("/laboratorio").status_code == 200 and cliente.get("/").status_code == 200


def test_usuario_soporte_nuevo_es_tecnico_y_recibe_tickets(cliente):
    h = entrar(cliente, ADMIN)
    r = cliente.post("/api/usuarios", headers=h, json={"nombre": "Nuevo Técnico", "correo": "nuevo.tecnico@soporte.local",
                                                       "contrasena": "Soporte123", "rol": "Soporte"})
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    tecnicos = {t["correo"]: t for t in cliente.get("/api/admin/tecnicos", headers=h).json()}
    nuevo = tecnicos["nuevo.tecnico@soporte.local"]
    assert nuevo["id"] == "T09" and nuevo["disponible"] and nuevo["limite_carga"] == 8
    # con todos los demás no disponibles, la IA le asigna el ticket (el modelo admite técnicos que no conoció al entrenar)
    for t in tecnicos.values():
        if t["id"] != "T09":
            cliente.put(f"/api/admin/tecnicos/{t['id']}", headers=h, json={"disponible": False})
    ticket = registrar(cliente, entrar(cliente, ANA), MONITOR)
    assert ticket["tecnico"]["id"] == "T09"
    # deja de ser Soporte → no disponible; vuelve a Soporte → disponible
    cliente.put(f"/api/usuarios/{uid}", headers=h, json={"rol": "Usuario"})
    assert not {t["id"]: t for t in cliente.get("/api/admin/tecnicos", headers=h).json()}["T09"]["disponible"]
    cliente.put(f"/api/usuarios/{uid}", headers=h, json={"rol": "Soporte"})
    assert {t["id"]: t for t in cliente.get("/api/admin/tecnicos", headers=h).json()}["T09"]["disponible"]
