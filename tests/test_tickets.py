"""Pruebas de tickets con IA (fases 3 y 4 del Sprint 2): registro, flujo de estados, permisos, corrección y asignación."""
import pytest

from src.sistema import db as bd
from src.sistema.modelos import Correccion, Tecnico, Ticket
from tests.ayudas import ADMIN, ANA, CORREO_CLAVE, LUIS, MONITOR, SERVIDOR, credencial_tecnico, entrar, registrar

pytestmark = pytest.mark.usefixtures("bd_limpia")


def test_registrar_ticket_tiene_categoria_prioridad_tecnico_y_analisis(cliente):
    t = registrar(cliente, entrar(cliente, ANA))
    assert t["codigo"] == "TK-0001" and t["estado"] == "Abierto"
    assert t["categoria"] == "Red" and t["prioridad"] == "Crítica"
    assert t["tecnico"] and t["tecnico"]["id"].startswith("T")
    assert "analisis" not in t  # el solicitante no ve el análisis
    d = cliente.get(f"/api/tickets/{t['id']}", headers=entrar(cliente, ADMIN)).json()
    a = d["analisis"]
    assert a["version_modelos"] and a["categoria_sugerida"] == "Red" and len(a["tecnicos_sugeridos"]) == 8
    assert abs(sum(a["prob_categoria"].values()) - 1) < 1e-3 and len(a["similares"]) == 5 and a["tiempo_ms"] > 0
    assert [h["accion"] for h in d["historial"]] == ["creado", "asignado"]
    assert registrar(cliente, entrar(cliente, LUIS))["codigo"] == "TK-0002"


def test_analizar_antes_de_guardar_no_crea_ticket(cliente):
    h = entrar(cliente, ANA)
    r = cliente.post("/api/tickets/analizar", headers=h, json=CORREO_CLAVE)
    assert r.status_code == 200 and r.json()["clasificacion"]["categoria"] == "Correo"
    assert r.json()["solucion_rapida"]["id"] == "SR-51" and "tecnicos" not in r.json()
    assert cliente.get("/api/tickets", headers=h).json() == []
    assert "tecnicos" in cliente.post("/api/tickets/analizar", headers=entrar(cliente, ADMIN), json=CORREO_CLAVE).json()


def test_solucion_rapida_resuelta_cierra_el_ticket(cliente):
    h = entrar(cliente, ANA)
    t = registrar(cliente, h, CORREO_CLAVE, resuelto_con_solucion_rapida=True)
    assert t["estado"] == "Cerrado" and t["resuelto_con_solucion_rapida"] and t["tecnico"] is None
    assert t["solucion"] and t["cerrado_en"]
    r = cliente.post("/api/tickets", headers=h, json={**SERVIDOR, "resuelto_con_solucion_rapida": True})  # sin solución rápida disponible
    assert r.status_code == 422


def test_tecnico_ve_el_ticket_y_lo_resuelve(cliente):
    t = registrar(cliente, entrar(cliente, ANA))
    ht = entrar(cliente, credencial_tecnico(t["tecnico"]["id"]))
    assert [x["id"] for x in cliente.get("/api/tickets", headers=ht).json()] == [t["id"]]
    url = f"/api/tickets/{t['id']}/estado"
    assert cliente.put(url, headers=ht, json={"estado": "Resuelto", "solucion": "x"}).status_code == 422   # Abierto -> Resuelto no existe
    assert cliente.put(url, headers=ht, json={"estado": "En progreso"}).json()["estado"] == "En progreso"
    assert cliente.put(url, headers=ht, json={"estado": "Resuelto"}).status_code == 422                    # sin solución
    assert cliente.put(url, headers=ht, json={"estado": "Resuelto", "solucion": "  "}).status_code == 422
    r = cliente.put(url, headers=ht, json={"estado": "Resuelto", "solucion": "Se reinició el switch del piso"})
    assert r.json()["estado"] == "Resuelto" and r.json()["solucion"] and r.json()["resuelto_en"]
    assert cliente.put(url, headers=entrar(cliente, ANA), json={"estado": "En progreso"}).status_code == 403


