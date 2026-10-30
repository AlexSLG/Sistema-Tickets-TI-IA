"""Soluciones rápidas administrables (HU26).

Soporte o un Administrador guardan como solución rápida lo aprendido en un ticket Resuelto o Cerrado; el Administrador las edita y
las activa o desactiva. Tras cada cambio se reconstruye en memoria solo el índice de soluciones del servicio, sin reiniciar: la
solución se sugiere de inmediato a un ticket que se parezca a sus frases.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.models import catalogo_soluciones as catalogo
from src.sistema import ia
from src.sistema.db import get_db
from src.sistema.esquemas import SolucionActualizar, SolucionCrear
from src.sistema.modelos import Historial, Ticket, Usuario
from src.sistema.rutas.tickets import puede_ver
from src.sistema.seguridad import requiere_rol

router = APIRouter(prefix="/api/soluciones", tags=["soluciones rápidas"])
staff = requiere_rol("Soporte", "Administrador")
admin = requiere_rol("Administrador")


def _limpiar(lista):
    vistas, salida = set(), []
    for x in lista:
        x = " ".join(str(x).split())
        if x and x.lower() not in vistas:
            vistas.add(x.lower())
            salida.append(x[:500])
    if not salida:
        raise HTTPException(422, "Las frases de ejemplo y los pasos no pueden estar vacíos.")
    return salida


def _aplicar(soluciones):
    catalogo.guardar(soluciones)
    ia.servicio().recargar_soluciones()


@router.get("", summary="Listar las soluciones rápidas (Soporte y Administrador)")
def listar(_: Usuario = Depends(staff)):
    return [{**s, "activa": s.get("activa", True)} for s in catalogo.leer()]


@router.post("", status_code=201, summary="Guardar una solución rápida (desde un ticket Resuelto o Cerrado)")
def crear(e: SolucionCrear, u: Usuario = Depends(staff), db: Session = Depends(get_db)):
    ticket = None
    if e.ticket_id:
        ticket = db.get(Ticket, e.ticket_id)
        if ticket is None:
            raise HTTPException(404, "Ticket no encontrado.")
        if not puede_ver(db, u, ticket):
            raise HTTPException(403, "Solo puedes guardar soluciones de tickets que atiendes.")
        if ticket.estado not in ("Resuelto", "Cerrado"):
            raise HTTPException(422, "Solo se puede guardar como solución rápida un ticket Resuelto o Cerrado.")
    soluciones = catalogo.leer()
    nueva = {"id": catalogo.siguiente_id(soluciones), "categoria": e.categoria, "problema": " ".join(e.problema.split()),
             "frases_ejemplo": _limpiar(e.frases_ejemplo), "pasos": _limpiar(e.pasos), "activa": True,
             "origen": "ticket" if ticket else "manual", "ticket_origen": ticket.codigo if ticket else None,
             "creada_por": u.nombre, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")}
    _aplicar(soluciones + [nueva])
    if ticket:
        db.add(Historial(ticket_id=ticket.id, usuario_id=u.id, accion="solución rápida", detalle=f"Guardado como {nueva['id']}: {nueva['problema']}"))
        db.commit()
    return nueva


@router.put("/{solucion_id}", summary="Editar, activar o desactivar una solución rápida (Administrador)")
def actualizar(solucion_id: str, e: SolucionActualizar, _: Usuario = Depends(admin)):
    soluciones = catalogo.leer()
    s = next((x for x in soluciones if x["id"] == solucion_id), None)
    if s is None:
        raise HTTPException(404, "Solución rápida no encontrada.")
    if e.problema is not None:
        s["problema"] = " ".join(e.problema.split())
    if e.categoria is not None:
        s["categoria"] = e.categoria
    if e.frases_ejemplo is not None:
        s["frases_ejemplo"] = _limpiar(e.frases_ejemplo)
    if e.pasos is not None:
        s["pasos"] = _limpiar(e.pasos)
    if e.activa is not None:
        s["activa"] = e.activa
    _aplicar(soluciones)
    return {**s, "activa": s.get("activa", True)}
