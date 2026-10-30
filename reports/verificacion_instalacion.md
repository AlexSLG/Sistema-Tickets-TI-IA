# Verificación de la instalación en un entorno limpio

Fecha: 2026-10-30. Equipo: Windows 11, Docker Desktop, CPU AMD de 16 hilos, sin GPU.

## Procedimiento

1. Clonar el repositorio local en una carpeta temporal vacía: `git clone . <carpeta temporal>` (solo lo versionado: código, `models/v1/`, `data/processed/`; sin `.venv`, sin `data/app.db`, sin `.env`).
2. Levantar con un nombre de proyecto y un puerto distintos para no interferir con la instalación del equipo:
   `PUERTO_APP=8010 docker compose -p tickets_limpio up --build -d`
3. Esperar a `GET /api/salud` y ejecutar la prueba de humo: `python scripts/prueba_humo.py http://localhost:8010`.
4. Comprobaciones adicionales: endpoints del laboratorio sin sesión, mensaje de error en español, PyTorch en CPU dentro del contenedor.
5. Bajar y limpiar: `docker compose -p tickets_limpio down -v`, borrar la imagen y la carpeta temporal.

## Resultado

| Paso | Resultado | Tiempo |
|---|---|---:|
| Construcción de la imagen (descarga de dependencias, PyTorch CPU) y arranque de PostgreSQL 16 | Correcto (`exit 0`) | 159 s |
| Aplicación lista (`/api/salud` → `{"estado":"ok","version_modelos":"v1"}`), incluida la carga de modelos y la siembra de 60 tickets de demostración | Correcto | 12 s después de arrancar |
| Prueba de humo (guion completo de los tres roles: solución rápida, incidente crítico, bandeja, resolución, corrección, balanceo, panel y modelos) | **Correcta**, 20 comprobaciones | 3 s |
| `PUT /api/tecnicos` y `POST /api/reentrenar` sin sesión | 401 (protegidos) | — |
| Ruta inexistente | `{"detail":"Recurso no encontrado."}` | — |
| PyTorch dentro del contenedor | `cuda False` (solo CPU) | — |
| `down -v` y limpieza | Correcto | — |

Tamaño de la imagen de la aplicación: 2,07 GB (PyTorch CPU y dependencias científicas).

## Observaciones

- Sin `.env` se usan los valores por defecto de `docker-compose.yml`; para un servidor real se copia `.env.ejemplo` como `.env` y se cambian `SECRETO_JWT` y `POSTGRES_PASSWORD` (ver `docs/manual_instalacion.md`).
- La primera construcción depende de la velocidad de Internet (descarga ≈ 1 GB). Las siguientes reutilizan la caché de Docker.
- El rendimiento con la instalación local está en `reports/rendimiento.md` (mediana de análisis 22 ms).
