"""Datos iniciales del sistema. Se ejecuta solo si la BD está vacía.

    python -m src.sistema.semilla              # carga los datos si la BD está vacía
    python -m src.sistema.semilla --reiniciar  # borra todo y vuelve a crear
"""
import argparse
import unicodedata

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sistema import db as bd
from src.sistema.modelos import Tecnico, Usuario
from src.sistema.seguridad import hash_contrasena

RAIZ = bd.config.RAIZ
CATEGORIAS = ["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"]

ADMIN = ("Administrador del sistema", "admin@soporte.local", "Admin123")
SOLICITANTES = [("Ana Torres", "ana.torres@empresa.local"), ("Luis Paz", "luis.paz@empresa.local"), ("Rosa Campos", "rosa.campos@empresa.local")]
CLAVE_USUARIO, CLAVE_SOPORTE = "Usuario123", "Soporte123"


def _sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def correo_soporte(nombre):
    partes = _sin_acentos(nombre).lower().split()
    return f"{partes[0]}.{partes[-1]}@soporte.local"


def bd_vacia(db: Session) -> bool:
    return db.scalar(select(Usuario.id).limit(1)) is None


def sembrar_usuarios_y_tecnicos(db: Session):
    """Administrador, 3 solicitantes y un técnico por fila de data/processed/tecnicos.csv."""
    db.add(Usuario(nombre=ADMIN[0], correo=ADMIN[1], contrasena_hash=hash_contrasena(ADMIN[2]), rol="Administrador"))
    for nombre, correo in SOLICITANTES:
        db.add(Usuario(nombre=nombre, correo=correo, contrasena_hash=hash_contrasena(CLAVE_USUARIO), rol="Usuario"))
    tec = pd.read_csv(RAIZ / "data" / "processed" / "tecnicos.csv")
    hash_soporte = hash_contrasena(CLAVE_SOPORTE)  # misma clave para todos: se calcula una sola vez
    for r in tec.itertuples():
        u = Usuario(nombre=r.nombre, correo=correo_soporte(r.nombre), contrasena_hash=hash_soporte, rol="Soporte")
        db.add(u)
        db.flush()
        db.add(Tecnico(id=r.id_tecnico, usuario_id=u.id, nombre=r.nombre, area=r.area, limite_carga=int(r.limite_carga), disponible=True,
                       aptitudes={c: int(getattr(r, f"aptitud_{c.lower()}")) for c in CATEGORIAS}))
    db.commit()


def credenciales():
    """Texto con las credenciales de demostración."""
    with bd.SessionLocal() as db:
        tecnicos = db.scalars(select(Tecnico).order_by(Tecnico.id)).all()
        lineas = ["Credenciales de demostración:", f"  Administrador: {ADMIN[1]} / {ADMIN[2]}"]
        lineas += [f"  Usuario:       {c} / {CLAVE_USUARIO}" for _, c in SOLICITANTES]
        lineas += [f"  Soporte {t.id}:   {t.usuario.correo} / {CLAVE_SOPORTE}  ({t.nombre}, {t.area})" for t in tecnicos]
        return "\n".join(lineas)


def sembrar(db: Session, n_historial=60, verbose=False):
    sembrar_usuarios_y_tecnicos(db)
    if n_historial:
        from src.sistema.semilla_historial import sembrar_historial
        sembrar_historial(db, n_historial, verbose)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reiniciar", action="store_true", help="borra todas las tablas y las vuelve a crear")
    ap.add_argument("--sin-historial", action="store_true", help="solo usuarios y técnicos")
    a = ap.parse_args()
    bd.iniciar()
    if a.reiniciar:
        bd.Base.metadata.drop_all(bd.engine)
        bd.Base.metadata.create_all(bd.engine)
    with bd.SessionLocal() as db:
        if bd_vacia(db):
            sembrar(db, 0 if a.sin_historial else 60, verbose=True)
            print("Datos iniciales cargados.")
        else:
            print("La base de datos ya tiene datos (usa --reiniciar para empezar de cero).")
    print(credenciales())


if __name__ == "__main__":
    main()
