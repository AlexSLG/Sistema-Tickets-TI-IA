# Sistema de tickets TI con IA

Mesa de ayuda web instalable en un servidor local con Docker. Los usuarios registran tickets en español y la IA los analiza: clasifica, prioriza, asigna el técnico adecuado sin saturar a nadie, propone soluciones rápidas para errores comunes, muestra casos similares y aprende de las correcciones de Soporte.

| Función | Modelo |
|---|---|
| Clasificación (Hardware, Software, Red, Accesos, Correo, Seguridad) y embedding del ticket | GRU bidireccional |
| Prioridad (Baja, Media, Alta, Crítica) | Perceptrón Multicapa (MLP) |
| Asignación de técnico según aptitudes, carga e historial | MLP + reglas de balanceo |
| Casos similares y soluciones rápidas | Embeddings de la GRU + similitud coseno con umbral |
| Aprendizaje continuo | Reentrenamiento con correcciones; la versión nueva solo se publica si no empeora |

Restricción del curso: solo MLP, CNN, RNN, LSTM, GRU y Autoencoder. **No se usan transformers ni modelos de lenguaje preentrenados como parte del sistema.** MarianMT se usó solo para traducir los datos (preprocesamiento).

Proyecto académico (Scrum + CRISP-ML(Q)). Equipo: Alex (Scrum Master), Jeferson (Product Owner), Jesús y César. Jira: proyecto «PROYECTO DE IA» (SCRUM).

## Documentación

| Documento | Contenido |
|---|---|
| [Manual de instalación](docs/manual_instalacion.md) | Docker y sin Docker, variables `.env`, puerto, datos de demostración, copias de seguridad, errores frecuentes |
| [Manual de usuario](docs/manual_usuario.md) | Un capítulo por rol con capturas; cómo leer el análisis de la IA |
| [Arquitectura](docs/arquitectura.md) | Componentes, flujo de un ticket, aprendizaje continuo, mapa de archivos |
| [CRISP-ML(Q)](docs/crisp_ml_q.md) | Las seis fases con evidencias y aseguramiento de calidad |
| [Informe de modelos](reports/informe_modelos.md) | Datos, arquitecturas, métricas frente a los umbrales, limitaciones |
| [Contrato de la API](docs/contrato_api.md) · [Modelo de datos](docs/modelo_datos.md) | Endpoints con roles; tablas y archivos |
| [Plan de pruebas](docs/plan_pruebas.md) · [Resultados](reports/resultados_pruebas.md) · [Aceptación](reports/aceptacion_final.md) | Casos por historia HU01–HU37, resultados y acta |
| [Rendimiento](reports/rendimiento.md) · [Instalación verificada](reports/verificacion_instalacion.md) | < 2 s en CPU; instalación limpia con Docker |
| [Pendientes](reports/pendientes_finales.md) | Lo que falta (conjunto de prueba del equipo) y trabajo futuro |

## Estado

| Sprint | Contenido | Estado |
|---|---|---|
| 1 · Modelos (30/09 – 12/10) | Datos, modelos entrenados y evaluados, API de inferencia y laboratorio | ✅ |
| 2 · Sistema (13/10 – 19/10) | Aplicación web con tres roles, IA integrada, administración, panel de métricas, Docker Compose | ✅ |
| 3 · Pruebas y entrega | Seguridad, HU26 (soluciones rápidas administrables), datos de demostración, manuales, CRISP-ML(Q), plan y resultados de pruebas, rendimiento | ✅ salvo la validación con el conjunto escrito por el equipo (HU35), lista para ejecutarse al recibir sus tickets |

## Instalación rápida (Docker)

Requisitos: Docker Desktop (o Docker Engine + Compose v2) y Git. No hace falta GPU.

```bash
git clone <url-del-repositorio> Sistema_de_tickets_TI_con_IA
cd Sistema_de_tickets_TI_con_IA
copy .env.ejemplo .env          # opcional en una demo; obligatorio en un servidor: cambiar SECRETO_JWT y POSTGRES_PASSWORD
docker compose up -d --build
```

Abrir **http://localhost:8001** (puerto configurable con `PUERTO_APP`). El primer arranque construye la imagen (≈ 3 min), crea las tablas en PostgreSQL 16 y carga los datos de demostración. Los contenedores se reinician solos con Docker Desktop. Detalles, sin Docker y solución de errores: [manual de instalación](docs/manual_instalacion.md).