def test_bandeja_ordenada_por_prioridad(cliente):
    h = entrar(cliente, ANA)
    baja, critica = registrar(cliente, h, MONITOR), registrar(cliente, h, SERVIDOR)
    with bd.SessionLocal() as s:  # los dos al mismo técnico
        for tid in (baja["id"], critica["id"]):
            s.get(Ticket, tid).tecnico_id = "T08"
        s.commit()
    bandeja = cliente.get("/api/tickets", headers=entrar(cliente, credencial_tecnico("T08"))).json()
    assert bandeja[0]["id"] == critica["id"] and bandeja[0]["prioridad"] == "Crítica"
    assert [x["id"] for x in bandeja] == [critica["id"], baja["id"]]


def test_usuario_confirma_o_reabre(cliente):
    h = entrar(cliente, ANA)
    t = registrar(cliente, h)
    ht = entrar(cliente, credencial_tecnico(t["tecnico"]["id"]))
    assert cliente.post(f"/api/tickets/{t['id']}/confirmar", headers=h).status_code == 422  # aún no está Resuelto
    url = f"/api/tickets/{t['id']}/estado"
    cliente.put(url, headers=ht, json={"estado": "En progreso"})
    cliente.put(url, headers=ht, json={"estado": "Resuelto", "solucion": "Listo"})
    assert cliente.post(f"/api/tickets/{t['id']}/reabrir", headers=entrar(cliente, LUIS)).status_code == 403  # otro usuario
    assert cliente.post(f"/api/tickets/{t['id']}/reabrir", headers=h).json()["estado"] == "En progreso"
    cliente.put(url, headers=ht, json={"estado": "Resuelto", "solucion": "Ahora sí"})
    r = cliente.post(f"/api/tickets/{t['id']}/confirmar", headers=h).json()
    assert r["estado"] == "Cerrado" and r["cerrado_en"]


def test_permisos_sobre_tickets_ajenos(cliente):
    t = registrar(cliente, entrar(cliente, ANA))
    assert cliente.get(f"/api/tickets/{t['id']}", headers=entrar(cliente, LUIS)).status_code == 403
    assert cliente.get("/api/tickets", headers=entrar(cliente, LUIS)).json() == []
    otro = "T01" if t["tecnico"]["id"] != "T01" else "T02"
    ho = entrar(cliente, credencial_tecnico(otro))
    assert cliente.get(f"/api/tickets/{t['id']}", headers=ho).status_code == 403
    assert cliente.post(f"/api/tickets/{t['id']}/comentarios", headers=ho, json={"texto": "hola"}).status_code == 403
    assert cliente.get("/api/tickets/no-existe", headers=entrar(cliente, ADMIN)).status_code == 404
    assert len(cliente.get("/api/tickets", headers=entrar(cliente, ADMIN)).json()) == 1
    assert cliente.get("/api/tickets").status_code == 401


def test_comentarios(cliente):
    h = entrar(cliente, ANA)
    t = registrar(cliente, h)
    ht = entrar(cliente, credencial_tecnico(t["tecnico"]["id"]))
    cliente.post(f"/api/tickets/{t['id']}/comentarios", headers=ht, json={"texto": "Estoy revisando el switch"})
    d = cliente.post(f"/api/tickets/{t['id']}/comentarios", headers=h, json={"texto": "Gracias, sigo sin red"}).json()
    assert [c["rol"] for c in d["comentarios"]] == ["Soporte", "Usuario"] and d["comentarios"][1]["autor"] == "Ana Torres"
    assert cliente.post(f"/api/tickets/{t['id']}/comentarios", headers=h, json={"texto": ""}).status_code == 422


