"""Aplicación FastAPI: API de inferencia (Sprint 1), sistema de tickets (Sprint 2) y páginas web.

Ejecutar:  uvicorn src.service.app:app --port 8001      (sistema en /, laboratorio en /laboratorio, documentación en /docs)
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
import threading
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.models.comun import RAIZ
from src.service.inferencia import Servicio
from src.service.schemas import (ActivarEntrada, AnalisisSalida, CargasEntrada, CorreccionEntrada, ReentrenarEntrada, SimilaresEntrada,
                                 SimilaresSalida, TecnicoEstado, TicketEntrada)
from src.sistema import config
from src.sistema.seguridad import requiere_rol
from src.training import registro
from src.training import reentrenar as _reentrenar
from src.training.reentrenar import CORRECCIONES, COLUMNAS, leer_correcciones

ESTATICO = Path(__file__).parent / "static"
FIGURAS = RAIZ / "reports" / "figuras"
solo_admin = requiere_rol("Administrador")
MODULO_REENTRENAR = "src.training.reentrenar"  # proceso que se lanza al reentrenar (las pruebas lo sustituyen)

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
        if previo is not None:  # conserva las cargas editadas de los técnicos (página de prueba)
            nuevo.cargas.update(previo.cargas)
        estado["servicio"] = nuevo


def al_iniciar():
    try:
        servicio()
    except HTTPException:
        pass  # se informará con 503 en cada petición hasta que haya modelos
    # Sistema de tickets: crea las tablas y, si la BD está vacía, carga los datos de demostración
    from src.sistema import db as bd, semilla
    bd.iniciar()
    if config.semilla_automatica():
        with bd.SessionLocal() as sesion:
            if semilla.bd_vacia(sesion):
                semilla.sembrar(sesion)


@asynccontextmanager
async def ciclo_de_vida(_app):
    al_iniciar()
    yield


app = FastAPI(title="Sistema de tickets TI con IA", version="1.0", lifespan=ciclo_de_vida,
              description="Mesa de ayuda con IA: clasifica y prioriza tickets, sugiere técnico, soluciones rápidas y casos similares. "
                          "Incluye la API de inferencia (Sprint 1) y el sistema de tickets con roles (Sprints 2 y 3).")


# ------------------------------------------------------------------ errores en español
MENSAJES = {
    "missing": "Campo obligatorio.", "string_too_short": "Debe tener al menos {min_length} caracteres.",
    "string_too_long": "Debe tener como máximo {max_length} caracteres.", "literal_error": "Valor no válido. Opciones: {expected}.",
    "greater_than_equal": "Debe ser mayor o igual que {ge}.", "less_than_equal": "Debe ser menor o igual que {le}.",
    "int_parsing": "Debe ser un número entero.", "int_from_float": "Debe ser un número entero.", "bool_parsing": "Debe ser verdadero o falso.",
    "string_type": "Debe ser un texto.", "dict_type": "Debe ser un objeto JSON.", "json_invalid": "El cuerpo de la petición no es un JSON válido.",
    "model_attributes_type": "El cuerpo de la petición debe ser un objeto JSON.", "string_pattern_mismatch": "El formato no es válido.",
    "extra_forbidden": "Campo no permitido.", "float_parsing": "Debe ser un número.",
}


@app.exception_handler(RequestValidationError)
async def error_de_validacion(_request: Request, exc: RequestValidationError):
    detalle = []
    for e in exc.errors():
        plantilla = MENSAJES.get(e.get("type"))
        try:
            msg = plantilla.format(**(e.get("ctx") or {})) if plantilla else e.get("msg", "Valor no válido.")
        except (KeyError, IndexError):
            msg = plantilla or e.get("msg", "Valor no válido.")
        campo = ".".join(str(x) for x in e.get("loc", []) if x not in ("body", "query", "path"))
        detalle.append({"loc": e.get("loc", []), "msg": f"{campo}: {msg}" if campo else msg, "type": e.get("type")})
    return JSONResponse(status_code=422, content={"detail": detalle})


@app.exception_handler(StarletteHTTPException)
async def error_http(_request: Request, exc: StarletteHTTPException):
    textos = {404: "Recurso no encontrado.", 405: "Método no permitido para esta ruta."}
    detalle = textos.get(exc.status_code, exc.detail) if exc.detail in ("Not Found", "Method Not Allowed") else exc.detail
    return JSONResponse(status_code=exc.status_code, content={"detail": detalle}, headers=getattr(exc, "headers", None))


@app.exception_handler(Exception)
async def error_interno(_request: Request, exc: Exception):
    traceback.print_exception(exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor. Revisa los registros de la aplicación."})


@app.middleware("http")
async def sin_cache_para_la_pagina(request, call_next):
    """Las páginas y sus recursos no se guardan en caché: así los cambios se ven al recargar."""
    respuesta = await call_next(request)
    ruta = request.url.path
    if ruta in ("/", "/laboratorio") or ruta.startswith("/estatico/"):
        respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


# ------------------------------------------------------------------ sistema de tickets (Sprints 2 y 3)
from src.sistema.rutas import auth as _auth, panel as _panel, tecnicos as _tecnicos, tickets as _tickets, usuarios as _usuarios  # noqa: E402

for _r in (_auth, _usuarios, _tickets, _tecnicos, _panel):
    app.include_router(_r.router)


# ------------------------------------------------------------------ inferencia (lectura, sin sesión)
@app.post("/api/analizar", response_model=AnalisisSalida, tags=["inferencia"], summary="Analizar un ticket")
def analizar(t: TicketEntrada):
    return servicio().analizar(t.titulo, t.descripcion, t.impacto, t.urgencia, t.usuarios_afectados)


@app.post("/api/similares", response_model=SimilaresSalida, tags=["inferencia"], summary="Casos similares")
def similares(e: SimilaresEntrada):
    return servicio().similares(e.texto, e.k)


@app.get("/api/tecnicos", response_model=list[TecnicoEstado], tags=["laboratorio"], summary="Estado de los técnicos del laboratorio")
def get_tecnicos():
    return servicio().estado_tecnicos()


@app.put("/api/tecnicos", response_model=list[TecnicoEstado], tags=["laboratorio"], summary="Fijar las cargas del laboratorio (Administrador)")
def put_tecnicos(e: CargasEntrada, _=Depends(solo_admin)):
    try:
        return servicio().fijar_cargas(e.cargas)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


# ------------------------------------------------------------------ aprendizaje continuo
@app.post("/api/correcciones", tags=["aprendizaje continuo"], summary="Guardar una corrección (Administrador)")
def correcciones(c: CorreccionEntrada, _=Depends(solo_admin)):
    s = servicio()
    if c.tecnico_reasignado and c.tecnico_reasignado not in s.ids:
        raise HTTPException(422, f"Técnico desconocido: {c.tecnico_reasignado}")
    ruta = CORRECCIONES
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists() or ruta.stat().st_size == 0
    with open(ruta, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(COLUMNAS)
        w.writerow([c.titulo, c.descripcion, c.categoria_corregida, c.prioridad_corregida, c.tecnico_reasignado or "",
                    c.impacto or "", c.urgencia or "", c.usuarios_afectados or "", datetime.now().strftime("%Y-%m-%d %H:%M")])
    return {"guardada": True, "total_correcciones": len(leer_correcciones(ruta))}


@app.get("/api/correcciones", tags=["aprendizaje continuo"], summary="Correcciones guardadas")
def listar_correcciones():
    return leer_correcciones(CORRECCIONES).fillna("").to_dict(orient="records")


def _ruta_correcciones():
    return CORRECCIONES  # se lee en cada llamada: las pruebas la sustituyen por un archivo temporal


def _ejecutar_reentrenamiento(epocas):
    """Reentrena en un PROCESO aparte (python -m src.training.reentrenar): el entrenamiento no compite por el intérprete
    con las peticiones de la API. Los mensajes de progreso se leen de su salida."""
    trabajo.update(estado="ejecutando", mensajes=[], resultado=None, inicio=datetime.now().isoformat(timespec="seconds"), fin=None)
    descriptor, nombre = tempfile.mkstemp(prefix="reentrenamiento_", suffix=".json")
    os.close(descriptor)  # en Windows el archivo abierto no lo podría escribir el otro proceso
    salida = Path(nombre)
    try:
        cmd = [sys.executable, "-u", "-m", MODULO_REENTRENAR, "--epocas", str(epocas),
               "--correcciones", str(_ruta_correcciones()), "--salida-json", str(salida)]
        entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        with subprocess.Popen(cmd, cwd=str(RAIZ), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                              errors="replace", env=entorno) as proc:
            for linea in proc.stdout:
                linea = linea.strip()
                if linea and not linea.startswith(("{", "}", '"')) and "Warning" not in linea:
                    trabajo["mensajes"] = (trabajo["mensajes"] + [linea])[-30:]
            proc.wait()
        if proc.returncode != 0 or not salida.exists() or salida.stat().st_size == 0:
            raise RuntimeError("el proceso de reentrenamiento terminó con error: " + " | ".join(trabajo["mensajes"][-3:]))
        r = json.loads(salida.read_text(encoding="utf-8"))
        if r.get("publicada"):
            recargar()
        trabajo.update(estado="terminado", resultado=r)
    except Exception as e:
        trabajo.update(estado="error", resultado={"publicada": False, "motivo": f"Error: {e}", "detalle": traceback.format_exc()[-800:]})
    finally:
        salida.unlink(missing_ok=True)
        trabajo["fin"] = datetime.now().isoformat(timespec="seconds")


@app.post("/api/reentrenar", tags=["aprendizaje continuo"], summary="Reentrenar con las correcciones (Administrador)",
          description="Reentrena desde la versión vigente, en un proceso aparte, y la compara con ella en un conjunto de referencia fijo; solo se "
                      "publica si su F1 macro iguala o supera. Exige un mínimo de correcciones válidas (variable MIN_CORRECCIONES_REENTRENAR, 5 por "
                      "defecto). En segundo plano por defecto (consultar `GET /api/reentrenar/estado`); con `sincrono=true` espera el resultado.")
def post_reentrenar(e: ReentrenarEntrada = ReentrenarEntrada(), _=Depends(solo_admin)):
    if trabajo["estado"] == "ejecutando":
        raise HTTPException(409, "Ya hay un reentrenamiento en curso.")
    validas, minimo = _reentrenar.contar_correcciones_validas(_ruta_correcciones()), config.minimo_correcciones()
    if validas < minimo:
        raise HTTPException(422, f"Se necesitan al menos {minimo} correcciones válidas para reentrenar (hay {validas}). "
                                 "Corrige la categoría o prioridad de más tickets y vuelve a intentarlo.")
    if e.sincrono:
        _ejecutar_reentrenamiento(e.epocas)
        return trabajo["resultado"]
    threading.Thread(target=_ejecutar_reentrenamiento, args=(e.epocas,), daemon=True).start()
    return {"estado": "ejecutando", "mensaje": "Reentrenamiento iniciado; consulta GET /api/reentrenar/estado."}


@app.get("/api/reentrenar/estado", tags=["aprendizaje continuo"], summary="Estado del reentrenamiento")
def estado_reentrenamiento():
    return {**trabajo, "minimo_correcciones": config.minimo_correcciones(),
            "correcciones_validas": _reentrenar.contar_correcciones_validas(_ruta_correcciones())}


# ------------------------------------------------------------------ modelos y métricas
@app.get("/api/modelos", tags=["modelos"], summary="Registro de versiones")
def modelos():
    return registro.cargar()


@app.post("/api/modelos/activar", tags=["modelos"], summary="Restaurar o activar una versión publicada (Administrador)")
def activar(e: ActivarEntrada, _=Depends(solo_admin)):
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


# ------------------------------------------------------------------ páginas
if FIGURAS.exists():
    app.mount("/figuras", StaticFiles(directory=str(FIGURAS)), name="figuras")
app.mount("/estatico", StaticFiles(directory=str(ESTATICO)), name="estatico")


@app.get("/", include_in_schema=False)
def pagina_sistema():
    """Sistema de tickets."""
    return FileResponse(ESTATICO / "sistema" / "index.html")


@app.get("/laboratorio", include_in_schema=False)
def laboratorio():
    """Página de prueba de los modelos (Sprint 1)."""
    return FileResponse(ESTATICO / "index.html")
