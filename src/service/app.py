"""API de inferencia (FastAPI) y página de prueba.

Ejecutar:  uvicorn src.service.app:app --port 8000      (documentación automática en /docs; página de prueba en /)
"""
import csv
import json
import threading
import traceback
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.models.comun import RAIZ
from src.service.inferencia import Servicio
from src.service.schemas import (ActivarEntrada, AnalisisSalida, CargasEntrada, CorreccionEntrada, ReentrenarEntrada, SimilaresEntrada,
                                 SimilaresSalida, TecnicoEstado, TicketEntrada)
from src.training import registro
from src.training.reentrenar import CORRECCIONES, COLUMNAS, leer_correcciones, reentrenar

ESTATICO = Path(__file__).parent / "static"
FIGURAS = RAIZ / "reports" / "figuras"

app = FastAPI(title="Sistema de tickets TI con IA · API de inferencia", version="1.0",
              description="Clasifica y prioriza tickets, sugiere técnico, soluciones rápidas y casos similares. "
                          "Sprint 1: modelos (GRU, MLP) y página de prueba.")
estado = {"servicio": None, "lock": threading.Lock()}
trabajo = {"estado": "inactivo", "mensajes": [], "resultado": None, "inicio": None, "fin": None}


def servicio() -> Servicio:
    if estado["servicio"] is None:
        with estado["lock"]:
            if estado["servicio"] is None:
                try:
                    estado["servicio"] = Servicio()
                except Exception as e:
                    raise HTTPException(503, f"Los modelos no están disponibles: {e}")
    return estado["servicio"]


def recargar(version=None):
    with estado["lock"]:
        previo = estado["servicio"]
        nuevo = Servicio(version)
        if previo is not None:  # conserva las cargas editadas de los técnicos
            nuevo.cargas.update(previo.cargas)
        estado["servicio"] = nuevo


@app.middleware("http")
async def sin_cache_para_la_pagina(request, call_next):
    """La página y sus recursos no se guardan en caché: así los cambios de estilo se ven al recargar."""
    respuesta = await call_next(request)
    ruta = request.url.path
    if ruta in ("/", "/laboratorio") or ruta.startswith("/estatico/"):
        respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@app.on_event("startup")
def al_iniciar():
    try:
        servicio()
    except HTTPException:
        pass  # se informará con 503 en cada petición hasta que haya modelos


# ------------------------------------------------------------------ inferencia
@app.post("/api/analizar", response_model=AnalisisSalida, tags=["inferencia"], summary="Analizar un ticket")
def analizar(t: TicketEntrada):
    return servicio().analizar(t.titulo, t.descripcion, t.impacto, t.urgencia, t.usuarios_afectados)


@app.post("/api/similares", response_model=SimilaresSalida, tags=["inferencia"], summary="Casos similares")
def similares(e: SimilaresEntrada):
    return servicio().similares(e.texto, e.k)


@app.get("/api/tecnicos", response_model=list[TecnicoEstado], tags=["técnicos"], summary="Estado de los técnicos")
def get_tecnicos():
    return servicio().estado_tecnicos()


@app.put("/api/tecnicos", response_model=list[TecnicoEstado], tags=["técnicos"], summary="Fijar las cargas de los técnicos (para probar el balanceo)")
def put_tecnicos(e: CargasEntrada):
    try:
        return servicio().fijar_cargas(e.cargas)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


