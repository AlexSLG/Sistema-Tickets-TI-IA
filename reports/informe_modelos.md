# Informe de modelos · Sprint 1

Versión evaluada: **v1** (`models/registry.json`). Todas las métricas son sobre el conjunto de **prueba** (`data/processed/test.csv`), solo con **tickets reales** (se excluyen las variantes aumentadas), salvo que se indique otra cosa. Métricas completas en `reports/metricas.json` y figuras en `reports/figuras/`.

## 1. Resumen y criterios de aceptación

| Modelo | Criterio del plan | Resultado | ¿Cumple? |
|---|---|---|---|
| GRU de categoría | F1 macro ≥ 0,85 en test | **0,884** | Sí |
| GRU de categoría | mejor que el modelo base | 0,8837 frente a 0,8839 (diferencia −0,0002; IC 95 % −0,014 a +0,015) | **No: empate estadístico** |
| MLP de prioridad | F1 macro ≥ 0,80 | **0,923** | Sí |
| MLP de prioridad | recall de Crítica ≥ 0,85 | **0,953** | Sí |
| MLP de asignación | técnico esperado en primer lugar ≥ 80 % | **85,0 %** (techo de la regla: 90,5 %) | Sí |
| Reglas de balanceo | ningún técnico supera su límite si hay otro disponible | **0 violaciones** en 1 417 tickets (sin balanceo: 2) | Sí |
| Similitud | 3 de 5 similares de la misma categoría en una muestra de 30 | **87 %** de la muestra de 30; **89,5 %** en los 1 329 tickets de validación | Sí |
| Soluciones rápidas | (umbral configurable) | umbral 0,70; detector conservador (apartado 6) | — |

Dos cosas que conviene leer con cuidado antes de las cifras:

1. **El MLP de prioridad no aporta nada sobre la regla de la matriz impacto × urgencia** (0,923 frente a 0,931 de la regla pura). Impacto y urgencia se derivaron de la prioridad al etiquetar, así que el modelo reproduce esa matriz. Sin esas dos variables el F1 cae a 0,58. Apartado 5.
2. **La GRU no supera al modelo base.** Empatan dentro del margen de error. Apartado 4.

## 2. Datos

- 9 379 tickets en español (8 834 reales y 545 variantes por retrotraducción de Correo y Accesos), de cuatro fuentes públicas recopiladas, traducidas (MarianMT) y depuradas (`reports/inventario_fuentes.md`, `reports/calidad_traduccion.md`).
- División 70/15/15 por `grupo` y estratificada por categoría y prioridad (`reports/division_resumen.md`): train 6 545, val 1 417, test 1 417 (1 331 reales). Las variantes de un ticket quedan siempre en su mismo conjunto.
- Categorías en test (reales): Software 643, Seguridad 223, Red 216, Hardware 174, Accesos 54, **Correo 21**. Con tan pocos tickets en Correo y Accesos, el F1 de esas clases tiene mucha incertidumbre.
- **Etiquetas:** la categoría y la prioridad de la fuente principal y de la v1 salen de reglas documentadas (`reports/reglas_etiquetado.md`). Una auditoría manual (`reports/auditoria_etiquetas.md`) estimó **≈ 85 % de acierto en categoría y ≈ 93 % en prioridad** sobre una muestra sin ajustar (n = 60, ±9 puntos). Impacto, urgencia y usuarios afectados se derivan de la prioridad y del texto; no existen en ninguna fuente.

## 3. Arquitecturas

