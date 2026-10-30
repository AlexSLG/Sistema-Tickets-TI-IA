# CRISP-ML(Q) · documento de cierre

El proyecto siguió las seis fases de CRISP-ML(Q) (*Cross-Industry Standard Process for Machine Learning with Quality assurance*) dentro de tres sprints de Scrum. Para cada fase se indica el objetivo, lo que se hizo, las evidencias en el repositorio, el aseguramiento de calidad (riesgos y cómo se verificaron) y el sprint.

## Resumen

| # | Fase | Sprint | Evidencia principal | Estado |
|---|---|---|---|---|
| 1 | Comprensión del negocio y de los datos | 1 | `reports/inventario_fuentes.md`, `reports/eda.md`, `PLAN_SPRINT1.md` (criterios de éxito) | Completa |
| 2 | Preparación de datos | 1 | `reports/*_resumen.md`, `reglas_etiquetado.md`, `calidad_traduccion.md`, `auditoria_etiquetas.md`, `tests/test_datos.py` | Completa |
| 3 | Modelado | 1 | `reports/informe_modelos.md` (§3–6), `comparacion_gru.json`, `src/models/`, `src/training/` | Completa |
| 4 | Evaluación | 1 y 3 | `reports/informe_modelos.md`, `metricas.json`, `bootstrap_gru_vs_base.json`; conjunto del equipo: `data/prueba_equipo/`, `src/training/evaluar_prueba_equipo.py` | Completa en `test.csv`; **validación con el conjunto del equipo pendiente de sus tickets** |
| 5 | Despliegue | 2 y 3 | Aplicación (`src/`), `docker-compose.yml`, `reports/rendimiento.md`, `reports/verificacion_instalacion.md`, manuales | Completa |
| 6 | Monitoreo y mantenimiento | 2 y 3 | Panel de métricas, correcciones, `src/training/reentrenar.py`, `models/registry.json`, `src/training/ciclo_aprendizaje.py` | Completa; ciclo verificado con datos del equipo pendiente de sus tickets |

---

## 1. Comprensión del negocio y de los datos (Sprint 1)

**Objetivo.** Reducir el tiempo de atención de una mesa de ayuda TI: clasificar y priorizar automáticamente los tickets escritos en español, sugerir el técnico adecuado sin saturar a nadie, resolver los problemas comunes con autoservicio y aprender de las correcciones de Soporte.

**Criterios de éxito definidos antes de entrenar** (`PLAN_SPRINT1.md`): F1 macro de categoría ≥ 0,85 y mejor que un modelo base; F1 macro de prioridad ≥ 0,80 con recall de Crítica ≥ 0,85; técnico esperado en primer lugar ≥ 80 %; ningún técnico por encima de su límite si hay otro disponible; ≥ 3 de 5 casos similares de la misma categoría; respuesta < 2 s en CPU; aprendizaje continuo sin regresiones.

**Restricciones.** Solo MLP, CNN, RNN, LSTM, GRU y Autoencoder (sin transformers ni modelos de lenguaje preentrenados en el sistema); CPU; instalación en un servidor local; todo en español.

**Qué se hizo.** Inventario de cinco fuentes públicas (`reports/inventario_fuentes.md`: 28 587 tickets multilingües, 812 en español, 1 800 de un conjunto adicional, 66 691 incidencias con tiempos y responsables, 200 de soporte técnico) y análisis exploratorio (`reports/eda.md`, `notebooks/01_eda.ipynb`, figuras `reports/figuras/eda_*.png`).

**Aseguramiento de calidad.**
- Riesgo: ninguna fuente tiene las seis categorías del negocio ni impacto/urgencia → se decidió etiquetar con reglas documentadas y auditarlas (fase 2).
- Riesgo: textos en inglés/alemán → traducción como preprocesamiento, con control de calidad.
- Viabilidad: los criterios se fijaron con números, antes de entrenar, y se verifican con pruebas automáticas.

## 2. Preparación de datos (Sprint 1)