Sin Docker (Python 3.11):

```bash
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn src.service.app:app --port 8001
```

| Dirección | Qué es |
|---|---|
| `http://localhost:8001/` | Sistema de tickets |
| `http://localhost:8001/laboratorio` | Laboratorio de modelos (acciones que cambian datos: solo Administrador) |
| `http://localhost:8001/docs` | Documentación interactiva de la API |

**Datos de demostración** (un comando; automático con la base vacía): `python -m src.sistema.semilla --reiniciar` (en Docker: `docker compose exec app python -m src.sistema.semilla --reiniciar`). Crea el Administrador, 3 usuarios, 8 técnicos y 60 tickets analizados por la IA en todos los estados —abiertos, en progreso, resueltos, cerrados, reabiertos y cerrados con solución rápida— con comentarios, correcciones y una solución rápida guardada por Soporte.

## Credenciales de demostración

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@soporte.local` | `Admin123` |
| Usuario | `ana.torres@empresa.local` · `luis.paz@empresa.local` · `rosa.campos@empresa.local` | `Usuario123` |
| Soporte (8 técnicos) | `nombre.apellido@soporte.local`, p. ej. `marcela.vega@soporte.local` (T05, redes), `mateo.quispe@soporte.local` (T08, generalista), `lucia.herrera@soporte.local` (T07, accesos y correo) | `Soporte123` |

La pantalla de inicio de sesión tiene botones que rellenan estas cuentas. **Cambiarlas antes de usar el sistema con datos reales.**

## Guion de demostración

1. **Solución rápida.** Como `ana.torres` → *Nuevo ticket*: *«No puedo entrar a mi correo, dice contraseña incorrecta»* → **Analizar** → la IA sugiere pasos → **Sí, se resolvió**: el ticket queda Cerrado sin ocupar a un técnico.
2. **Incidente grave.** *«El servidor de archivos no responde»*, descripción *«El servidor de archivos no responde, hay una caída de la red en todo el piso y nadie puede trabajar»*, impacto **Alto**, urgencia **Alta**, **40** usuarios → **Registrar ticket** → Red / **Crítica**, asignado automáticamente (p. ej. Marcela Vega).
3. **Técnico.** Como el técnico asignado: el ticket aparece primero en la bandeja → panel **Análisis de la IA** (probabilidades, ranking de técnicos con carga, similares) → *En progreso* → comentario → solución → *Resuelto*. Como `ana`: **Confirmar y cerrar** (o **Reabrir**).
4. **Solución rápida nueva (HU26).** En ese ticket resuelto, el técnico pulsa **Guardar como solución rápida**, ajusta frases y pasos y guarda. Como `ana`, un ticket nuevo con una de esas frases recibe la sugerencia de inmediato. El Administrador la ve en *Soluciones rápidas* (editar, desactivar).
5. **Corrección y aprendizaje.** El técnico corrige la categoría de otro ticket → queda en `data/correcciones.csv`. En *Modelos de IA*, con 5 correcciones o más, **Reentrenar**: la versión nueva solo se publica si no empeora.
6. **Balanceo.** Como `admin` → *Técnicos* → desmarcar **Disponible** al técnico más apto → registrar de nuevo el ticket del paso 2 → se asigna al siguiente y el análisis explica por qué.
7. **Panel.** *Panel de métricas*: estados, categorías, prioridades, tiempos, carga frente al límite y calidad de las sugerencias de la IA.

## Resultados

| Modelo | Resultado (test, tickets reales) | Criterio |
|---|---|---|
| GRU de categoría | F1 macro **0,884** (modelo base TF-IDF + regresión logística: 0,884; empate estadístico) | ≥ 0,85 ✅ · mejor que el base: empate |
| MLP de prioridad | F1 macro **0,923**, recall de Crítica **0,953** | ≥ 0,80 y ≥ 0,85 ✅ |
| MLP de asignación + balanceo | técnico esperado primero **85,0 %**; 0 violaciones del límite | ≥ 80 % ✅ |
| Casos similares | ≥ 3 de 5 de la misma categoría en el **89,5 %** | ✅ |
| Rendimiento (CPU) | análisis: mediana **22 ms**, p95 31 ms; registro: 32 ms / 45 ms | < 2 s ✅ |
| Pruebas | `pytest` 68/68 · E2E 4/4 · prueba de humo correcta · instalación limpia verificada | ✅ |

**Limitaciones conocidas** (detalle en el [informe de modelos](reports/informe_modelos.md)): las etiquetas de la fuente principal salen de reglas (≈ 85 % de acierto estimado); el estilo de plantilla de esa fuente hace que algunos textos reales se clasifiquen peor (p. ej. phishing); la prioridad depende casi por completo de impacto y urgencia; el historial de asignaciones se derivó con reglas documentadas; las soluciones rápidas son un detector conservador. La validación con tickets escritos por el equipo está pendiente de su entrega ([pendientes](reports/pendientes_finales.md)).

## Pruebas

```bash
.venv\Scripts\python -m pytest                                    # 68 pruebas (BD, correcciones y catálogo temporales)
.venv\Scripts\python scripts\prueba_humo.py http://localhost:8001   # guion completo contra la aplicación en marcha
$env:E2E_BASE="http://localhost:8001"; .venv\Scripts\python -m pytest tests/e2e   # navegador real (Playwright)
.venv\Scripts\python scripts\medir_rendimiento.py http://localhost:8001
```

Playwright (solo para E2E y capturas): `pip install playwright` y `python -m playwright install chromium`.

## Estructura del repositorio

```
src/service/          aplicación FastAPI (app.py), servicio de modelos (inferencia.py), interfaz (static/sistema/) y laboratorio (static/)
src/sistema/          configuración, base de datos, tablas, seguridad, puente con la IA, semilla de demostración, rutas/
src/models/           GRU, MLP de prioridad y de asignación, similitud, modelo base, catálogo de soluciones rápidas
src/training/         entrenamiento, evaluación, registro de versiones, reentrenamiento, evaluación del conjunto del equipo, ciclo de aprendizaje
src/data/             preparación de datos (inventario → división) y validación del conjunto del equipo
models/               registry.json y la versión v1 entrenada
data/processed/       train/val/test, técnicos, historial de asignaciones, soluciones_rapidas.json
data/prueba_equipo/   plantilla e instrucciones del conjunto de prueba del equipo
docs/                 manuales, arquitectura, CRISP-ML(Q), modelo de datos, contrato de API, plan de pruebas, img/
reports/              informes de datos y modelos, rendimiento, pruebas, aceptación, pendientes, figuras/
scripts/              prueba_humo.py, medir_rendimiento.py, capturas_manual.py
tests/                pytest; e2e/ con Playwright
Dockerfile · docker-compose.yml · .env.ejemplo
```

## Reproducir los datos y entrenar de nuevo

Cada script se ejecuta por separado y deja su salida en `data/` o `reports/`; semillas fijas (42). `Dataset/` contiene las fuentes originales: no se modifican ni se mueven (se trabaja sobre copias en `data/raw/`). Los datos provienen de fuentes públicas recopiladas, traducidas y depuradas (`reports/inventario_fuentes.md`); los datos auxiliares se derivan con reglas documentadas (`reports/reglas_etiquetado.md`).

```bash
copy Dataset\* data\raw\                                       # solo la primera vez
.venv\Scripts\python -m src.data.inventario
.venv\Scripts\python -m src.data.filtrar
.venv-traduccion\Scripts\python -m src.data.traduccion         # traducción a español (GPU, ≈ 10 min; reanudable)
.venv\Scripts\python -m src.data.unificar
.venv-traduccion\Scripts\python -m src.data.aumentar           # retrotraducción (GPU)
.venv\Scripts\python -m src.data.dividir
.venv\Scripts\python -m src.data.auxiliares
.venv\Scripts\python -m src.data.soluciones_rapidas
.venv\Scripts\python -m src.training.entrenar_todo --version v1   # ≈ 1 h en CPU
.venv\Scripts\python -m src.training.evaluar
```

## Convenciones

- Código, comentarios, interfaz y reportes en español. Python 3.11; PyTorch en CPU.
- Taxonomía — categorías: Hardware, Software, Red, Accesos, Correo, Seguridad; prioridades: Baja, Media, Alta, Crítica; impacto: Bajo, Medio, Alto; urgencia: Baja, Media, Alta (la prioridad sigue la matriz impacto × urgencia: Alto + Alta = Crítica); roles: Usuario, Soporte, Administrador.
