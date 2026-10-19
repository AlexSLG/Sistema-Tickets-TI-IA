"""Tablas ORM (versión simplificada de docs/modelo_datos.md). Tipos portables entre SQLite y PostgreSQL."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.sistema.db import Base

ROLES = ("Usuario", "Soporte", "Administrador")
ESTADOS = ("Abierto", "En progreso", "Resuelto", "Cerrado")
ESTADOS_ABIERTOS = ("Abierto", "En progreso")


def ahora():
    return datetime.now(timezone.utc)


def nuevo_id():
    return str(uuid.uuid4())


class FechaUTC(TypeDecorator):
    """Guarda siempre UTC y devuelve fechas con zona horaria (SQLite no conserva la zona)."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, valor, dialect):
        if valor is None:
            return None
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        valor = valor.astimezone(timezone.utc)
        return valor.replace(tzinfo=None) if dialect.name == "sqlite" else valor

    def process_result_value(self, valor, dialect):
        if valor is not None and valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    contrasena_hash: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en = mapped_column(FechaUTC, default=ahora)


class Tecnico(Base):
    __tablename__ = "tecnicos"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)  # T01…
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    area: Mapped[str] = mapped_column(String(120))
    limite_carga: Mapped[int] = mapped_column(Integer)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True)
    aptitudes = mapped_column(JSON)  # {"Hardware": 5, …}
    usuario = relationship("Usuario")


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    codigo: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text)
    impacto: Mapped[str] = mapped_column(String(10))
    urgencia: Mapped[str] = mapped_column(String(10))
    usuarios_afectados: Mapped[int] = mapped_column(Integer, default=1)
    solicitante_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), index=True)
    tecnico_id: Mapped[str | None] = mapped_column(ForeignKey("tecnicos.id"), nullable=True, index=True)
    categoria: Mapped[str] = mapped_column(String(20))
    prioridad: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(15), default="Abierto", index=True)
    resuelto_con_solucion_rapida: Mapped[bool] = mapped_column(Boolean, default=False)
    solucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en = mapped_column(FechaUTC, default=ahora)
    actualizado_en = mapped_column(FechaUTC, default=ahora)
    resuelto_en = mapped_column(FechaUTC, nullable=True)
    cerrado_en = mapped_column(FechaUTC, nullable=True)
    solicitante = relationship("Usuario", foreign_keys=[solicitante_id])
    tecnico = relationship("Tecnico")
    analisis = relationship("AnalisisIA", uselist=False, back_populates="ticket", cascade="all, delete-orphan")
    comentarios = relationship("Comentario", order_by="Comentario.creado_en", cascade="all, delete-orphan")
    historial = relationship("Historial", order_by="Historial.creado_en", cascade="all, delete-orphan")
    correcciones = relationship("Correccion", order_by="Correccion.creado_en", cascade="all, delete-orphan")


class AnalisisIA(Base):
    __tablename__ = "analisis_ia"
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), primary_key=True)
    version_modelos: Mapped[str] = mapped_column(String(20))
    categoria_sugerida: Mapped[str] = mapped_column(String(20))
    prob_categoria = mapped_column(JSON)
    prioridad_sugerida: Mapped[str] = mapped_column(String(10))
    prob_prioridad = mapped_column(JSON)
    tecnicos_sugeridos = mapped_column(JSON)  # ranking completo de Servicio.asignar
    solucion_rapida = mapped_column(JSON, nullable=True)
    similares = mapped_column(JSON)
    tiempo_ms: Mapped[float] = mapped_column()
    ticket = relationship("Ticket", back_populates="analisis")


class Comentario(Base):
    __tablename__ = "comentarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), index=True)
    autor_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    texto: Mapped[str] = mapped_column(Text)
    creado_en = mapped_column(FechaUTC, default=ahora)
    autor = relationship("Usuario")


class Historial(Base):
    __tablename__ = "historial"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), index=True)
    usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    accion: Mapped[str] = mapped_column(String(20))  # creado, estado, asignado, reasignado, corregido, comentario
    detalle: Mapped[str] = mapped_column(Text, default="")
    creado_en = mapped_column(FechaUTC, default=ahora)
    usuario = relationship("Usuario")


class Correccion(Base):
    __tablename__ = "correcciones"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), index=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    categoria_ia: Mapped[str] = mapped_column(String(20))
    categoria_correcta: Mapped[str] = mapped_column(String(20))
    prioridad_ia: Mapped[str] = mapped_column(String(10))
    prioridad_correcta: Mapped[str] = mapped_column(String(10))
    version_modelos: Mapped[str] = mapped_column(String(20))
    creado_en = mapped_column(FechaUTC, default=ahora)
    usuario = relationship("Usuario")
