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