**Qué se hizo.**
1. Filtrado de colas de TI y de tickets comerciales (`reports/filtrado_resumen.md`).
2. Traducción con MarianMT (opus-mt) solo como preprocesamiento (`reports/calidad_traduccion.md`, revisión de una muestra).
3. Unificación, depuración de duplicados y casi duplicados (coseno ≥ 0,88) (`reports/unificacion_resumen.md`).
4. Etiquetado de categoría y prioridad con reglas (`src/data/mapeo.py`, `reports/reglas_etiquetado.md`); impacto, urgencia y usuarios afectados derivados de la prioridad y del texto.
5. Aumento por retrotraducción solo para Accesos y Correo, marcado como `aumento` y excluido de la evaluación (`reports/aumento_resumen.md`).
6. División 70/15/15 **por grupo** (un ticket y sus variantes nunca se separan), estratificada, semilla 42 (`reports/division_resumen.md`).
7. Datos auxiliares (técnicos, historial de asignaciones, soluciones rápidas) derivados con reglas documentadas y calibradas con `issues.csv` (`reports/datos_auxiliares.md`).

**Aseguramiento de calidad.**
- **Auditoría manual de etiquetas** (`reports/auditoria_etiquetas.md`): ≈ 85 % de acierto en categoría y ≈ 93 % en prioridad (n = 60, ±9 puntos); errores sistemáticos corregidos en las reglas.
- **Sin fugas** entre entrenamiento y prueba: división por grupo y prueba automática.
- **Integridad**: `tests/test_datos.py` (valores de la taxonomía, sin vacíos ni duplicados, grupos completos, proporciones de la división).
- Fuentes originales intactas en `Dataset/`; se trabaja sobre copias en `data/raw/`.

## 3. Modelado (Sprint 1)

**Qué se hizo** (`reports/informe_modelos.md` §3):

| Función | Modelo |
|---|---|
| Categoría + embedding del ticket | GRU bidireccional de 2 capas (embedding 128, oculta 128, pooling máximo + medio → 512) |
| Modelo base de referencia | TF-IDF + regresión logística |
| Prioridad | MLP (embedding + categoría + impacto + urgencia + usuarios) |
| Asignación | MLP por par ticket–técnico + reglas de balanceo |
| Casos similares | Coseno entre embeddings de la GRU |
| Soluciones rápidas | Coseno híbrido (TF-IDF de caracteres 0,7 + GRU 0,3) con umbral 0,70 calibrado |

Selección de la GRU entre variantes (1 o 2 capas, embedding 128 o 200) por F1 macro de validación (`reports/comparacion_gru.json`).

**Aseguramiento de calidad.** Semillas fijas (42); modelo base obligatorio para comparar; parada temprana con validación; pesos por clase para el desbalance; restricción de arquitecturas del curso revisada (sin transformers en el sistema); entrenamiento reproducible con `python -m src.training.entrenar_todo`.

## 4. Evaluación (Sprints 1 y 3)

**En `test.csv`, solo tickets reales** (`reports/informe_modelos.md` §1):

| Criterio | Resultado | ¿Cumple? |
|---|---|---|
| GRU de categoría F1 macro ≥ 0,85 | 0,884 | Sí |
| GRU mejor que el modelo base | 0,8837 frente a 0,8839 (IC 95 % de la diferencia −0,014 a +0,015) | Empate estadístico |
| MLP de prioridad F1 macro ≥ 0,80 / recall Crítica ≥ 0,85 | 0,923 / 0,953 | Sí |
| Técnico esperado primero ≥ 80 % | 85,0 % | Sí |
| Balanceo: violaciones de límite | 0 | Sí |
| ≥ 3 de 5 similares de la misma categoría | 89,5 % (validación) | Sí |

**Validación con el conjunto independiente del equipo (Sprint 3).** Preparado: plantilla e instrucciones (`data/prueba_equipo/LEEME.md`), validador con control de solapamiento contra los datos del proyecto (`src/data/validar_prueba_equipo.py`) y evaluación completa con matriz de confusión, errores y comparación con `test.csv` (`src/training/evaluar_prueba_equipo.py`). **Pendiente** de que el equipo entregue `data/prueba_equipo/tickets_equipo.csv` (≥ 60 tickets); ver `reports/pendientes_finales.md`.

**Aseguramiento de calidad.** Umbrales contra resultados con intervalos por bootstrap; análisis de errores y limitaciones explícitas (ruido de etiqueta ≈ 15 %, sesgo de escenario de la fuente principal, circularidad de la prioridad con impacto y urgencia) en `reports/informe_modelos.md` §9; no se maquillan resultados.

