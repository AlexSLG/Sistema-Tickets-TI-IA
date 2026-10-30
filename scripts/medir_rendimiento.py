"""Medición de rendimiento contra la aplicación en marcha (local o Docker) · HU37.

    python scripts/medir_rendimiento.py [http://localhost:8001] [--analisis 100] [--registros 50] [--entorno "Docker"]

Hace N análisis (`POST /api/tickets/analizar`) y M registros (`POST /api/tickets`) con textos del conjunto de prueba
(data/processed/test.csv, muestra fija con semilla 42) y mide el tiempo de respuesta visto por el cliente (incluye red,
autenticación, base de datos e IA). Criterio de aceptación: < 2 s en mediana y p95. Los modelos se ejecutan solo en CPU.
Los tickets registrados quedan en la base de datos (usar una base de pruebas o la de demostración).

Salida: reports/rendimiento.md y reports/rendimiento.json
"""
import argparse
import json
import os
import platform
import statistics
import time
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
INFORME, JSON = RAIZ / "reports" / "rendimiento.md", RAIZ / "reports" / "rendimiento.json"
LIMITE_S = 2.0
PERFILES = [("Bajo", "Baja", 1), ("Medio", "Media", 5), ("Alto", "Alta", 40), ("Bajo", "Media", 1), ("Medio", "Alta", 10)]


def resumen(tiempos):
    t = np.array(tiempos)
    return {"n": int(len(t)), "mediana_s": float(np.median(t)), "p95_s": float(np.percentile(t, 95)), "max_s": float(t.max()),
            "media_s": float(t.mean()), "cumple": bool(np.median(t) < LIMITE_S and np.percentile(t, 95) < LIMITE_S)}


def cuerpos(n, semilla=42):
    df = pd.read_csv(RAIZ / "data" / "processed" / "test.csv", keep_default_na=False).sample(n, random_state=semilla, replace=n > 0)
    for i, (_, r) in enumerate(df.iterrows()):
        imp, urg, afect = PERFILES[i % len(PERFILES)]
        yield {"titulo": str(r["titulo"])[:200] or "Incidencia", "descripcion": str(r["descripcion"])[:4000] or str(r["titulo"]),
               "impacto": imp, "urgencia": urg, "usuarios_afectados": afect}


def medir(base, n_analisis, n_registros):
    c = httpx.Client(base_url=base, timeout=60)
    r = c.post("/api/auth/login", json={"correo": "ana.torres@empresa.local", "contrasena": "Usuario123"})
    r.raise_for_status()
    h = {"Authorization": "Bearer " + r.json()["token"]}
    version = c.get("/api/salud").json()["version_modelos"]
    c.post("/api/tickets/analizar", headers=h, json=next(cuerpos(1)))  # calentamiento
    analisis, ia_ms, registros = [], [], []
    for cuerpo in cuerpos(n_analisis):
        t0 = time.perf_counter()
        r = c.post("/api/tickets/analizar", headers=h, json=cuerpo)
        analisis.append(time.perf_counter() - t0)
        r.raise_for_status()
        ia_ms.append(r.json().get("tiempo_ms", 0))
    for cuerpo in cuerpos(n_registros, semilla=7):
        t0 = time.perf_counter()
        r = c.post("/api/tickets", headers=h, json=cuerpo)
        registros.append(time.perf_counter() - t0)
        assert r.status_code == 201, r.text
    return {"version_modelos": version, "analizar": resumen(analisis), "registrar": resumen(registros),
            "ia_interna_ms": {"mediana": float(statistics.median(ia_ms)), "p95": float(np.percentile(ia_ms, 95))}}


def informe(res):
    fila = lambda nombre, s: (f"| {nombre} | {s['n']} | {s['mediana_s'] * 1000:.0f} ms | {s['p95_s'] * 1000:.0f} ms | {s['max_s'] * 1000:.0f} ms | "
                              f"{'cumple' if s['cumple'] else 'NO cumple'} |")
    return "\n".join([
        "# Rendimiento del sistema", "",
        f"Fecha: {res['fecha']}. Servidor: `{res['base']}` ({res['entorno']}). Versión de modelos: {res['version_modelos']}.",
        f"Equipo de medición: {res['equipo']}. Los modelos se ejecutan **solo en CPU** (PyTorch sin GPU).", "",
        "Tiempo de respuesta medido desde el cliente (incluye autenticación, base de datos, IA y red local). Criterio: **< 2 s** en mediana y p95.", "",
        "| Operación | Peticiones | Mediana | p95 | Máximo | Criterio |", "|---|---:|---:|---:|---:|---|",
        fila("Analizar ticket (`POST /api/tickets/analizar`)", res["analizar"]),
        fila("Registrar ticket (`POST /api/tickets`: análisis + asignación + guardado)", res["registrar"]), "",
        f"Tiempo interno de la IA por análisis (campo `tiempo_ms`): mediana {res['ia_interna_ms']['mediana']:.0f} ms, p95 {res['ia_interna_ms']['p95']:.0f} ms.", "",
        "Textos: muestra fija (semilla 42) del conjunto de prueba `data/processed/test.csv`, con combinaciones variadas de impacto y urgencia.",
        "Reproducir: `python scripts/medir_rendimiento.py http://localhost:8001`. La prueba automática `tests/test_api.py::test_tiempo_de_respuesta_menor_a_2_segundos` "
        "y `tests/test_tickets.py::test_registro_de_ticket_menor_a_2_segundos` lo verifican en cada ejecución de pytest.", ""])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="http://localhost:8001")
    ap.add_argument("--analisis", type=int, default=100)
    ap.add_argument("--registros", type=int, default=50)
    ap.add_argument("--entorno", default="local")
    a = ap.parse_args()
    res = medir(a.base, a.analisis, a.registros)
    res.update(base=a.base, entorno=a.entorno, fecha=datetime.now().strftime("%Y-%m-%d %H:%M"),
               equipo=f"{platform.system()} {platform.release()}, {platform.processor() or platform.machine()}, {os.cpu_count()} hilos")
    JSON.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    INFORME.write_text(informe(res), encoding="utf-8")
    for k in ("analizar", "registrar"):
        s = res[k]
        print(f"{k}: mediana {s['mediana_s'] * 1000:.0f} ms · p95 {s['p95_s'] * 1000:.0f} ms · máx {s['max_s'] * 1000:.0f} ms · {'cumple' if s['cumple'] else 'NO cumple'}")
    print(f"Informe: {INFORME.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
