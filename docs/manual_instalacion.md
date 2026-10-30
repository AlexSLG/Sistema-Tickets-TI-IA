# Manual de instalación

Sistema de tickets TI con IA. Se puede instalar de dos formas: **con Docker** (recomendada para un servidor: PostgreSQL 16 + aplicación) o **sin Docker** (Python 3.11 y SQLite, útil para desarrollo o para equipos sin Docker). No hace falta GPU: los modelos se ejecutan en CPU.

## 1. Requisitos

| | Con Docker | Sin Docker |
|---|---|---|
| Sistema operativo | Windows 10/11, Linux o macOS | Windows 10/11 o Linux |
| Software | Docker Desktop (Windows/macOS) o Docker Engine + Compose v2 (Linux), Git | Python 3.11, Git |
| Memoria | 4 GB libres (la aplicación usa ≈ 1 GB) | 3 GB libres |
| Disco | ≈ 3 GB (imagen de 2 GB + base de datos) | ≈ 2 GB (entorno virtual con PyTorch CPU) |
| Red | Internet solo la primera vez (descarga de dependencias) | Igual |

## 2. Instalación con Docker

```bash
git clone <url-del-repositorio> Sistema_de_tickets_TI_con_IA
cd Sistema_de_tickets_TI_con_IA
copy .env.ejemplo .env            # Linux/macOS: cp .env.ejemplo .env
# editar .env: cambiar SECRETO_JWT y POSTGRES_PASSWORD (ver sección 4)
docker compose up -d --build
```

La primera construcción tarda ≈ 3 minutos (descarga ≈ 1 GB). Después, la aplicación espera a que PostgreSQL esté sano, crea las tablas y, si la base está vacía, carga los datos de demostración (≈ 15 s). Abrir **http://localhost:8001** (o el puerto definido en `PUERTO_APP`).

| Comando | Para qué |
|---|---|
| `docker compose ps` | Ver si los contenedores `db` y `app` están en marcha (`healthy`/`running`) |
| `docker compose logs -f app` | Ver los registros de la aplicación |
| `docker compose restart app` | Reiniciar solo la aplicación |
| `docker compose down` | Detener (los datos se conservan) |
| `docker compose down -v` | Detener **y borrar la base de datos** (al volver a levantar se cargan los datos de demostración) |
| `docker compose up -d --build` | Actualizar tras un `git pull` |

**Arranque automático:** los contenedores tienen `restart: unless-stopped`. Si Docker Desktop está configurado para iniciar con la sesión (*Settings › General › Start Docker Desktop when you sign in*), el sistema vuelve a estar disponible al encender el equipo. No usar `docker compose down` si se quiere ese comportamiento.

**Persistencia:** la base de datos está en el volumen `pgdata`; `models/` (versiones de los modelos y `registry.json`) y `data/` (correcciones y catálogo de soluciones rápidas) se montan desde la carpeta del proyecto, así que el reentrenamiento y las soluciones guardadas sobreviven a reinicios y actualizaciones.

## 3. Instalación sin Docker (Python + SQLite)

```bash
git clone <url-del-repositorio> Sistema_de_tickets_TI_con_IA
cd Sistema_de_tickets_TI_con_IA
py -3.11 -m venv .venv                                   # Linux: python3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt  # Linux: .venv/bin/python -m pip ...
.venv\Scripts\python -m uvicorn src.service.app:app --host 0.0.0.0 --port 8001
```

La primera vez se crea `data/app.db` (SQLite) y se cargan los datos de demostración. Para usar PostgreSQL sin Docker, definir `DATABASE_URL=postgresql+psycopg://usuario:clave@servidor:5432/tickets` antes de arrancar.

## 4. Variables de configuración (`.env`)

| Variable | Por defecto | Descripción |
|---|---|---|
| `SECRETO_JWT` | clave de demostración | Firma de las sesiones. **Cambiar** por una cadena larga: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `tickets` / `tickets` / `tickets` | Credenciales de la base PostgreSQL del contenedor. Cambiar la contraseña **antes** del primer arranque (si se cambia después hay que hacer `down -v`) |
| `PUERTO_APP` | `8001` | Puerto del servidor en el que se publica la aplicación |
| `MIN_CORRECCIONES_REENTRENAR` | `5` | Correcciones válidas necesarias para permitir el reentrenamiento |
| `HORAS_EXPIRACION_TOKEN` | `8` | Horas de validez de una sesión |
| `DATABASE_URL` | SQLite en `data/app.db` (sin Docker) | Solo para la instalación sin Docker |
| `SEMILLA_AUTOMATICA` | `1` | `0` para no cargar los datos de demostración en una base vacía |

