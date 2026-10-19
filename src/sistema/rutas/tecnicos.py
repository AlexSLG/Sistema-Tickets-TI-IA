"""Administración de técnicos: límite de carga, disponibilidad y aptitudes (HU15). Los cambios los usa la asignación de la IA."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sistema import ia
from src.sistema.db import get_db
from src.sistema.esquemas import TecnicoActualizar, TecnicoAdmin
from src.sistema.modelos import Tecnico, Usuario
from src.sistema.seguridad import requiere_rol

router = APIRouter(prefix="/api/admin/tecnicos", tags=["administración de técnicos"])
admin = requiere_rol("Administrador")


def salida(t: Tecnico, carga: int) -> TecnicoAdmin:
    return TecnicoAdmin(id=t.id, nombre=t.nombre, area=t.area, correo=t.usuario.correo, limite_carga=t.limite_carga, disponible=t.disponible,
                        aptitudes=t.aptitudes, carga=carga)


@router.get("", response_model=list[TecnicoAdmin], summary="Técnicos con su carga actual")
def listar(_: Usuario = Depends(admin), db: Session = Depends(get_db)):
    cargas = ia.contexto_tecnicos(db)["cargas"]
    return [salida(t, cargas.get(t.id, 0)) for t in db.scalars(select(Tecnico).order_by(Tecnico.id))]


@router.put("/{tecnico_id}", response_model=TecnicoAdmin, summary="Cambiar límite, disponibilidad o aptitudes")
def actualizar(tecnico_id: str, e: TecnicoActualizar, _: Usuario = Depends(admin), db: Session = Depends(get_db)):
    t = db.get(Tecnico, tecnico_id)
    if t is None:
        raise HTTPException(404, "Técnico no encontrado.")
    if e.limite_carga is not None:
        t.limite_carga = e.limite_carga
    if e.disponible is not None:
        t.disponible = e.disponible
    if e.aptitudes:
        if any(not 1 <= v <= 5 for v in e.aptitudes.values()):
            raise HTTPException(422, "Las aptitudes deben estar entre 1 y 5.")
        t.aptitudes = {**t.aptitudes, **e.aptitudes}  # se asigna un diccionario nuevo para que SQLAlchemy detecte el cambio
    db.commit()
    return salida(t, ia.contexto_tecnicos(db)["cargas"].get(t.id, 0))
