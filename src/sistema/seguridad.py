"""Contraseñas (bcrypt), tokens JWT y dependencias de autenticación y roles."""
from datetime import timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.sistema import config
from src.sistema.db import get_db
from src.sistema.modelos import Usuario, ahora

_bearer = HTTPBearer(auto_error=False)


def hash_contrasena(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("ascii")


def verificar_contrasena(contrasena: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(contrasena.encode("utf-8"), hash_.encode("ascii"))
    except ValueError:
        return False


def crear_token(usuario: Usuario) -> str:
    cuerpo = {"sub": usuario.id, "rol": usuario.rol, "exp": ahora() + timedelta(hours=config.horas_expiracion())}
    return jwt.encode(cuerpo, config.secreto_jwt(), algorithm="HS256")


def leer_token(token: str) -> dict:
    return jwt.decode(token, config.secreto_jwt(), algorithms=["HS256"])


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> Usuario:
    if cred is None:
        raise HTTPException(401, "Debes iniciar sesión.")
    try:
        datos = leer_token(cred.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "La sesión expiró; inicia sesión de nuevo.")
    except jwt.PyJWTError:
        raise HTTPException(401, "Sesión no válida; inicia sesión de nuevo.")
    usuario = db.get(Usuario, datos.get("sub"))
    if usuario is None or not usuario.activo:
        raise HTTPException(401, "El usuario no existe o está desactivado.")
    return usuario


def requiere_rol(*roles):
    """Dependencia que exige que el usuario tenga uno de los roles indicados."""
    def comprobar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(403, f"No tienes permiso para esta acción (se requiere: {', '.join(roles)}).")
        return usuario
    return comprobar
