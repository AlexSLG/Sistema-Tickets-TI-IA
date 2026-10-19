"""Configuración común de las pruebas: el sistema usa una BD SQLite temporal y nunca toca data/app.db."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="tickets_pruebas_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "pruebas.db").replace("\\", "/")
os.environ["SEMILLA_AUTOMATICA"] = "0"
os.environ["SECRETO_JWT"] = "secreto-de-pruebas-con-longitud-suficiente-1234"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="module")
def cliente():
    from src.service.app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def bd_limpia(cliente):
    """BD vacía con usuarios y técnicos (sin historial de tickets) para cada prueba del sistema."""
    from src.sistema import db as bd, semilla
    bd.Base.metadata.drop_all(bd.engine)
    bd.Base.metadata.create_all(bd.engine)
    with bd.SessionLocal() as s:
        semilla.sembrar(s, n_historial=0)
    yield
