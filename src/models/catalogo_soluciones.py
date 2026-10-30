"""Catálogo de soluciones rápidas (HU22 y HU26).

Fuente única: data/processed/soluciones_rapidas.json. Cada entrada tiene id (SR-01…), categoria, problema, frases_ejemplo, pasos y,
desde el Sprint 3, `activa` (por defecto verdadero) y, si la agregó Soporte o un Administrador desde un ticket, `origen`,
`ticket_origen`, `creada_por` y `fecha`. Solo las activas se indexan y se sugieren. Se eligió el archivo JSON (y no una tabla) porque
lo leen igual el servicio de inferencia, el laboratorio y el reentrenamiento, y en Docker persiste en el volumen ./data.
"""
import json
import os
import tempfile
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RUTA = Path(os.getenv("CATALOGO_SOLUCIONES") or RAIZ / "data" / "processed" / "soluciones_rapidas.json")  # la variable permite usar otra copia
_lock = threading.Lock()


def leer(ruta=None):
    return json.loads(Path(ruta or RUTA).read_text(encoding="utf-8"))


def activas(soluciones):
    return [s for s in soluciones if s.get("activa", True)]


def guardar(soluciones, ruta=None):
    """Escritura atómica (archivo temporal + reemplazo) para no dejar el catálogo a medias."""
    ruta = Path(ruta or RUTA)
    with _lock:
        fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".soluciones_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(soluciones, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ruta)


def siguiente_id(soluciones):
    numeros = [int(s["id"].split("-")[1]) for s in soluciones if s["id"].split("-")[-1].isdigit()]
    return f"SR-{max(numeros, default=0) + 1:02d}"
