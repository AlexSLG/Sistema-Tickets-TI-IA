"""Modelos Pydantic de entrada y salida del sistema de tickets."""
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Rol = Literal["Usuario", "Soporte", "Administrador"]
Categoria = Literal["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"]
Prioridad = Literal["Baja", "Media", "Alta", "Crítica"]
Impacto = Literal["Bajo", "Medio", "Alto"]
Urgencia = Literal["Baja", "Media", "Alta"]
Estado = Literal["Abierto", "En progreso", "Resuelto", "Cerrado"]
CORREO = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ------------------------------------------------------------------ usuarios y sesión
class LoginEntrada(BaseModel):
    correo: str = Field(..., min_length=3, max_length=160)
    contrasena: str = Field(..., min_length=1, max_length=100)


class UsuarioSalida(BaseModel):
    id: str
    nombre: str
    correo: str
    rol: Rol
    activo: bool
    tecnico_id: Optional[str] = None


class LoginSalida(BaseModel):
    token: str
    usuario: UsuarioSalida


class UsuarioCrear(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120)
    correo: str = Field(..., pattern=CORREO, max_length=160)
    contrasena: str = Field(..., min_length=6, max_length=100)
    rol: Rol = "Usuario"


class UsuarioActualizar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=120)
    rol: Optional[Rol] = None
    activo: Optional[bool] = None
    contrasena: Optional[str] = Field(None, min_length=6, max_length=100)


# ------------------------------------------------------------------ técnicos
class TecnicoAdmin(BaseModel):
    id: str
    nombre: str
    area: str
    correo: str
    limite_carga: int
    disponible: bool
    aptitudes: Dict[str, int]
    carga: int


class TecnicoActualizar(BaseModel):
    limite_carga: Optional[int] = Field(None, ge=1, le=100)
    disponible: Optional[bool] = None
    aptitudes: Optional[Dict[Categoria, int]] = None


# ------------------------------------------------------------------ tickets
class TicketEntrada(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    descripcion: str = Field(..., min_length=3, max_length=5000)
    impacto: Impacto = "Medio"
    urgencia: Urgencia = "Media"
    usuarios_afectados: int = Field(1, ge=1, le=100000)


class TicketCrear(TicketEntrada):
    resuelto_con_solucion_rapida: bool = False


class EstadoEntrada(BaseModel):
    estado: Estado
    solucion: Optional[str] = Field(None, max_length=5000)


class ComentarioEntrada(BaseModel):
    texto: str = Field(..., min_length=1, max_length=3000)


class CorregirEntrada(BaseModel):
    categoria: Optional[Categoria] = None
    prioridad: Optional[Prioridad] = None


class ReasignarEntrada(BaseModel):
    tecnico_id: Optional[str] = None  # sin valor: reasignación automática