| Componente | Arquitectura | Parámetros |
|---|---|---:|
| **Modelo base** | TF-IDF (1–2-gramas, `min_df` 2) + regresión logística con pesos por clase; `C` = 10 elegido en validación | — |
| **GRU de categoría** | tokenización por palabras (vocabulario del train, 6 091 palabras, `max_len` 128) → Embedding 128 → **GRU bidireccional de 2 capas** (oculta 128) → pooling máximo + medio (**embedding del ticket, 512 dim.**) → Dropout 0,4 → Dense 6. Pérdida con pesos por clase y suavizado de etiquetas 0,05; Adam (lr 2e-3); parada temprana por F1 macro de validación (26 épocas; del orden de una hora en CPU, con otras tareas en paralelo) | 1 277 318 |
| **MLP de prioridad** | [embedding de la GRU (512) + categoría (one-hot en entrenamiento, probabilidades de la GRU en inferencia) + impacto + urgencia + log(usuarios)] → 256 → 128 → 4; dropout 0,3, pesos por clase, parada temprana | 168 068 |
| **MLP de asignación** | por par (ticket, técnico): [categoría (6), prioridad (4), aptitud/5, carga/límite, tiempo medio histórico/24 h] → 64 → 32 → puntaje; se entrena como entropía cruzada sobre los 8 técnicos candidatos | 3 009 |
| **Reglas de balanceo** | ordena por puntaje; los técnicos con carga ≥ límite pasan al final (entre ellos, menor ocupación primero); si todos están al límite, se elige el de menor ocupación | — |
| **Similitud** | coseno entre embeddings de la GRU sobre 7 503 tickets reales (train + val) | — |
| **Soluciones rápidas** | 50 entradas, 253 textos indexados (frases de ejemplo + enunciado). Puntaje = 0,7 · coseno TF-IDF de caracteres (3–5-gramas) + 0,3 · coseno de embeddings de la GRU; umbral 0,70 | — |

No se usan transformers ni modelos de lenguaje preentrenados en el sistema. La traducción (MarianMT) fue preprocesamiento.

**Elección de la GRU** (criterio: F1 macro de validación en tickets reales; `reports/comparacion_gru.json`). El plan pedía probar, si no se alcanzaba el modelo base: más épocas, `max_len`, embedding 200 y dos capas.

| Variante | Mejor F1 macro val | F1 macro test |
|---|---:|---:|
| 1 capa, embedding 128 | 0,851 | 0,874 |
| 1 capa, embedding 200 | 0,846 | 0,866 |
| **2 capas, embedding 128 (elegida)** | **0,867** | **0,884** |

El modelo base tiene 0,874 en validación. No se probó otro `max_len` porque solo el 4,6 % de los tickets supera 120 palabras.

## 4. Categoría: GRU frente al modelo base

| Clase | n | F1 base | F1 GRU | Precisión GRU | Recall GRU |
|---|---:|---:|---:|---:|---:|
| Hardware | 174 | 0,899 | 0,883 | 0,880 | 0,885 |
| Software | 643 | 0,920 | 0,915 | 0,924 | 0,907 |
| Red | 216 | 0,828 | 0,839 | 0,845 | 0,833 |
| Accesos | 54 | 0,846 | 0,860 | 0,776 | 0,963 |
| Correo | 21 | 0,837 | 0,857 | 0,857 | 0,857 |
| Seguridad | 223 | 0,973 | 0,949 | 0,946 | 0,951 |
| **F1 macro** | 1 331 | **0,8839** | **0,8837** | | |

Exactitud: base 0,907, GRU 0,901. Si se incluyen las variantes aumentadas, la GRU llega a 0,889 de F1 macro. Intervalos de confianza al 95 % (bootstrap, 1 000 remuestreos): GRU 0,853–0,907; base 0,852–0,908; **diferencia −0,0002 (−0,014 a +0,015)**. Los dos modelos coinciden en el 93,2 % de los tickets.

Exactitud por fuente (reales): `Dataset_ticket.xlsx` 0,973 (GRU) y 0,970 (base); fuente principal 0,886 y 0,893; `tech-support` 0,839 y 0,935 (31 tickets); v1 0,864 y 0,864.

**Por qué la GRU llega a 0,88 y no más, y por qué no supera al modelo base:**

1. **Techo de etiqueta.** La auditoría estimó que ≈ 15 % de las categorías de la fuente principal y de la v1 son discutibles. Un F1 macro de 0,88 sobre etiquetas con ese ruido está cerca de lo alcanzable. Los errores se concentran en la fuente principal (0,886 de exactitud frente a 0,973 en `Dataset_ticket.xlsx`, cuyas etiquetas vienen de la fuente).
2. **Las etiquetas salieron de reglas de palabras clave.** Un modelo lineal de bolsa de palabras (TF-IDF + regresión logística) reproduce casi exactamente ese proceso generador; una red recurrente tiene más capacidad, pero no más información que aprender.
3. **Datos pequeños.** 6 545 tickets de entrenamiento, con variantes de plantilla, para 1,3 millones de parámetros.
4. La diferencia no es significativa (IC 95 % de ±0,015). Lo que sí aporta la GRU es el **embedding de 512 dimensiones** que usan el MLP de prioridad y la búsqueda de casos similares (88,6–89,5 % frente al 81,6 % con TF-IDF): el modelo base no lo produce.

