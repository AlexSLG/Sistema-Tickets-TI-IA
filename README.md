# Sistema de tickets TI con IA

Sistema web de mesa de ayuda, instalable en un servidor local con Docker. Los usuarios registran tickets en español y la IA los analiza:

| Función | Modelo |
|---|---|
| Clasificación (Hardware, Software, Red, Accesos, Correo, Seguridad) y embedding del ticket | GRU bidireccional |
| Predicción de prioridad (Baja, Media, Alta, Crítica) | Perceptrón Multicapa (MLP) |
| Asignación de técnico según aptitudes, carga e historial | MLP + reglas de balanceo |
| Casos similares y soluciones rápidas | Embeddings de la GRU + similitud coseno con umbral |
| Aprendizaje continuo | Reentrenamiento con correcciones; la versión nueva solo se publica si no empeora |

Restricción del curso: solo MLP, CNN, RNN, LSTM, GRU y Autoencoder. **No se usan transformers ni modelos de lenguaje preentrenados como parte del sistema.** MarianMT se usó solo para traducir los datos (preprocesamiento).

Proyecto académico (Scrum + CRISP-ML(Q)). Equipo: Alex (Scrum Master), Jeferson (Product Owner), Jesús y César. Jira: proyecto «PROYECTO DE IA» (SCRUM).

## Estado

| Sprint | Contenido | Estado |
|---|---|---|
| 1 · Modelos (30/09 – 12/10) | Datos, modelos entrenados y evaluados, API de inferencia y página de prueba (`/laboratorio`) | ✅ `reports/informe_modelos.md` |
| 2 · Sistema (19/10) | Aplicación web con tres roles, base de datos, IA integrada en cada ticket, administración, panel de métricas y Docker Compose | ✅ funcional; lo pendiente está en `PENDIENTES_SPRINT3.md` |
| 3 · Pruebas, mejoras y entrega | — | pendiente |

## Ejecutar en local (Windows, sin instalar PostgreSQL)

Requisitos: Python 3.11 y Git. No hace falta GPU. Los modelos entrenados (`models/v1/`) están en el repositorio.

```bash
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn src.service.app:app --port 8000
```

Abre **http://localhost:8000**. La primera vez la aplicación crea la base de datos SQLite (`data/app.db`) y carga los datos de demostración (≈ 15–30 s: carga los modelos y registra 60 tickets con la IA). Para empezar de cero: borra `data/app.db` o ejecuta `python -m src.sistema.semilla --reiniciar`.

| Dirección | Qué es |
|---|---|
| `http://localhost:8000/` | Sistema de tickets (inicio de sesión) |
| `http://localhost:8000/laboratorio` | Página de prueba de los modelos (Sprint 1) |
| `http://localhost:8000/docs` | Documentación interactiva de la API |

> Si Windows muestra «An Application Control policy has blocked this file» al importar `torch` o `pandas`, el Control de aplicaciones inteligente (Smart App Control) bloquea los binarios sin firmar de Python. Hay que desactivarlo en *Seguridad de Windows › Control de aplicaciones y del explorador*; es una decisión del usuario.

Variables de entorno opcionales: `DATABASE_URL` (por defecto SQLite en `data/app.db`), `SECRETO_JWT` (clave de las sesiones; **cámbiala fuera de desarrollo**), `HORAS_EXPIRACION_TOKEN` (8) y `SEMILLA_AUTOMATICA` (`0` para no cargar los datos de demostración).

## Ejecutar con Docker (PostgreSQL 16 + aplicación)

```bash
docker compose up --build          # http://localhost:8000
docker compose down                # detiene; los datos se conservan
docker compose down -v             # además borra la base de datos (la próxima vez vuelve a cargar los datos de demostración)
```

El contenedor `app` espera a que PostgreSQL esté sano, crea las tablas y carga los datos de demostración si la base está vacía (el primer arranque tarda ≈ 1 minuto). `models/` y `data/` se montan como volúmenes: las versiones de modelos y `data/correcciones.csv` persisten. Probado en este proyecto: `scripts/prueba_humo.py` recorre el guion completo contra los contenedores.

