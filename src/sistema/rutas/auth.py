"""Inicio de sesión y datos del usuario autenticado."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sistema.db import get_db
from src.sistema.esquemas import LoginEntrada, LoginSalida, UsuarioSalida
from src.sistema.modelos import Tecnico, Usuario
from src.sistema.seguridad import crear_token, usuario_actual, verificar_contrasena

router = APIRouter(prefix="/api/auth", tags=["autenticación"])


def usuario_salida(db: Session, u: Usuario) -> UsuarioSalida:
    tecnico = db.scalar(select(Tecnico.id).where(Tecnico.usuario_id == u.id))
    return UsuarioSalida(id=u.id, nombre=u.nombre, correo=u.correo, rol=u.rol, activo=u.activo, tecnico_id=tecnico)


@router.post("/login", response_model=LoginSalida, summary="Iniciar sesión")
def login(e: LoginEntrada, db: Session = Depends(get_db)):
    u = db.scalar(select(Usuario).where(Usuario.correo == e.correo.strip().lower()))
    if u is None or not verificar_contrasena(e.contrasena, u.contrasena_hash):
        raise HTTPException(401, "Correo o contraseña incorrectos.")
    if not u.activo:
        raise HTTPException(401, "El usuario está desactivado; contacta al administrador.")
    return LoginSalida(token=crear_token(u), usuario=usuario_salida(db, u))


@router.get("/yo", response_model=UsuarioSalida, summary="Usuario de la sesión actual")
def yo(u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return usuario_salida(db, u)