## 5. Prioridad

| Modelo | F1 macro | Exactitud | Recall Crítica |
|---|---:|---:|---:|
| Regla: matriz impacto × urgencia | 0,931 | 0,934 | 0,943 |
| **MLP completo** (embedding + categoría + impacto + urgencia + usuarios) | **0,923** | 0,926 | **0,953** |
| MLP sin embedding (solo variables tabulares) | 0,931 | 0,934 | 0,943 |
| MLP sin impacto ni urgencia (texto + categoría + usuarios) | 0,582 | 0,601 | 0,623 |
| Base TF-IDF + regresión logística (solo texto) | 0,638 | 0,645 | 0,604 |

F1 por clase del MLP (Baja, Media, Alta, Crítica): la matriz de confusión está en `reports/figuras/cm_prioridad_mlp.png`; Crítica (n = 106) tiene recall 0,953.

**Lectura honesta.** En la construcción de los datos, impacto y urgencia se eligieron para ser coherentes con la prioridad (matriz, con un 7 % de excepciones), así que predecir la prioridad con ellos es predecir la matriz: el MLP no mejora a la regla y, con el embedding añadido, incluso queda un punto por debajo. Sin ellos, solo con el texto, no se llega a 0,80 ni a 0,85 de recall en Crítica. **El criterio se cumple, pero no demuestra que el modelo entienda la gravedad del problema por el texto.** En el sistema real, impacto y urgencia deberán ser datos que aporte el solicitante o Soporte; con datos reales el MLP podrá aprender relaciones que la matriz no capture.

## 6. Asignación, balanceo, similitud y soluciones rápidas

**Asignación** (historial derivado con reglas documentadas, calibradas con `issues.csv`; `reports/datos_auxiliares.md`):

- Top-1 **85,0 %** (con balanceo 85,5 %), top-3 98,7 %. La regla determinista que generó el historial reproduce la asignación inicial en el 90,5 % (el resto es ruido de la decisión), así que el MLP alcanza el 94 % de su techo. Referencia «el más apto sin mirar la carga»: 39,1 %.
- Top-1 por categoría: Accesos 0,945, Correo 0,943, Hardware 0,914, Seguridad 0,919, Red 0,903, **Software 0,768** (los tickets de Software se reparten entre tres técnicos con aptitud parecida y la carga decide).
- **Balanceo:** 0 violaciones del límite con las reglas (2 sin ellas); en 78 tickets de prueba (5,5 %) todos los técnicos estaban al límite y se eligió al de menor ocupación.
- Como el historial se generó con una regla, esta métrica demuestra que el modelo aprende esa regla, no que asigne bien a técnicos reales.

**Casos similares:** ≥ 3 de 5 vecinos de la misma categoría en el 89,5 % de los 1 329 tickets reales de validación (precisión@5 0,895) y en el 86,7 % de una muestra de 30; con TF-IDF, 81,6 % (precisión@5 0,758).

**Soluciones rápidas:** el embedding de la GRU, entrenado para clasificar categorías, distingue mal problemas concretos de una misma categoría (acierto del 22 % entre frases de una misma entrada). Con el híbrido TF-IDF de caracteres + GRU sube al 44 % (leave-one-out sobre las 203 frases; es una prueba exigente porque las frases de una entrada están redactadas a propósito de forma distinta). El umbral 0,70 se eligió para una precisión ≥ 0,85 en esa prueba. Resultado: **detector conservador**; solo dispara en el 0,3 % de los tickets largos de validación (y en esos casos la categoría coincide siempre) y sí con textos cortos parecidos a los ejemplos («mi equipo no tiene internet», «no puedo conectarme a la VPN»). Las entradas de Correo y Seguridad no tienen semilla en los datos y debe validarlas el equipo.

## 7. Aprendizaje continuo