def test_correccion_guarda_fila_en_bd_y_en_csv(cliente, tmp_path, monkeypatch):
    import src.training.reentrenar as re_mod
    ruta = tmp_path / "correcciones.csv"
    monkeypatch.setattr(re_mod, "CORRECCIONES", ruta)
    t = registrar(cliente, entrar(cliente, ANA))
    ht = entrar(cliente, credencial_tecnico(t["tecnico"]["id"]))
    url = f"/api/tickets/{t['id']}/corregir"
    assert cliente.post(url, headers=entrar(cliente, ANA), json={"categoria": "Seguridad"}).status_code == 403
    assert cliente.post(url, headers=ht, json={}).status_code == 422
    assert cliente.post(url, headers=ht, json={"categoria": "Red", "prioridad": "Crítica"}).status_code == 422  # sin cambios
    d = cliente.post(url, headers=ht, json={"categoria": "Software", "prioridad": "Alta"}).json()
    assert d["categoria"] == "Software" and d["prioridad"] == "Alta"
    assert d["correcciones"][0]["categoria_ia"] == "Red" and d["correcciones"][0]["categoria_correcta"] == "Software"
    with bd.SessionLocal() as s:
        c = s.query(Correccion).one()
        assert (c.categoria_ia, c.categoria_correcta, c.prioridad_ia, c.prioridad_correcta) == ("Red", "Software", "Crítica", "Alta")
    filas = ruta.read_text(encoding="utf-8").splitlines()
    assert filas[0].startswith("titulo,descripcion,categoria_corregida,prioridad_corregida,tecnico_reasignado")
    assert len(filas) == 2 and "Software,Alta" in filas[1]
    # el reentrenamiento existente lee ese archivo sin cambios
    assert len(re_mod.leer_correcciones()) == 1 and len(re_mod.correcciones_a_tickets(re_mod.leer_correcciones())) > 0


def test_tecnico_al_limite_no_recibe_el_ticket(cliente):
    primero = registrar(cliente, entrar(cliente, ANA))
    mejor = primero["tecnico"]["id"]
    with bd.SessionLocal() as s:  # el técnico más apto queda al límite: tiene 1 ticket abierto y su límite es 1
        s.get(Tecnico, mejor).limite_carga = 1
        s.commit()
    segundo = registrar(cliente, entrar(cliente, LUIS))
    assert segundo["tecnico"]["id"] != mejor
    ranking = cliente.get(f"/api/tickets/{segundo['id']}", headers=entrar(cliente, ADMIN)).json()["analisis"]["tecnicos_sugeridos"]
    ideal = next(t for t in ranking if t["id_tecnico"] == mejor)
    assert ideal["saturado"] and ranking[0]["id_tecnico"] == segundo["tecnico"]["id"] and not ranking[0]["saturado"]
    assert "límite" in (ideal["nota"] or "")


def test_tecnico_no_disponible_se_trata_como_saturado(cliente):
    mejor = registrar(cliente, entrar(cliente, ANA))["tecnico"]["id"]
    with bd.SessionLocal() as s:
        s.get(Tecnico, mejor).disponible = False
        s.commit()
    assert registrar(cliente, entrar(cliente, LUIS))["tecnico"]["id"] != mejor


def test_reasignacion_manual_y_automatica(cliente):
    t = registrar(cliente, entrar(cliente, ANA))
    ha = entrar(cliente, ADMIN)
    url = f"/api/tickets/{t['id']}/reasignar"
    auto = cliente.post(url, headers=ha, json={}).json()
    assert auto["tecnico"]["id"] != t["tecnico"]["id"]
    destino = "T01" if auto["tecnico"]["id"] != "T01" else "T02"
    man = cliente.post(url, headers=ha, json={"tecnico_id": destino}).json()
    assert man["tecnico"]["id"] == destino
    assert cliente.post(url, headers=ha, json={"tecnico_id": destino}).status_code == 422
    assert cliente.post(url, headers=ha, json={"tecnico_id": "T99"}).status_code == 422
    assert [h["accion"] for h in man["historial"]].count("reasignado") == 2
    hd = entrar(cliente, credencial_tecnico(destino))  # el técnico actual solo puede devolverlo (automático)
    assert cliente.post(url, headers=hd, json={"tecnico_id": "T03"}).status_code == 403
    assert cliente.post(url, headers=hd, json={}).json()["tecnico"]["id"] != destino
    assert cliente.post(url, headers=entrar(cliente, ANA), json={}).status_code == 403


def test_registro_de_ticket_menor_a_2_segundos(cliente):
    import time
    h = entrar(cliente, ANA)
    registrar(cliente, h, MONITOR)  # calentamiento
    tiempos = []
    for datos in (SERVIDOR, CORREO_CLAVE, MONITOR, SERVIDOR, CORREO_CLAVE):
        t0 = time.perf_counter()
        registrar(cliente, h, datos)
        tiempos.append(time.perf_counter() - t0)
    assert max(tiempos) < 2.0, tiempos
