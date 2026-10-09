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

## Estado del Sprint 1 (modelos, 30/09 – 12/10)

| Paso | Estado |
|---|---|
| 1 · Repositorio y entorno | ✅ |
| 2 · Inventario de fuentes | ✅ `reports/inventario_fuentes.md` |
| 3 · Filtrado y traducción | ✅ `reports/calidad_traduccion.md` |
| 4 · Mapeo, depuración y unificación (+ auditoría de etiquetas) | ✅ `reports/reglas_etiquetado.md`, `reports/auditoria_etiquetas.md` |
| 5 · EDA y división 70/15/15 por grupo | ✅ `reports/eda.md`, `reports/division_resumen.md`, `notebooks/01_eda.ipynb` |
| 6 · Técnicos, historial de asignaciones y soluciones rápidas | ✅ `reports/datos_auxiliares.md` |
| 7 · Modelos (base, GRU, MLP de prioridad, asignación, similitud) | ⏳ pendiente |
| 8–12 · Reentrenamiento, API de inferencia, página de prueba, diseño del Sprint 2, evaluación final | ⏳ pendiente |

El plan detallado está en `PLAN_SPRINT1.md`.

## Datos

`data/processed/` contiene **9 379 tickets** (8 834 reales y 545 variantes aumentadas) ya etiquetados, divididos en `train.csv` / `val.csv` / `test.csv` (70/15/15 por `grupo`, para que una variante nunca quede en un conjunto distinto al de su ticket original), además de `tecnicos.csv`, `historial_asignaciones.csv` y `soluciones_rapidas.json`.

| Categoría | Tickets | Reales |
|---|---:|---:|
| Software | 4 274 | 4 274 |
| Seguridad | 1 481 | 1 481 |
| Red | 1 437 | 1 437 |
| Hardware | 1 148 | 1 148 |
| Accesos | 600 | 354 |
| Correo | 439 | 140 |

Prioridad: Baja 33 %, Media 33 %, Alta 27 %, Crítica 8 %.

**Limitaciones que conviene conocer** (detalle en los informes):

- Las etiquetas de la fuente principal y de la v1 salen de reglas, no de personas. Una auditoría manual sobre una muestra sin ajustar estima ≈ 85 % de acierto en categoría y ≈ 93 % en prioridad.
- Correo y Accesos están reforzados con variantes por retrotraducción; Correo solo tiene 140 tickets reales.
- El historial de asignaciones se simula con reglas calibradas con `issues.csv`; no son registros de trabajo real.
- Al evaluar, usa solo los tickets reales (`origen_etiqueta != "aumento"`).

Los datos tienen su origen en fuentes públicas recopiladas, traducidas y depuradas (`reports/inventario_fuentes.md`). La carpeta `Dataset/` contiene las fuentes originales: **no se modifican ni se mueven**; el trabajo se hace sobre las copias de `data/raw/`.

## Instalación (Windows)

Requisitos: Python 3.11, Git. No hace falta GPU para entrenar ni servir. Una GPU NVIDIA solo acelera la traducción (≈ 23 veces) y el aumento de datos.

```bash
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

> Si Windows muestra «An Application Control policy has blocked this file» al importar `torch` o `pandas`, el Control de aplicaciones inteligente (Smart App Control) está bloqueando los binarios sin firmar de Python. Hay que desactivarlo en *Seguridad de Windows › Control de aplicaciones y del explorador*; es una decisión del usuario y no se puede revertir sin reinstalar Windows.

Entorno opcional con GPU, solo para traducir y aumentar:

```bash
py -3.11 -m venv .venv-traduccion
.venv-traduccion\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cu126
.venv-traduccion\Scripts\python -m pip install transformers sentencepiece sacremoses pandas pyarrow
```

## Reproducir los datos

Cada script se puede ejecutar por separado y deja su salida en `data/` o `reports/`. Las rutas son relativas a la raíz y las semillas son fijas (42). Orden:

```bash
# 0. Copiar las fuentes originales (solo la primera vez)
copy Dataset\* data\raw\

# 1–2. Inventario de fuentes -> reports/inventario_fuentes.md
.venv\Scripts\python -m src.data.inventario

# 3. Filtrado de colas y traducción en/de/it -> es (con GPU, ≈ 10 min; reanudable por caché)
.venv\Scripts\python -m src.data.filtrar
.venv-traduccion\Scripts\python -m src.data.traduccion
.venv\Scripts\python -m src.data.muestra_calidad            # muestra de 100 traducciones para revisión

# 4. Unificación y etiquetado con reglas, y aumento por retrotraducción (GPU)
.venv\Scripts\python -m src.data.unificar                   # -> data/processed/tickets_base.csv
.venv-traduccion\Scripts\python -m src.data.aumentar        # -> data/processed/tickets.csv
.venv\Scripts\python -m src.data.auditoria medir            # acierto sobre las muestras auditadas

# 5. División 70/15/15 por grupo y análisis exploratorio
.venv\Scripts\python -m src.data.dividir
.venv\Scripts\python -m src.data.eda

# 6. Técnicos, historial de asignaciones y soluciones rápidas
.venv\Scripts\python -m src.data.auxiliares
.venv\Scripts\python -m src.data.soluciones_rapidas
```

Pruebas de los datos:

```bash
.venv\Scripts\python -m pytest tests/ -q
```

Entrenar los modelos, levantar la API de inferencia y abrir la página de prueba se documentará aquí al terminar los pasos 7 a 10.

## Estructura

```
Dataset/              fuentes originales (no tocar)
data/raw/             copia de Dataset/ (no versionada)
data/interim/         por fuente: filtrado, traducido, caché de traducción (no versionada)
data/processed/       tickets.csv, train/val/test.csv, tecnicos.csv, historial_asignaciones.csv, soluciones_rapidas.json
notebooks/            01_eda.ipynb
src/data/             inventario, filtrar, traduccion, mapeo, unificar, aumentar, auditoria, dividir, eda, auxiliares, soluciones_rapidas
src/models/           (paso 7) gru_clasificador, mlp_prioridad, mlp_asignacion, similitud
src/training/         (pasos 7–8) entrenar_*, evaluar, reentrenar, registro
src/service/          (pasos 9–10) API FastAPI y página de prueba
models/               artefactos por versión y registry.json
reports/              inventario, reglas, auditoría, EDA, calidad de traducción y, más adelante, métricas
tests/                pruebas con pytest
```

## Convenciones

- Todo el código, comentarios, interfaz y reportes en español.
- Python 3.11 en `.venv`; PyTorch en CPU para entrenar y servir.
- Taxonomía — categorías: Hardware, Software, Red, Accesos, Correo, Seguridad; prioridades: Baja, Media, Alta, Crítica; impacto: Bajo, Medio, Alto; urgencia: Baja, Media, Alta (la prioridad sigue la matriz impacto × urgencia); roles: Usuario, Soporte, Administrador.
