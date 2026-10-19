"""Panel de métricas (HU28, HU29, HU30): Administrador ve todo; Soporte ve solo lo suyo."""
from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sistema import ia
from src.sistema.db import get_db
from src.sistema.modelos import ESTADOS, ESTADOS_ABIERTOS, Tecnico, Ticket, Usuario, ahora
from src.sistema.seguridad import requiere_rol

router = APIRouter(prefix="/api/panel", tags=["panel"])
CATEGORIAS = ["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"]
PRIORIDADES = ["Baja", "Media", "Alta", "Crítica"]


def _promedio(valores):
    return round(sum(valores) / len(valores), 2) if valores else None


@router.get("/resumen", summary="Resumen de métricas del sistema")
def resumen(u: Usuario = Depends(requiere_rol("Administrador", "Soporte")), db: Session = Depends(get_db)):
    tecnicos = db.scalars(select(Tecnico).order_by(Tecnico.id)).all()
    q = select(Ticket)
    propio = None
    if u.rol == "Soporte":
        propio = next((t for t in tecnicos if t.usuario_id == u.id), None)
        q = q.where(Ticket.tecnico_id == (propio.id if propio else "-"))
        tecnicos = [propio] if propio else []
    tickets = db.scalars(q).all()
    area_de = {t.id: t.area for t in tecnicos}
    nombre_de = {t.id: t.nombre for t in tecnicos}

    # tiempos de resolución en horas (creado → resuelto), sin contar los resueltos con solución rápida (autoservicio)
    resueltos = [t for t in tickets if t.resuelto_en and not t.resuelto_con_solucion_rapida]
    horas = {t.id: (t.resuelto_en - t.creado_en).total_seconds() / 3600 for t in resueltos}
    por_tecnico = []
    for tec in tecnicos:
        h = [horas[t.id] for t in resueltos if t.tecnico_id == tec.id]
        por_tecnico.append({"id": tec.id, "nombre": tec.nombre, "resueltos": len(h), "promedio_horas": _promedio(h)})

    # cargas actuales frente al límite
    cargas = ia.contexto_tecnicos(db)["cargas"]
    carga_tecnicos = [{"id": t.id, "nombre": t.nombre, "area": t.area, "carga": cargas.get(t.id, 0), "limite": t.limite_carga, "disponible": t.disponible}
                      for t in tecnicos]

    # sugerencias de la IA aceptadas sin corrección (el ticket conserva lo que sugirió el modelo)
    con_analisis = [t for t in tickets if t.analisis is not None]
    acep_cat = sum(1 for t in con_analisis if t.categoria == t.analisis.categoria_sugerida)
    acep_pri = sum(1 for t in con_analisis if t.prioridad == t.analisis.prioridad_sugerida)

    # tickets por día, últimos 14 días (incluidos los días sin tickets)
    hoy = ahora().date()
    dias = [hoy - timedelta(days=i) for i in range(13, -1, -1)]
    cuenta_dias = Counter(t.creado_en.date() for t in tickets)

    return {
        "alcance": "propios" if u.rol == "Soporte" else "todos",
        "total": len(tickets),
        "por_estado": {e: sum(1 for t in tickets if t.estado == e) for e in ESTADOS},
        "por_categoria": {c: sum(1 for t in tickets if t.categoria == c) for c in CATEGORIAS},
        "por_prioridad": {p: sum(1 for t in tickets if t.prioridad == p) for p in PRIORIDADES},
        "por_area": dict(Counter(area_de.get(t.tecnico_id, "Sin técnico (solución rápida o sin asignar)") for t in tickets)),
        "abiertos": sum(1 for t in tickets if t.estado in ESTADOS_ABIERTOS),
        "tiempo_resolucion": {"promedio_horas": _promedio(list(horas.values())), "resueltos": len(horas), "por_tecnico": por_tecnico},
        "carga_tecnicos": carga_tecnicos,
        "resueltos_con_solucion_rapida": sum(1 for t in tickets if t.resuelto_con_solucion_rapida),
        "sugerencias_ia": {"analizados": len(con_analisis),
                           "categoria_aceptada": round(acep_cat / len(con_analisis), 4) if con_analisis else None,
                           "prioridad_aceptada": round(acep_pri / len(con_analisis), 4) if con_analisis else None,
                           "corregidos": len(con_analisis) - acep_cat if con_analisis else 0},
        "por_dia": [{"fecha": d.isoformat(), "tickets": cuenta_dias.get(d, 0)} for d in dias],
    }
