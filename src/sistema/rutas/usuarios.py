"""Administración de usuarios (solo Administrador).

Un usuario con rol Soporte es técnico: al crearlo (o al pasarlo a Soporte) se le crea su ficha de técnico con valores
iniciales que el Administrador puede ajustar en la pantalla Técnicos. Si deja de ser Soporte o se desactiva, su ficha queda
como no disponible y la IA deja de asignarle tickets nuevos.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sistema.db import get_db
from src.sistema.esquemas import UsuarioActualizar, UsuarioCrear, UsuarioSalida
from src.models.comun import CATEGORIAS
from src.sistema.modelos import Tecnico, Usuario
from src.sistema.rutas.auth import usuario_salida
from src.sistema.seguridad import hash_contrasena, requiere_rol

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])
admin = requiere_rol("Administrador")
AREA_NUEVO, LIMITE_NUEVO, APTITUD_NUEVO = "Mesa de ayuda", 8, 3


def sincronizar_tecnico(db: Session, u: Usuario, reactivar=False):
    """Crea la ficha de técnico de un usuario Soporte o actualiza su disponibilidad según su rol y estado."""
    t = db.scalar(select(Tecnico).where(Tecnico.usuario_id == u.id))
    es_tecnico = u.rol == "Soporte" and u.activo
    if t is None and u.rol == "Soporte":
        numeros = [int(i[1:]) for i in db.scalars(select(Tecnico.id)) if i[1:].isdigit()]
        t = Tecnico(id=f"T{max(numeros, default=0) + 1:02d}", usuario_id=u.id, nombre=u.nombre, area=AREA_NUEVO, limite_carga=LIMITE_NUEVO,
                    disponible=es_tecnico, aptitudes={c: APTITUD_NUEVO for c in CATEGORIAS})
        db.add(t)
    elif t is not None:
        t.nombre = u.nombre
        if not es_tecnico:
            t.disponible = False
        elif reactivar:  # vuelve a ser Soporte o se reactiva su cuenta; si solo cambia el nombre, se respeta la disponibilidad fijada
            t.disponible = True


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
    db.flush()
    sincronizar_tecnico(db, u)
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
    antes = (u.rol, u.activo)
    if e.rol is not None:
        u.rol = e.rol
    if e.activo is not None:
        u.activo = e.activo
    if e.contrasena:
        u.contrasena_hash = hash_contrasena(e.contrasena)
    if e.rol is not None or e.activo is not None or e.nombre is not None:
        sincronizar_tecnico(db, u, reactivar=(u.rol, u.activo) != antes)
    db.commit()
    return usuario_salida(db, u)