`python -m src.training.reentrenar` une `train.csv` con `data/correcciones.csv`, reentrena a partir de los pesos de la versión vigente y compara en un conjunto de referencia fijo (`test.csv`, tickets reales). Solo se publica si el F1 macro de categoría iguala o supera al vigente; cada intento queda en `models/registry.json` y se puede restaurar una versión anterior.

Prueba con 6 correcciones de ejemplo (`reports/prueba_reentrenamiento.md`): dos versiones se **descartaron** por empeorar (0,8731 y 0,8707 frente a 0,8736) y una, con tasa de aprendizaje 0 para probar el camino de publicación, se **publicó** al igualar. Seis correcciones sobre 6 500 tickets no mueven el F1 más que el ruido (±0,003). El conjunto de referencia es el mismo test que se usa para evaluar; es lo que pide el plan, pero significa que cada decisión de publicar o descartar se apoya en él.

## 8. Servicio y pruebas

- API FastAPI (`/docs`) y página de prueba con las 4 pestañas del plan en `/`. Contrato en `docs/contrato_api.md`; modelo de datos del Sprint 2 en `docs/modelo_datos.md`.
- `/api/analizar`: **mediana 29 ms, p95 45 ms, máximo 52 ms** en CPU (60 llamadas; el criterio es < 2 s).
- 25 pruebas automáticas (`pytest tests/`): respuesta válida, tiempos < 2 s, balanceo de carga (el más apto saturado pasa al siguiente; ningún técnico supera su límite si hay otro disponible; todos al límite), umbral de soluciones rápidas, validación de entradas, correcciones, registro de versiones e integridad de los datos y de la división.

## 9. Limitaciones y riesgos

1. **Ruido de etiqueta (≈ 15 % en categoría)**: fija el techo de la GRU y hace poco fiable el F1 de Correo (21 tickets de prueba) y Accesos (54).
2. **Sesgo de escenario.** Seguridad y Software se distinguen en parte por el relato de plantilla (*hospital, datos médicos* frente a *análisis, inversión, plataforma*). Con texto de usuario real los resultados serán peores. Ejemplo medido: «Recibí un correo falso de mi banco que me pide mi contraseña, es phishing» se clasifica como Software o Correo, no como Seguridad; los reportes de virus y de acceso no autorizado sí se clasifican bien. **Debe verificarse con el conjunto de prueba escrito por el equipo (SCRUM-100).**
3. **Prioridad:** circularidad con impacto y urgencia (apartado 5).
4. **Asignación e historial derivados por reglas.** Los técnicos y su historial se construyeron con reglas documentadas (`reports/reglas_etiquetado.md`), no con registros de una mesa de ayuda en operación.
5. **Soluciones rápidas:** cobertura baja y entradas de Correo y Seguridad sin validar.
6. **Correcciones:** el efecto de unas pocas correcciones es menor que el ruido de evaluación; el conjunto de referencia coincide con el de prueba.
7. **Auditoría de etiquetas** hecha en una única revisión manual, no por el equipo.

## 10. Recomendaciones para el Sprint 2

- Incorporar tickets reales del equipo (SCRUM-100 y los que se registren en la aplicación) y reentrenar; son lo que más mejorará la categoría.
- Pedir impacto y urgencia al solicitante o a Soporte, o estimarlos con un modelo propio entrenado con tickets reales.
- Sustituir el historial derivado por reglas por el real (`asignaciones`) y recalibrar `limite_carga`.
- Calcular las cargas de los técnicos desde la base de datos y enviarlas en cada petición (hoy el servicio guarda un estado en memoria).
- Validar las 50 soluciones rápidas con Soporte y ampliarlas con las que se registren en `soluciones`.
- Considerar un conjunto de referencia distinto del de prueba para decidir las publicaciones.

## 11. Reproducir

```bash
python -m src.training.entrenar_todo --version v1     # base, GRU, MLP de prioridad, asignación, similitud (del orden de una hora en CPU; la GRU de 2 capas es la parte lenta)
python -m src.training.evaluar                        # reports/metricas.json y figuras
python -m pytest tests/ -q
uvicorn src.service.app:app --port 8000               # API y página de prueba en http://localhost:8000
```

Los modelos entrenados (`models/v1/`, ≈ 23 MB) no están en el repositorio; `models/registry.json` sí.
