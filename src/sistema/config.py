"""Configuración del sistema (variables de entorno con valores por defecto para trabajar en local)."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def url_bd():
    """DATABASE_URL; sin configurar, SQLite en data/app.db (no hace falta instalar nada)."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{(RAIZ / 'data' / 'app.db').as_posix()}"
    return url


def secreto_jwt():
    return os.getenv("SECRETO_JWT", "clave-de-desarrollo-cambiar-en-produccion")


def horas_expiracion():
    return int(os.getenv("HORAS_EXPIRACION_TOKEN", "8"))


def semilla_automatica():
    """Si es verdadero, al iniciar con la BD vacía se cargan los datos de demostración."""
    return os.getenv("SEMILLA_AUTOMATICA", "1") != "0"