# ------------------------------------------------------------------ aprendizaje continuo
@app.post("/api/correcciones", tags=["aprendizaje continuo"], summary="Guardar una corrección")
def correcciones(c: CorreccionEntrada):
    s = servicio()
    if c.tecnico_reasignado and c.tecnico_reasignado not in s.ids:
        raise HTTPException(422, f"Técnico desconocido: {c.tecnico_reasignado}")
    CORRECCIONES.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not CORRECCIONES.exists() or CORRECCIONES.stat().st_size == 0
    with open(CORRECCIONES, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(COLUMNAS)
        w.writerow([c.titulo, c.descripcion, c.categoria_corregida, c.prioridad_corregida, c.tecnico_reasignado or "",
                    c.impacto or "", c.urgencia or "", c.usuarios_afectados or "", datetime.now().strftime("%Y-%m-%d %H:%M")])
    return {"guardada": True, "total_correcciones": len(leer_correcciones())}


@app.get("/api/correcciones", tags=["aprendizaje continuo"], summary="Correcciones guardadas")
def listar_correcciones():
    return leer_correcciones().fillna("").to_dict(orient="records")


def _ejecutar_reentrenamiento(epocas):
    trabajo.update(estado="ejecutando", mensajes=[], resultado=None, inicio=datetime.now().isoformat(timespec="seconds"), fin=None)
    try:
        r = reentrenar(epocas=epocas, progreso=lambda m: trabajo["mensajes"].append(m))
        if r.get("publicada"):
            recargar()
        trabajo.update(estado="terminado", resultado=r)
    except Exception as e:
        trabajo.update(estado="error", resultado={"publicada": False, "motivo": f"Error: {e}", "detalle": traceback.format_exc()[-800:]})
    trabajo["fin"] = datetime.now().isoformat(timespec="seconds")


@app.post("/api/reentrenar", tags=["aprendizaje continuo"], summary="Reentrenar con las correcciones",
          description="Reentrena desde la versión vigente y la compara con ella en un conjunto de referencia fijo; solo se publica si su F1 macro "
                      "iguala o supera. Por defecto se ejecuta en segundo plano (consultar `GET /api/reentrenar/estado`); con `sincrono=true` espera el resultado.")
def post_reentrenar(e: ReentrenarEntrada = ReentrenarEntrada()):
    if trabajo["estado"] == "ejecutando":
        raise HTTPException(409, "Ya hay un reentrenamiento en curso.")
    if e.sincrono:
        _ejecutar_reentrenamiento(e.epocas)
        return trabajo["resultado"]
    threading.Thread(target=_ejecutar_reentrenamiento, args=(e.epocas,), daemon=True).start()
    return {"estado": "ejecutando", "mensaje": "Reentrenamiento iniciado; consulta GET /api/reentrenar/estado."}


@app.get("/api/reentrenar/estado", tags=["aprendizaje continuo"], summary="Estado del reentrenamiento")
def estado_reentrenamiento():
    return trabajo


# ------------------------------------------------------------------ modelos y métricas
@app.get("/api/modelos", tags=["modelos"], summary="Registro de versiones")
def modelos():
    return registro.cargar()


@app.post("/api/modelos/activar", tags=["modelos"], summary="Restaurar o activar una versión publicada")
def activar(e: ActivarEntrada):
    try:
        registro.restaurar(e.version)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    recargar(e.version)
    return registro.cargar()


@app.get("/api/metricas", tags=["modelos"], summary="Métricas de la versión activa y figuras")
def metricas():
    reg = registro.cargar()
    v = registro.version_activa(reg)
    if v is None:
        raise HTTPException(503, "No hay versión activa.")
    d = RAIZ / v["directorio"]
    salida = {"version": v["version"], "resumen": v["metricas"]}
    for clave, nombre in (("categoria", "metricas_categoria.json"), ("prioridad", "metricas_prioridad.json"),
                          ("asignacion", "metricas_asignacion.json"), ("similitud", "metricas_similitud.json")):
        ruta = d / nombre
        salida[clave] = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None
    salida["figuras"] = sorted(f"/figuras/{p.name}" for p in FIGURAS.glob("*.png")) if FIGURAS.exists() else []
    return salida


@app.get("/api/salud", tags=["modelos"], summary="Estado del servicio")
def salud():
    s = servicio()
    return {"estado": "ok", "version_modelos": s.version}


# ------------------------------------------------------------------ página de prueba
if FIGURAS.exists():
    app.mount("/figuras", StaticFiles(directory=str(FIGURAS)), name="figuras")
app.mount("/estatico", StaticFiles(directory=str(ESTATICO)), name="estatico")


@app.get("/", include_in_schema=False)
@app.get("/laboratorio", include_in_schema=False)
def pagina():
    return FileResponse(ESTATICO / "index.html")
