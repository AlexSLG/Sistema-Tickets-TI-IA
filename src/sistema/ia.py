"""Puente entre el sistema de tickets y los modelos (clase Servicio de src/service/inferencia.py).

Los modelos no se cargan dos veces: se usa el mismo objeto en memoria que la API de inferencia. Las cargas, límites,
aptitudes y disponibilidad de los técnicos salen de la base de datos (no del estado de la página de prueba).
"""
import csv
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.comun import CATEGORIAS, PRIORIDADES
from src.sistema.modelos import ESTADOS_ABIERTOS, AnalisisIA, Tecnico, Ticket


def servicio():
    from src.service.app import servicio as obtener  # importación diferida: evita un ciclo con app.py
    return obtener()


def contexto_tecnicos(db: Session):
    """Cargas reales (tickets Abiertos o En progreso), límites, aptitudes y no disponibles, tal como están en la BD."""
    tecnicos = db.scalars(select(Tecnico).order_by(Tecnico.id)).all()
    cuenta = dict(db.execute(select(Ticket.tecnico_id, func.count()).where(Ticket.estado.in_(ESTADOS_ABIERTOS), Ticket.tecnico_id.is_not(None))
                             .group_by(Ticket.tecnico_id)).all())
    return {
        "cargas": {t.id: int(cuenta.get(t.id, 0)) for t in tecnicos},
        "limites": {t.id: t.limite_carga for t in tecnicos},
        "aptitudes": {t.id: t.aptitudes for t in tecnicos},
        "no_disponibles": [t.id for t in tecnicos if not t.disponible],
    }


def analizar(db: Session, titulo, descripcion, impacto, urgencia, usuarios_afectados):
    """Análisis completo con la carga real de los técnicos."""
    return servicio().analizar(titulo, descripcion, impacto, urgencia, usuarios_afectados, **contexto_tecnicos(db))


def ranking(db: Session, categoria, prioridad):
    """Ranking de técnicos para una categoría y prioridad con el estado actual de la BD."""
    return servicio().asignar(CATEGORIAS.index(categoria), PRIORIDADES.index(prioridad), **contexto_tecnicos(db))


def elegir_tecnico(lista, excluir=None):
    """Primer técnico del ranking que está disponible y no es el excluido. En un ranking con técnicos saturados, el primero ya es
    el de mejor puntaje con capacidad (o el de menor ocupación si todos están al límite)."""
    for t in lista:
        if t["id_tecnico"] == excluir or (t["nota"] or "").startswith("No disponible"):
            continue
        return t
    return None


def guardar_analisis(db: Session, ticket: Ticket, r: dict):
    db.add(AnalisisIA(ticket_id=ticket.id, version_modelos=r["version_modelos"], categoria_sugerida=r["clasificacion"]["categoria"],
                      prob_categoria=r["clasificacion"]["probabilidades"], prioridad_sugerida=r["prioridad"]["prioridad"],
                      prob_prioridad=r["prioridad"]["probabilidades"], tecnicos_sugeridos=r["tecnicos"], solucion_rapida=r["solucion_rapida"],
                      similares=r["similares"], tiempo_ms=r["tiempo_ms"]))


def agregar_a_correcciones_csv(ticket: Ticket, categoria: str, prioridad: str):
    """Añade una fila a data/correcciones.csv con las columnas que usa src/training/reentrenar.py, para que el reentrenamiento
    existente la incluya sin cambios."""
    from src.training import reentrenar
    ruta = reentrenar.CORRECCIONES
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists() or ruta.stat().st_size == 0
    with open(ruta, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(reentrenar.COLUMNAS)
        w.writerow([ticket.titulo, ticket.descripcion, categoria, prioridad, "", ticket.impacto, ticket.urgencia, ticket.usuarios_afectados,
                    datetime.now().strftime("%Y-%m-%d %H:%M")])