## Credenciales de demostración

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@soporte.local` | `Admin123` |
| Usuario | `ana.torres@empresa.local` · `luis.paz@empresa.local` · `rosa.campos@empresa.local` | `Usuario123` |
| Soporte (8 técnicos) | `nombre.apellido@soporte.local`, p. ej. `marcela.vega@soporte.local` (T05, redes), `mateo.quispe@soporte.local` (T08, generalista), `lucia.herrera@soporte.local` (T07, accesos y correo) | `Soporte123` |

La pantalla de inicio de sesión tiene botones que rellenan estas cuentas. Lista completa: `python -m src.sistema.semilla`.

## Guion de demostración

1. **Solución rápida.** Entra como `ana.torres` → *Nuevo ticket* → título y descripción: *«No puedo entrar a mi correo, dice contraseña incorrecta»* → **Analizar**. La IA lo clasifica (Correo, prioridad Baja) y sugiere una solución rápida con pasos → **Sí, se resolvió**: el ticket queda **Cerrado** sin asignar a nadie.
2. **Incidente grave.** Registra *«El servidor de archivos no responde»* con descripción *«El servidor de archivos no responde, hay una caída de la red en todo el piso y nadie puede trabajar»*, impacto **Alto**, urgencia **Alta**, **40** usuarios → no hay solución rápida → **Registrar ticket**. Resultado: «Clasificado como **Red**, prioridad **Crítica**, asignado a **Marcela Vega**» (el técnico depende de las cargas del momento).
   > Con la redacción *«El servidor de archivos no responde y todo el piso no puede trabajar»* (sin mencionar la red) el modelo lo clasifica como Software / Alta: es una limitación conocida, ver `reports/informe_modelos.md`.
3. **Técnico.** Cierra sesión y entra como el técnico asignado (p. ej. `marcela.vega`) → el ticket aparece **primero** en la bandeja → ábrelo y revisa el panel **Análisis de la IA** (probabilidades de categoría y prioridad, ranking de técnicos con carga y adecuación, solución rápida, 5 casos similares, versión de los modelos y tiempo) → **Pasar a En progreso** → comenta → escribe la solución → **Marcar como resuelto**. (Como `ana`, *Mis tickets* → el ticket → **Confirmar y cerrar** o **Reabrir**.)
4. **Corrección.** Como técnico, abre otro ticket → *Corregir la clasificación de la IA* → cambia la categoría → *Guardar corrección*. En el análisis aparece «La IA sugirió X; corregido a Y por Z» y se añade una fila a `data/correcciones.csv`.
5. **Balanceo.** Entra como `admin` → *Técnicos* → desmarca **Disponible** (o baja el límite de carga) al técnico más apto → como `ana`, registra de nuevo el ticket del paso 2 → se asigna al **siguiente** técnico y el análisis explica por qué («Era el más adecuado por aptitud, pero no está disponible…»). Vuelve a marcar al técnico como disponible.
6. **Panel y modelos.** Como `admin`: *Panel de métricas* (tickets por estado, categoría, prioridad y área; tiempos de resolución; carga frente al límite; sugerencias de la IA aceptadas; tickets por día) y *Modelos de IA* (versión activa, métricas, versiones, correcciones guardadas, **Reentrenar** con progreso y comparación con la versión vigente, **Activar** una versión publicada).

## Roles y permisos

| Rol | Puede |
|---|---|
| **Usuario** | Registrar tickets (con análisis y solución rápida previos), ver los suyos, comentar, confirmar o reabrir. No ve el análisis de la IA |
| **Soporte** | Ver su bandeja (ordenada por prioridad), cambiar estados, resolver con solución, comentar, corregir la clasificación, devolver el ticket para una reasignación automática, ver el análisis de la IA y su resumen |
| **Administrador** | Todo lo anterior sobre cualquier ticket, reasignar manualmente, gestionar usuarios y técnicos (límite, disponibilidad, aptitudes), ver el panel y gestionar modelos y reentrenamiento |

Estados: `Abierto` → `En progreso` → `Resuelto` → `Cerrado` (el solicitante confirma, o reabre y vuelve a `En progreso`). La **carga** de un técnico son sus tickets en `Abierto` o `En progreso`.

## Pruebas

```bash
.venv\Scripts\python -m pytest tests/ -q          # 53 pruebas: datos, API de inferencia, login y roles, tickets con IA, administración, panel y semilla
.venv\Scripts\python scripts/prueba_humo.py http://localhost:8000   # guion completo contra un servidor en marcha (local o Docker)
```

Las pruebas del sistema usan una base SQLite temporal y no escriben en `data/app.db` ni en `data/correcciones.csv`.

## API

Además de los endpoints de inferencia del Sprint 1 (`docs/contrato_api.md`, siguen disponibles y sin protección para el laboratorio):

| Ruta | Rol |
|---|---|
| `POST /api/auth/login`, `GET /api/auth/yo` | público / autenticado |
| `GET/POST /api/usuarios`, `PUT /api/usuarios/{id}` | Administrador |
| `GET /api/admin/tecnicos`, `PUT /api/admin/tecnicos/{id}` | Administrador |
| `POST /api/tickets/analizar`, `POST /api/tickets`, `GET /api/tickets`, `GET /api/tickets/{id}` | autenticado (según rol) |
| `PUT /api/tickets/{id}/estado`, `POST …/comentarios`, `…/confirmar`, `…/reabrir`, `…/corregir`, `…/reasignar` | según el flujo |
| `GET /api/panel/resumen` | Administrador (Soporte: solo lo suyo) |

Detalle y esquemas en `/docs`.

## Estructura

```
src/service/          API de inferencia (Sprint 1: app, inferencia, schemas), rutas del sistema y páginas estáticas
src/service/static/   index.html y app.js (laboratorio) · sistema/ (interfaz del sistema: nucleo.js, tickets.js, admin.js)
src/sistema/          config, db, modelos (tablas), seguridad (JWT y bcrypt), esquemas, ia (puente con los modelos), semilla, rutas/
src/models/           comun, base, gru_clasificador, mlp_prioridad, mlp_asignacion, similitud
src/training/         entrenar_*, entrenar_todo, evaluar, reentrenar, registro
src/data/             pipeline de datos del Sprint 1
models/               registry.json y la versión v1 entrenada
data/processed/       tickets, train/val/test, tecnicos.csv, historial_asignaciones.csv, soluciones_rapidas.json
docs/                 modelo_datos.md y contrato_api.md
reports/              informe de modelos, métricas, auditoría de etiquetas, EDA y reglas de etiquetado
scripts/              prueba_humo.py
tests/                pruebas con pytest
Dockerfile · docker-compose.yml
```

## Datos y modelos (Sprint 1)

`data/processed/` contiene **9 379 tickets** (8 834 reales y 545 variantes aumentadas) etiquetados, divididos en `train.csv` / `val.csv` / `test.csv` (70/15/15 por `grupo`), además de `tecnicos.csv`, `historial_asignaciones.csv` y `soluciones_rapidas.json` (51 entradas). Los datos tienen su origen en fuentes públicas recopiladas, traducidas y depuradas (`reports/inventario_fuentes.md`). `Dataset/` contiene las fuentes originales: no se modifican ni se mueven.

| Modelo | Resultado (test, tickets reales) | Criterio |
|---|---|---|
| GRU de categoría | F1 macro **0,884** (modelo base TF-IDF + regresión logística: 0,884; empate estadístico) | ≥ 0,85 ✅ · mejor que el base ❌ |
| MLP de prioridad | F1 macro **0,923**, recall de Crítica **0,953** (la regla impacto × urgencia da 0,931) | ≥ 0,80 y ≥ 0,85 ✅ |
| MLP de asignación | técnico esperado en primer lugar **85,0 %**; 0 violaciones del límite de carga | ≥ 80 % ✅ |
| Casos similares | ≥ 3 de 5 de la misma categoría en el **87 %** (muestra de 30) y 89,5 % (validación) | ✅ |

**Limitaciones que conviene conocer** (detalle en `reports/informe_modelos.md`): las etiquetas de la fuente principal salen de reglas (≈ 85 % de acierto estimado en la auditoría); el MLP de prioridad depende casi por completo de impacto y urgencia; el historial de asignaciones es una simulación; las soluciones rápidas son un detector conservador (funcionan mejor con textos cortos y parecidos a los ejemplos); algunos reportes con redacción real se clasifican mal (p. ej. phishing). Al evaluar usa solo los tickets reales (`origen_etiqueta != "aumento"`).

### Reproducir los datos y entrenar de nuevo

Cada script se puede ejecutar por separado y deja su salida en `data/` o `reports/`; las semillas son fijas (42).

```bash
copy Dataset\* data\raw\                                       # solo la primera vez
.venv\Scripts\python -m src.data.inventario                    # reports/inventario_fuentes.md
.venv\Scripts\python -m src.data.filtrar                       # filtrado de colas
.venv-traduccion\Scripts\python -m src.data.traduccion         # traducción en/de/it -> es (GPU, ≈ 10 min; reanudable)
.venv\Scripts\python -m src.data.unificar                      # mapeo, depuración y unificación
.venv-traduccion\Scripts\python -m src.data.aumentar           # aumento por retrotraducción (GPU)
.venv\Scripts\python -m src.data.dividir                       # 70/15/15 por grupo
.venv\Scripts\python -m src.data.auxiliares                    # técnicos e historial de asignaciones
.venv\Scripts\python -m src.data.soluciones_rapidas            # soluciones rápidas
.venv\Scripts\python -m src.training.entrenar_todo --version v1   # base, GRU, MLP, asignación y similitud (≈ 1 h en CPU)
.venv\Scripts\python -m src.training.evaluar                   # reports/metricas.json y figuras
```

El entorno de GPU (`.venv-traduccion`, torch CUDA 12.6) solo se necesita para traducir y aumentar. Las correcciones guardadas en el sistema se usan con `python -m src.training.reentrenar` o con el botón *Reentrenar* de la pantalla *Modelos de IA*.

## Convenciones

- Todo el código, comentarios, interfaz y reportes en español.
- Python 3.11 en `.venv`; PyTorch en CPU para entrenar y servir.
- Taxonomía — categorías: Hardware, Software, Red, Accesos, Correo, Seguridad; prioridades: Baja, Media, Alta, Crítica; impacto: Bajo, Medio, Alto; urgencia: Baja, Media, Alta (la prioridad sigue la matriz impacto × urgencia); roles: Usuario, Soporte, Administrador.
