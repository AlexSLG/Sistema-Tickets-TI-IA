"""Pruebas del sistema de tickets (Sprint 2): BD, usuarios, roles, tickets, IA, correcciones y panel.
Usan una BD SQLite temporal (ver conftest.py); los 25 tests del Sprint 1 siguen en test_api.py y test_datos.py."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.sistema import db as bd
from src.sistema import semilla
from src.sistema.modelos import Tecnico, Usuario
from src.sistema.seguridad import verificar_contrasena


@pytest.fixture(scope="module")
def cliente():
    from src.service.app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def bd_limpia(cliente):
    """Cada prueba parte de una BD vacía con usuarios y técnicos."""
    bd.Base.metadata.drop_all(bd.engine)
    bd.Base.metadata.create_all(bd.engine)
    with bd.SessionLocal() as s:
        semilla.sembrar(s, n_historial=0)
    yield


# ------------------------------------------------------------------ fase 1: BD y semilla
def test_semilla_crea_usuarios_y_tecnicos():
    with bd.SessionLocal() as s:
        usuarios = s.scalars(select(Usuario)).all()
        assert {u.rol for u in usuarios} == {"Administrador", "Usuario", "Soporte"}
        assert len(usuarios) == 1 + 3 + 8
        tecnicos = s.scalars(select(Tecnico).order_by(Tecnico.id)).all()
        assert [t.id for t in tecnicos] == [f"T0{i}" for i in range(1, 9)]
        assert tecnicos[0].aptitudes["Hardware"] == 5 and tecnicos[0].limite_carga > 0
        admin = s.scalar(select(Usuario).where(Usuario.correo == "admin@soporte.local"))
        assert verificar_contrasena("Admin123", admin.contrasena_hash) and not verificar_contrasena("otra", admin.contrasena_hash)
        assert not semilla.bd_vacia(s)
        assert any(u.correo == "marcela.vega@soporte.local" for u in usuarios)


# ------------------------------------------------------------------ fase 2: login, roles, usuarios
ADMIN = ("admin@soporte.local", "Admin123")
ANA = ("ana.torres@empresa.local", "Usuario123")
MARCELA = ("marcela.vega@soporte.local", "Soporte123")


def entrar(cliente, cred):
    r = cliente.post("/api/auth/login", json={"correo": cred[0], "contrasena": cred[1]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_login_correcto_e_incorrecto(cliente):
    r = cliente.post("/api/auth/login", json={"correo": ANA[0], "contrasena": ANA[1]})
    assert r.status_code == 200 and r.json()["usuario"]["rol"] == "Usuario" and r.json()["token"]
    assert cliente.post("/api/auth/login", json={"correo": ANA[0], "contrasena": "mala"}).status_code == 401
    assert cliente.post("/api/auth/login", json={"correo": "nadie@x.com", "contrasena": "x"}).status_code == 401
    soporte = cliente.post("/api/auth/login", json={"correo": MARCELA[0], "contrasena": MARCELA[1]}).json()["usuario"]
    assert soporte["rol"] == "Soporte" and soporte["tecnico_id"] == "T05"


def test_sin_token_401_y_token_invalido(cliente):
    assert cliente.get("/api/auth/yo").status_code == 401
    assert cliente.get("/api/auth/yo", headers={"Authorization": "Bearer basura"}).status_code == 401
    assert cliente.get("/api/auth/yo", headers=entrar(cliente, ANA)).json()["correo"] == ANA[0]


def test_usuario_no_entra_a_rutas_de_administrador(cliente):
    h = entrar(cliente, ANA)
    assert cliente.get("/api/usuarios", headers=h).status_code == 403
    assert cliente.post("/api/usuarios", headers=h, json={"nombre": "X Y", "correo": "x@y.com", "contrasena": "123456", "rol": "Administrador"}).status_code == 403
    assert cliente.get("/api/usuarios", headers=entrar(cliente, MARCELA)).status_code == 403
    assert len(cliente.get("/api/usuarios", headers=entrar(cliente, ADMIN)).json()) == 12


def test_administrador_gestiona_usuarios(cliente):
    h = entrar(cliente, ADMIN)
    r = cliente.post("/api/usuarios", headers=h, json={"nombre": "Pedro Gil", "correo": "Pedro.Gil@empresa.local", "contrasena": "Clave123", "rol": "Usuario"})
    assert r.status_code == 201 and r.json()["correo"] == "pedro.gil@empresa.local"
    assert cliente.post("/api/usuarios", headers=h, json={"nombre": "Pedro Gil", "correo": "pedro.gil@empresa.local", "contrasena": "Clave123"}).status_code == 422
    assert cliente.post("/api/usuarios", headers=h, json={"nombre": "Pedro", "correo": "no-es-correo", "contrasena": "Clave123"}).status_code == 422
    uid = r.json()["id"]
    entrar(cliente, ("pedro.gil@empresa.local", "Clave123"))
    assert cliente.put(f"/api/usuarios/{uid}", headers=h, json={"activo": False}).json()["activo"] is False
    assert cliente.post("/api/auth/login", json={"correo": "pedro.gil@empresa.local", "contrasena": "Clave123"}).status_code == 401
    cliente.put(f"/api/usuarios/{uid}", headers=h, json={"activo": True, "rol": "Soporte", "contrasena": "Nueva1234"})
    assert entrar(cliente, ("pedro.gil@empresa.local", "Nueva1234"))
    assert cliente.put("/api/usuarios/no-existe", headers=h, json={"activo": False}).status_code == 404


def test_administrador_no_puede_quitarse_el_rol(cliente):
    h = entrar(cliente, ADMIN)
    yo = cliente.get("/api/auth/yo", headers=h).json()
    assert cliente.put(f"/api/usuarios/{yo['id']}", headers=h, json={"rol": "Usuario"}).status_code == 422
    assert cliente.put(f"/api/usuarios/{yo['id']}", headers=h, json={"activo": False}).status_code == 422
