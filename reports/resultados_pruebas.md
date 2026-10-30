# Resultados de las pruebas · Sprint 3

Fecha: 2026-10-30. Plan: `docs/plan_pruebas.md`. Equipo: Windows 11, CPU de 16 hilos, sin GPU; Python 3.11; versión de modelos v1.

## 1. Resumen

| Conjunto | Pruebas | Resultado |
|---|---:|---|
| `pytest` (unitarias, integración y API, BD temporal) | 68 | **68 correctas**, 0 fallos (4 E2E omitidas por diseño: se ejecutan aparte) — ≈ 32 s |
| E2E con Playwright (`tests/e2e/`, navegador Chromium, guion por rol) | 4 | **4 correctas** contra la aplicación local (uvicorn + SQLite, base recién sembrada) |
| Prueba de humo (`scripts/prueba_humo.py`, 20 comprobaciones) | 1 | **Correcta** en local y en la instalación limpia con Docker (`reports/verificacion_instalacion.md`) |
| Rendimiento (`scripts/medir_rendimiento.py`, 100 análisis + 50 registros) | 1 | **Cumple**: análisis mediana 22 ms / p95 31 ms; registro 32 ms / 45 ms (`reports/rendimiento.md`) |

Distribución de las 68 pruebas automáticas: API de inferencia y laboratorio 21 (`test_api.py`), tickets 13, datos 8, prueba del equipo y ciclo de aprendizaje 7, sistema y roles 6, administración 6, panel 4, soluciones rápidas (HU26) 2, semilla 1.

Pruebas añadidas en el Sprint 3: endpoints del laboratorio protegidos (401/403 para cada operación y rol), mínimo de correcciones, reentrenamiento en proceso aparte, errores en español y sin 500 con 36 combinaciones de entradas inválidas o maliciosas (cuerpos nulos, listas, textos de 100 000 caracteres, inyección SQL/HTML, JSON mal formado), usuario Soporte nuevo como técnico, HU26 (guardar, sugerir de inmediato, desactivar, editar, permisos), registro < 2 s, validador del conjunto del equipo (6) y división A/B del ciclo de aprendizaje, semilla con reaperturas y solución rápida de Soporte, y las 4 E2E.

## 2. Errores encontrados y corregidos

| # | Error | Severidad | Dónde se detectó | Corrección | Estado |
|---|---|---|---|---|---|
| 1 | Los endpoints del laboratorio que cambian datos (`PUT /api/tecnicos`, `POST /api/correcciones`, `POST /api/reentrenar`, `POST /api/modelos/activar`) no pedían sesión: cualquiera en la red podía reentrenar o cambiar la versión de los modelos | **Alta** (seguridad) | Revisión de pendientes del Sprint 2 | Solo Administrador (`requiere_rol`); el laboratorio pide iniciar sesión | Corregido · prueba `test_operaciones_del_laboratorio_exigen_administrador` |
| 2 | En Windows, el reentrenamiento en proceso aparte no podía escribir su resultado: el archivo temporal quedaba abierto por la API (`PermissionError`) | **Alta** (el reentrenamiento desde la interfaz fallaba) | Prueba automática nueva | Cerrar el descriptor antes de lanzar el proceso | Corregido · `test_reentrenamiento_en_proceso_aparte` |
| 3 | Un usuario creado con rol Soporte no era técnico: nunca recibía tickets | Media | Pendientes del Sprint 2 | Ficha de técnico automática al crear o cambiar a Soporte; no disponible al quitar el rol o desactivar | Corregido · `test_usuario_soporte_nuevo_es_tecnico_y_recibe_tickets` |
| 4 | Al cambiar de pantalla rápidamente, una vista que terminaba de cargar tarde reemplazaba a la nueva (p. ej. el panel aparecía con «Todos los tickets» seleccionado) | Media | Prueba E2E del Administrador | Cada navegación pinta en su propio contenedor | Corregido · E2E `test_administrador_recorre_sus_pantallas` |
| 5 | Secretos (clave JWT y contraseña de PostgreSQL) fijos en `docker-compose.yml` | Media (seguridad) | Pendientes del Sprint 2 | Variables en `.env` con `.env.ejemplo`; `.env` fuera del repositorio | Corregido |
| 6 | Reentrenamiento posible con 1 o 2 correcciones (sin efecto medible y con riesgo de ruido) | Baja | Pendientes del Sprint 2 | Mínimo configurable (5) con mensaje explicativo en la interfaz | Corregido · `test_reentrenar_exige_un_minimo_de_correcciones` |
| 7 | Mensajes de validación de FastAPI en inglés y 404/405 en inglés | Baja | Revisión de errores | Manejadores en español | Corregido · `test_errores_en_espanol_y_sin_500` |
| 8 | Los scripts de prueba fallaban al imprimir ✔ en la consola de Windows (cp1252) | Baja | Ejecución de `capturas_manual.py` | Salida en UTF-8 | Corregido |
| 9 | Aviso de obsolescencia de `@app.on_event("startup")` | Baja | Pendientes del Sprint 2 | Migrado a `lifespan` | Corregido |

**No queda ningún error de severidad crítica ni alta abierto.**

## 3. Regresión final

Después de la última corrección (#4) se ejecutó todo de nuevo: `pytest` 68/68, E2E 4/4 y prueba de humo correcta.

## 4. Lo que no se pudo probar todavía

- **Validación con el conjunto del equipo (HU35) y ciclo de aprendizaje continuo con datos del equipo (HU37):** los scripts y sus pruebas están listos, pero falta el archivo `data/prueba_equipo/tickets_equipo.csv` (ver `reports/pendientes_finales.md`).
