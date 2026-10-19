"""Configuración común de las pruebas: el sistema usa una BD SQLite temporal y nunca toca data/app.db."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="tickets_pruebas_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "pruebas.db").replace("\\", "/")
os.environ["SEMILLA_AUTOMATICA"] = "0"
os.environ["SECRETO_JWT"] = "secreto-de-pruebas"
