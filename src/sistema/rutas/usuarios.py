"""Administración de usuarios (solo Administrador)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sistema.db import get_db
from src.sistema.esquemas import UsuarioActualizar, UsuarioCrear, UsuarioSalida
from src.sistema.modelos import Usuario
from src.sistema.rutas.auth import usuario_salida
from src.sistema.seguridad import hash_contrasena, requiere_rol

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])
admin = requiere_rol("Administrador")


@router.get("", response_model=list[UsuarioSalida], summary="Listar usuarios")
def listar(_: Usuario = Depends(admin), db: Session = Depends(get_db)):
    return [usuario_salida(db, u) for u in db.scalars(select(Usuario).order_by(Usuario.rol, Usuario.nombre))]


@router.post("", response_model=UsuarioSalida, status_code=201, summary="Crear usuario")
def crear(e: UsuarioCrear, _: Usuario = Depends(admin), db: Session = Depends(get_db)):
    correo = e.correo.strip().lower()
    if db.scalar(select(Usuario.id).where(Usuario.correo == correo)):
        raise HTTPException(422, "Ya existe un usuario con ese correo.")
    u = Usuario(nombre=e.nombre.strip(), correo=correo, contrasena_hash=hash_contrasena(e.contrasena), rol=e.rol)
    db.add(u)
    db.commit()
    return usuario_salida(db, u)


@router.put("/{usuario_id}", response_model=UsuarioSalida, summary="Cambiar rol, estado o contraseña")
def actualizar(usuario_id: str, e: UsuarioActualizar, yo: Usuario = Depends(admin), db: Session = Depends(get_db)):
    u = db.get(Usuario, usuario_id)
    if u is None:
        raise HTTPException(404, "Usuario no encontrado.")
    if u.id == yo.id and ((e.rol and e.rol != u.rol) or e.activo is False):
        raise HTTPException(422, "No puedes quitarte tu propio rol de administrador ni desactivar tu cuenta.")
    if e.nombre is not None:
        u.nombre = e.nombre.strip()
    if e.rol is not None:
        u.rol = e.rol
    if e.activo is not None:
        u.activo = e.activo
    if e.contrasena:
        u.contrasena_hash = hash_contrasena(e.contrasena)
    db.commit()
    return usuario_salida(db, u)
