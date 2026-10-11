"""Esquemas (entrada y salida) de la API de inferencia."""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Categoria = Literal["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"]
Prioridad = Literal["Baja", "Media", "Alta", "Crítica"]
Impacto = Literal["Bajo", "Medio", "Alto"]
Urgencia = Literal["Baja", "Media", "Alta"]


class TicketEntrada(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200, examples=["No puedo conectarme a la VPN"])
    descripcion: str = Field(..., min_length=3, max_length=5000, examples=["Desde esta mañana el cliente VPN da error al conectar desde casa."])
    impacto: Impacto = "Medio"
    urgencia: Urgencia = "Media"
    usuarios_afectados: int = Field(1, ge=1, le=100000)


class Clasificacion(BaseModel):
    categoria: Categoria
    probabilidades: Dict[str, float]


class PrioridadSalida(BaseModel):
    prioridad: Prioridad
    probabilidades: Dict[str, float]


class TecnicoSalida(BaseModel):
    id_tecnico: str
    nombre: str
    area: str
    aptitud: int
    carga: int
    limite_carga: int
    saturado: bool
    puntaje: float
    recomendado: bool
    nota: Optional[str] = None


class SolucionRapida(BaseModel):
    id: str
    categoria: str
    problema: str
    pasos: List[str]
    similitud: float


class CasoSimilar(BaseModel):
    id: str
    titulo: str
    descripcion: str
    categoria: str
    prioridad: str
    fuente: str
    similitud: float
    solucion: Optional[str] = None


class AnalisisSalida(BaseModel):
    clasificacion: Clasificacion
    prioridad: PrioridadSalida
    tecnicos: List[TecnicoSalida]
    solucion_rapida: Optional[SolucionRapida] = None
    similares: List[CasoSimilar]
    version_modelos: str
    tiempo_ms: float


class SimilaresEntrada(BaseModel):
    texto: str = Field(..., min_length=3, max_length=5000)
    k: int = Field(5, ge=1, le=20)


class SimilaresSalida(BaseModel):
    similares: List[CasoSimilar]
    tiempo_ms: float


class CargasEntrada(BaseModel):
    cargas: Dict[str, int] = Field(..., examples=[{"T07": 14, "T08": 3}])


class TecnicoEstado(BaseModel):
    id_tecnico: str
    nombre: str
    area: str
    limite_carga: int
    carga: int
    aptitudes: Dict[str, int]


class CorreccionEntrada(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    descripcion: str = Field(..., min_length=3, max_length=5000)
    categoria_corregida: Categoria
    prioridad_corregida: Prioridad
    tecnico_reasignado: Optional[str] = None
    impacto: Optional[Impacto] = None
    urgencia: Optional[Urgencia] = None
    usuarios_afectados: Optional[int] = Field(None, ge=1, le=100000)


class ReentrenarEntrada(BaseModel):
    epocas: int = Field(6, ge=1, le=30)
    sincrono: bool = False


class ActivarEntrada(BaseModel):
    version: str
