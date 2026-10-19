"""Tickets: registro con IA, listas, estados, comentarios, confirmar o reabrir, corrección y reasignación."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.sistema import ia
from src.sistema.db import get_db
from src.sistema.esquemas import (ComentarioEntrada, CorregirEntrada, EstadoEntrada, ReasignarEntrada, TicketCrear, TicketEntrada)
from src.sistema.modelos import ESTADOS_ABIERTOS, Comentario, Correccion, Historial, Tecnico, Ticket, Usuario, ahora
from src.sistema.seguridad import requiere_rol, usuario_actual

router = APIRouter(prefix="/api/tickets", tags=["tickets"])
ORDEN_PRIORIDAD = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
TRANSICIONES = {"Abierto": ["En progreso"], "En progreso": ["Resuelto"]}
staff = requiere_rol("Soporte", "Administrador")


# ------------------------------------------------------------------ utilidades
def tecnico_de(db: Session, u: Usuario):
    return db.scalar(select(Tecnico).where(Tecnico.usuario_id == u.id))


def codigo_siguiente(db: Session) -> str:
    ultimo = db.scalar(select(func.max(Ticket.codigo)))
    return f"TK-{(int(ultimo.split('-')[1]) + 1) if ultimo else 1:04d}"


def anotar(db: Session, t: Ticket, u: Usuario | None, accion: str, detalle: str = ""):
    db.add(Historial(ticket_id=t.id, usuario_id=u.id if u else None, accion=accion, detalle=detalle))


def puede_ver(db: Session, u: Usuario, t: Ticket) -> bool:
    if u.rol == "Administrador" or t.solicitante_id == u.id:
        return True
    if u.rol == "Soporte":
        tec = tecnico_de(db, u)
        return tec is not None and t.tecnico_id == tec.id
    return False


def cargar(db: Session, u: Usuario, ticket_id: str) -> Ticket:
    t = db.get(Ticket, ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket no encontrado.")
    if not puede_ver(db, u, t):
        raise HTTPException(403, "No tienes permiso sobre este ticket.")
    return t


def exigir_gestion(db: Session, u: Usuario, t: Ticket):
    """Administrador, o Soporte con el ticket asignado."""
    if u.rol == "Administrador":
        return
    tec = tecnico_de(db, u)
    if u.rol != "Soporte" or tec is None or t.tecnico_id != tec.id:
        raise HTTPException(403, "Solo el técnico asignado o un administrador pueden hacer esto.")


def resumen(t: Ticket) -> dict:
    return {"id": t.id, "codigo": t.codigo, "titulo": t.titulo, "categoria": t.categoria, "prioridad": t.prioridad, "estado": t.estado,
            "impacto": t.impacto, "urgencia": t.urgencia, "usuarios_afectados": t.usuarios_afectados,
            "solicitante": {"id": t.solicitante_id, "nombre": t.solicitante.nombre},
            "tecnico": {"id": t.tecnico.id, "nombre": t.tecnico.nombre, "area": t.tecnico.area} if t.tecnico else None,
            "resuelto_con_solucion_rapida": t.resuelto_con_solucion_rapida, "creado_en": t.creado_en, "actualizado_en": t.actualizado_en,
            "resuelto_en": t.resuelto_en, "cerrado_en": t.cerrado_en}


def detalle(u: Usuario, t: Ticket) -> dict:
    d = resumen(t)
    d["descripcion"] = t.descripcion
    d["solucion"] = t.solucion
    d["comentarios"] = [{"id": c.id, "autor": c.autor.nombre, "rol": c.autor.rol, "texto": c.texto, "creado_en": c.creado_en} for c in t.comentarios]
    ocultas = ("corregido",) if u.rol == "Usuario" else ()
    d["historial"] = [{"accion": h.accion, "detalle": h.detalle, "usuario": h.usuario.nombre if h.usuario else "Sistema", "creado_en": h.creado_en}
                      for h in t.historial if h.accion not in ocultas]
    if u.rol != "Usuario":  # el análisis de la IA solo lo ven Soporte y Administrador
        a = t.analisis
        d["analisis"] = None if a is None else {
            "version_modelos": a.version_modelos, "categoria_sugerida": a.categoria_sugerida, "prob_categoria": a.prob_categoria,
            "prioridad_sugerida": a.prioridad_sugerida, "prob_prioridad": a.prob_prioridad, "tecnicos_sugeridos": a.tecnicos_sugeridos,
            "solucion_rapida": a.solucion_rapida, "similares": a.similares, "tiempo_ms": a.tiempo_ms}
        d["correcciones"] = [{"categoria_ia": c.categoria_ia, "categoria_correcta": c.categoria_correcta, "prioridad_ia": c.prioridad_ia,
                              "prioridad_correcta": c.prioridad_correcta, "usuario": c.usuario.nombre, "version_modelos": c.version_modelos,
                              "creado_en": c.creado_en} for c in t.correcciones]
    return d


# ------------------------------------------------------------------ análisis y registro
@router.post("/analizar", summary="Analizar un ticket antes de guardarlo (categoría, prioridad y solución rápida)")
def analizar(e: TicketEntrada, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    r = ia.analizar(db, e.titulo, e.descripcion, e.impacto, e.urgencia, e.usuarios_afectados)
    if u.rol == "Usuario":  # el solicitante no ve el ranking de técnicos ni los similares
        r = {k: v for k, v in r.items() if k not in ("tecnicos", "similares")}
    return r


@router.post("", status_code=201, summary="Registrar un ticket")
def crear(e: TicketCrear, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    r = ia.analizar(db, e.titulo, e.descripcion, e.impacto, e.urgencia, e.usuarios_afectados)
    cat, pri = r["clasificacion"]["categoria"], r["prioridad"]["prioridad"]
    rapida = r["solucion_rapida"]
    t = Ticket(codigo=codigo_siguiente(db), titulo=e.titulo.strip(), descripcion=e.descripcion.strip(), impacto=e.impacto, urgencia=e.urgencia,
               usuarios_afectados=e.usuarios_afectados, solicitante_id=u.id, categoria=cat, prioridad=pri, estado="Abierto")
    db.add(t)
    db.flush()
    ia.guardar_analisis(db, t, r)
    anotar(db, t, u, "creado", f"Clasificado como {cat}, prioridad {pri}")
    if e.resuelto_con_solucion_rapida:
        if not rapida:
            raise HTTPException(422, "No hay una solución rápida para este ticket; regístralo normalmente.")
        t.estado, t.resuelto_con_solucion_rapida = "Cerrado", True
        t.solucion = f"Solución rápida «{rapida['problema']}»: " + " ".join(f"{i}. {p}" for i, p in enumerate(rapida["pasos"], 1))
        t.resuelto_en = t.cerrado_en = ahora()
        anotar(db, t, u, "estado", "Cerrado: el usuario resolvió el problema con la solución rápida sugerida por la IA")
    else:
        elegido = ia.elegir_tecnico(r["tecnicos"])
        if elegido:
            t.tecnico_id = elegido["id_tecnico"]
            anotar(db, t, None, "asignado", f"Asignado automáticamente a {elegido['nombre']} ({elegido['id_tecnico']})"
                   + (f". {elegido['nota']}" if elegido["nota"] else ""))
    db.commit()
    db.refresh(t)
    return detalle(u, t)


# ------------------------------------------------------------------ listas y detalle
@router.get("", summary="Listar tickets (Usuario: los suyos; Soporte: los asignados; Administrador: todos)")
def listar(estado: str | None = None, categoria: str | None = None, prioridad: str | None = None,
           u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    q = select(Ticket)
    if u.rol == "Usuario":
        q = q.where(Ticket.solicitante_id == u.id)
    elif u.rol == "Soporte":
        tec = tecnico_de(db, u)
        q = q.where(Ticket.tecnico_id == (tec.id if tec else "-"))
    if estado:
        q = q.where(Ticket.estado == estado)
    if categoria:
        q = q.where(Ticket.categoria == categoria)
    if prioridad:
        q = q.where(Ticket.prioridad == prioridad)
    tickets = db.scalars(q.order_by(Ticket.creado_en.desc())).all()
    if u.rol == "Soporte":  # bandeja: lo abierto primero, Crítica primero y, dentro de cada prioridad, lo más antiguo
        tickets.sort(key=lambda t: (t.estado not in ESTADOS_ABIERTOS, ORDEN_PRIORIDAD[t.prioridad], t.creado_en))
    return [resumen(t) for t in tickets]


@router.get("/{ticket_id}", summary="Detalle de un ticket")
def ver(ticket_id: str, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return detalle(u, cargar(db, u, ticket_id))


# ------------------------------------------------------------------ estados y comentarios
@router.put("/{ticket_id}/estado", summary="Cambiar el estado (Abierto → En progreso → Resuelto)")
def cambiar_estado(ticket_id: str, e: EstadoEntrada, u: Usuario = Depends(staff), db: Session = Depends(get_db)):
    t = cargar(db, u, ticket_id)
    exigir_gestion(db, u, t)
    if e.estado not in TRANSICIONES.get(t.estado, []):
        raise HTTPException(422, f"No se puede pasar de «{t.estado}» a «{e.estado}». Flujo: Abierto → En progreso → Resuelto "
                                 "(el solicitante confirma o reabre).")
    if e.estado == "Resuelto":
        if not (e.solucion and e.solucion.strip()):
            raise HTTPException(422, "Para resolver el ticket debes escribir la solución aplicada.")
        t.solucion, t.resuelto_en = e.solucion.strip(), ahora()
    t.estado, t.actualizado_en = e.estado, ahora()
    anotar(db, t, u, "estado", f"{e.estado}" + (f": {t.solucion}" if e.estado == "Resuelto" else ""))
    db.commit()
    return detalle(u, t)


@router.post("/{ticket_id}/comentarios", status_code=201, summary="Agregar un comentario")
def comentar(ticket_id: str, e: ComentarioEntrada, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    t = cargar(db, u, ticket_id)
    db.add(Comentario(ticket_id=t.id, autor_id=u.id, texto=e.texto.strip()))
    t.actualizado_en = ahora()
    anotar(db, t, u, "comentario", e.texto.strip()[:120])
    db.commit()
    db.refresh(t)
    return detalle(u, t)


def _solo_solicitante(u: Usuario, t: Ticket):
    if t.solicitante_id != u.id:
        raise HTTPException(403, "Solo quien registró el ticket puede confirmarlo o reabrirlo.")
    if t.estado != "Resuelto":
        raise HTTPException(422, "El ticket debe estar en estado Resuelto.")


@router.post("/{ticket_id}/confirmar", summary="El solicitante confirma la solución (Resuelto → Cerrado)")
def confirmar(ticket_id: str, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    t = cargar(db, u, ticket_id)
    _solo_solicitante(u, t)
    t.estado, t.cerrado_en, t.actualizado_en = "Cerrado", ahora(), ahora()
    anotar(db, t, u, "estado", "Cerrado: el solicitante confirmó la solución")
    db.commit()
    return detalle(u, t)


@router.post("/{ticket_id}/reabrir", summary="El solicitante reabre el ticket (Resuelto → En progreso)")
def reabrir(ticket_id: str, u: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    t = cargar(db, u, ticket_id)
    _solo_solicitante(u, t)
    t.estado, t.resuelto_en, t.actualizado_en = "En progreso", None, ahora()
    anotar(db, t, u, "estado", "Reabierto por el solicitante: el problema persiste")
    db.commit()
    return detalle(u, t)


# ------------------------------------------------------------------ corrección y reasignación
@router.post("/{ticket_id}/corregir", summary="Corregir la categoría o la prioridad sugeridas por la IA")
def corregir(ticket_id: str, e: CorregirEntrada, u: Usuario = Depends(staff), db: Session = Depends(get_db)):
    t = cargar(db, u, ticket_id)
    exigir_gestion(db, u, t)
    if e.categoria is None and e.prioridad is None:
        raise HTTPException(422, "Indica la categoría o la prioridad correcta.")
    nueva_cat, nueva_pri = e.categoria or t.categoria, e.prioridad or t.prioridad
    if nueva_cat == t.categoria and nueva_pri == t.prioridad:
        raise HTTPException(422, "La corrección no cambia nada: el ticket ya tiene esa categoría y prioridad.")
    a = t.analisis
    db.add(Correccion(ticket_id=t.id, usuario_id=u.id, categoria_ia=a.categoria_sugerida if a else t.categoria,
                      categoria_correcta=nueva_cat, prioridad_ia=a.prioridad_sugerida if a else t.prioridad, prioridad_correcta=nueva_pri,
                      version_modelos=a.version_modelos if a else "-"))
    anotar(db, t, u, "corregido", f"Categoría {t.categoria} → {nueva_cat}; prioridad {t.prioridad} → {nueva_pri}")
    t.categoria, t.prioridad, t.actualizado_en = nueva_cat, nueva_pri, ahora()
    ia.agregar_a_correcciones_csv(t, nueva_cat, nueva_pri)
    db.commit()
    db.refresh(t)
    return detalle(u, t)


@router.post("/{ticket_id}/reasignar", summary="Reasignar el ticket (automático o manual)")
def reasignar(ticket_id: str, e: ReasignarEntrada = ReasignarEntrada(), u: Usuario = Depends(staff), db: Session = Depends(get_db)):
    t = cargar(db, u, ticket_id)
    if t.estado not in ESTADOS_ABIERTOS:
        raise HTTPException(422, "Solo se pueden reasignar tickets Abiertos o En progreso.")
    if u.rol == "Soporte":
        exigir_gestion(db, u, t)
        if e.tecnico_id:
            raise HTTPException(403, "Soporte solo puede devolver el ticket para una reasignación automática.")
    anterior = t.tecnico_id
    if e.tecnico_id:  # manual (Administrador)
        nuevo = db.get(Tecnico, e.tecnico_id)
        if nuevo is None:
            raise HTTPException(422, "El técnico indicado no existe.")
        if nuevo.id == anterior:
            raise HTTPException(422, "El ticket ya está asignado a ese técnico.")
        modo = "manual"
    else:  # automática: el siguiente técnico con capacidad, sin contar al actual
        elegido = ia.elegir_tecnico(ia.ranking(db, t.categoria, t.prioridad), excluir=anterior)
        if elegido is None:
            raise HTTPException(422, "No hay otro técnico disponible para reasignar.")
        nuevo = db.get(Tecnico, elegido["id_tecnico"])
        modo = "automática" + (f" ({elegido['nota']})" if elegido["nota"] else "")
    t.tecnico_id, t.actualizado_en = nuevo.id, ahora()
    anotar(db, t, u, "reasignado", f"{anterior or 'sin asignar'} → {nuevo.nombre} ({nuevo.id}), reasignación {modo}")
    db.commit()
    db.refresh(t)
    return detalle(u, t)