`.env` no se sube al repositorio (está en `.gitignore`).

## 5. Cambiar el puerto

- Docker: `PUERTO_APP=8010` en `.env` y `docker compose up -d`. En una sola orden: PowerShell `$env:PUERTO_APP=8010; docker compose up -d`, Linux `PUERTO_APP=8010 docker compose up -d`.
- Sin Docker: `--port 8010` en la orden de `uvicorn`.

## 6. Reiniciar los datos de demostración

- Docker: `docker compose down -v` y `docker compose up -d` (o, con los contenedores en marcha, `docker compose exec app python -m src.sistema.semilla --reiniciar`).
- Sin Docker: `.venv\Scripts\python -m src.sistema.semilla --reiniciar`.

La semilla crea el Administrador, 3 usuarios, 8 técnicos (usuarios Soporte) y 60 tickets analizados por la IA en todos los estados (abiertos, en progreso, resueltos, cerrados, reabiertos y cerrados con solución rápida), con comentarios, correcciones y una solución rápida guardada por Soporte. Las credenciales están en el `README.md`.

## 7. Verificar que funciona

1. `http://localhost:8001/api/salud` debe responder `{"estado":"ok","version_modelos":"v1"}`.
2. Iniciar sesión con `admin@soporte.local` / `Admin123` y abrir el **Panel de métricas**.
3. Prueba de humo completa (requiere Python con `httpx`): `python scripts/prueba_humo.py http://localhost:8001` → «Prueba de humo correcta.»
4. Rendimiento (opcional): `python scripts/medir_rendimiento.py http://localhost:8001`.

## 8. Solución de errores frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Bind for 0.0.0.0:8001 failed: port is already allocated` o «el puerto ya está en uso» | Otro programa usa ese puerto. Elegir otro con `PUERTO_APP` (sección 5). En Windows, ver quién lo usa: `netstat -ano \| findstr :8001` |
| `error during connect ... docker_engine` / `Cannot connect to the Docker daemon` | Docker Desktop no está iniciado. Abrirlo y esperar a que diga *Engine running* |
| La página no carga justo después de `up` | Primer arranque: la aplicación carga los modelos y siembra la base (≈ 15–60 s). Ver `docker compose logs -f app` hasta «Application startup complete» |
| `An Application Control policy has blocked this file` al importar `torch` o `pandas` (sin Docker, Windows 11) | El Control de aplicaciones inteligente (Smart App Control) bloquea binarios de Python sin firmar. Desactivarlo en *Seguridad de Windows › Control de aplicaciones y del explorador* (decisión del usuario) o usar la instalación con Docker |
| El contenedor `app` se reinicia una y otra vez; `Killed` en los registros | Memoria insuficiente. Asignar al menos 4 GB a Docker Desktop (*Settings › Resources*) |
| `password authentication failed for user "tickets"` | Se cambió `POSTGRES_PASSWORD` después de crear la base. Volver a la contraseña original o `docker compose down -v` (borra los datos) |
| «Sesión expirada» o 401 en la interfaz | El token caducó (8 h) o cambió `SECRETO_JWT`. Volver a iniciar sesión |
| El laboratorio (`/laboratorio`) dice «requiere iniciar sesión como Administrador» | Las acciones que cambian cargas, correcciones o modelos están protegidas. Pulsar «Entrar como Administrador» |
| «Se necesitan al menos 5 correcciones válidas para reentrenar» | Comportamiento esperado: corregir más tickets o ajustar `MIN_CORRECCIONES_REENTRENAR` |
| `pip install` muy lento o falla con PyTorch | Instalar la versión CPU: `pip install torch --index-url https://download.pytorch.org/whl/cpu` y luego `pip install -r requirements.txt` |

La verificación de esta instalación en un entorno limpio está documentada en `reports/verificacion_instalacion.md`.
