"""Conexión a la base de datos (SQLAlchemy 2). SQLite en local, PostgreSQL en Docker."""
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.sistema import config


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def iniciar(url=None, reintentos=20, espera=2.0):
    """Crea el motor, espera a que la BD responda (en Docker tarda unos segundos) y crea las tablas."""
    global engine, SessionLocal
    url = url or config.url_bd()
    args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if engine is not None:
        engine.dispose()
    engine = create_engine(url, connect_args=args, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    for intento in range(reintentos):
        try:
            with engine.connect() as c:
                c.execute(text("SELECT 1"))
            break
        except Exception:
            if intento == reintentos - 1:
                raise
            time.sleep(espera)
    from src.sistema import modelos  # noqa: F401  (registra las tablas)
    Base.metadata.create_all(engine)
    return engine


def get_db():
    if SessionLocal is None:
        iniciar()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