## 5. Despliegue (Sprints 2 y 3)

**Qué se hizo.** Aplicación web con tres roles (FastAPI + SQLAlchemy + interfaz HTML/JS), IA integrada en cada ticket, panel de métricas, administración de técnicos, usuarios, soluciones rápidas y modelos; Docker Compose con PostgreSQL 16 y arranque automático; manuales de instalación y de usuario con capturas reales. Arquitectura en `docs/arquitectura.md`; contrato en `docs/contrato_api.md`; modelo de datos en `docs/modelo_datos.md`.

**Aseguramiento de calidad.**
- Pruebas automáticas (`pytest`, 68 pruebas: permisos por rol, flujo completo, balanceo, HU26, endpoints protegidos, errores sin 500) y prueba E2E con Playwright (`tests/e2e/`); resultados en `reports/resultados_pruebas.md`.
- Prueba de humo del guion de demostración contra los contenedores (`scripts/prueba_humo.py`).
- **Instalación verificada en un entorno limpio** con Docker (`reports/verificacion_instalacion.md`).
- **Rendimiento** < 2 s: mediana 22 ms / p95 31 ms por análisis y 32 ms / 45 ms por registro (`reports/rendimiento.md`).
- Seguridad: contraseñas con bcrypt, JWT, endpoints de administración protegidos, secretos fuera del código (`.env`).

## 6. Monitoreo y mantenimiento (Sprints 2 y 3)

**Qué se hizo.**
- **Indicadores de la IA** en el panel: porcentaje de categorías y prioridades aceptadas (sin corrección), uso de soluciones rápidas, tiempos y cargas.
- **Correcciones** de Soporte guardadas en la BD y en `data/correcciones.csv`.
- **Reentrenamiento** con regla de no regresión (solo se publica si el F1 macro en `test.csv` iguala o supera al vigente), en un proceso aparte, con un mínimo configurable de correcciones (5).
- **Registro de versiones** (`models/registry.json`) con versiones publicadas y descartadas, y **restauración** desde la pantalla Modelos.
- **Soluciones rápidas administrables** (HU26): lo aprendido en tickets resueltos se convierte en autoservicio al instante.
- **Ciclo verificable** con datos nuevos (`src/training/ciclo_aprendizaje.py`): mitad A del conjunto del equipo como correcciones, mitad B como evaluación, porcentaje de correcciones reproducidas y prueba negativa con etiquetas erróneas.

**Aseguramiento de calidad.**
- Prueba de publicación y de descarte del reentrenamiento (`reports/prueba_reentrenamiento.md`: dos versiones descartadas por empeorar y una publicada al igualar).
- Prueba negativa de publicación en el ciclo del equipo (pendiente de sus tickets).
- Mínimo de correcciones: con pocas correcciones el cambio en F1 es menor que el ruido (±0,003); la regla evita reentrenamientos sin efecto.
- Pruebas automáticas del registro de versiones, del mínimo de correcciones y del reentrenamiento en subproceso.

## Riesgos residuales

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Ruido de etiqueta (≈ 15 % en categoría) y estilo de plantilla de la fuente principal | El rendimiento con tickets escritos por usuarios reales puede ser menor que en `test.csv` | Validación con el conjunto del equipo; correcciones de Soporte y reentrenamiento |
| Prioridad muy dependiente de impacto y urgencia | Si el usuario los marca mal, la prioridad será incorrecta | Soporte corrige la prioridad; recomendación de guiar al usuario al elegir impacto y urgencia |
| Conjunto de referencia del reentrenamiento = conjunto de prueba | Las decisiones de publicar se apoyan siempre en los mismos tickets | Documentado; usar el conjunto del equipo como segunda referencia (mitad B) |
| Historial de asignaciones derivado por reglas | El MLP de asignación aprende la regla, no el comportamiento real | Reentrenar cuando haya historial real en la tabla `historial` |
| Pocas soluciones rápidas validadas por Soporte | Cobertura baja del autoservicio | HU26: Soporte agrega y edita soluciones desde los tickets resueltos |
| Un solo servidor, sin copias de seguridad automáticas | Pérdida de datos ante una falla del disco | Respaldar el volumen `pgdata` y las carpetas `models/` y `data/` (manual de instalación) |
