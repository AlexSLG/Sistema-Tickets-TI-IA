# Plan del Sprint 1 · Modelos (30/09 – 12/10/2026)

**Meta del sprint:** modelos de clasificación, prioridad, asignación y similitud entrenados, evaluados y servidos por una API de inferencia lista para integrarse en el Sprint 2, con una **página web de prueba** que demuestre su funcionamiento en la revisión del sprint.

Trabaja los pasos **en orden**. Al terminar cada paso, muestra un resumen corto de resultados y espera confirmación antes de seguir con los pasos 4 y 7 (son los que más decisiones implican).

---

## 0. Fuentes disponibles (`Dataset/`)

Revisadas el 09/10/2026:

| Archivo | Filas | Idioma | Qué trae | Uso |
|---|---|---|---|---|
| `aa_dataset-tickets-multi-lang-5-2-50-version.csv` | 28 587 | inglés 16 338, alemán 12 249 | `subject`, `body`, `answer`, `type` (Incident/Request/Problem/Change), `queue` (10 colas), `priority` (low/medium/high), `tag_1..tag_8` | **Fuente principal de texto.** `answer` sirve como solución para casos similares y soluciones rápidas |
| `dataset_clean_es_812.csv` | 812 | español | `text`, `categoria`, `prioridad`, `queue`, `type` | Versión 1 del equipo, derivada de la fuente anterior. **Sus etiquetas tienen errores** (ej. facturación etiquetada como Accesos; Correo sobrerrepresentado con 336). Reetiquetar con las reglas nuevas y deduplicar contra la fuente principal |
| `Dataset_ticket.xlsx` | 1 800 | inglés e italiano | `Category`, `Subcategory` (18 × 100), `Text` | **Fuente limpia de categorías de TI.** No trae prioridad |
| `tech-support-ticket-analytics.csv` | 200 | inglés | `issue_category`, `issue_description`, `priority` (low/medium/high/**urgent**), agente asignado, `resolution_notes`, escalamiento | Única fuente con nivel urgente (→ Crítica). `resolution_notes` alimenta las soluciones rápidas |
| `issues.csv` | 66 691 | — (sin texto) | prioridad, responsable (381), tiempos por estado del flujo, pasos de proceso, comentarios | **No sirve para los modelos de texto.** Se usa para que el historial de asignaciones tenga cargas, tiempos de resolución y reasignaciones realistas |

Datos que **ninguna fuente trae** y se derivan con reglas documentadas: impacto, urgencia, usuarios afectados, plantel de técnicos con aptitudes e historial de asignaciones. Ninguna fuente está en español nativo salvo la v1, así que se traduce.

---

## 1. Repositorio y entorno · Jira SCRUM-4

```
Sistema_de_tickets_TI_con_IA/
├── Dataset/              # fuentes originales (no tocar)
├── data/
│   ├── raw/              # copia de Dataset/
│   ├── interim/          # por fuente: filtrado, traducido, mapeado
│   └── processed/        # tickets.csv + splits (train/val/test) + auxiliares
├── notebooks/            # 01_eda.ipynb
├── src/
│   ├── data/             # inventario, traduccion, mapeo, unificar, dividir, auxiliares
│   ├── models/           # gru_clasificador.py, mlp_prioridad.py, mlp_asignacion.py, similitud.py
│   ├── training/         # entrenar_*.py, evaluar.py, reentrenar.py, registro.py
│   └── service/          # app.py (FastAPI), schemas.py, static/ (página de prueba)
├── models/               # artefactos por versión + registry.json
├── reports/              # inventario, reglas, EDA, métricas, figuras
├── tests/
├── requirements.txt
├── Dockerfile
├── .gitignore            # excluir .venv, data/raw, data/interim, modelos pesados
└── README.md             # cómo instalar, entrenar, levantar la API y abrir la página
```

- `git init`, primer commit. Crear `.venv` con Python 3.11 e instalar dependencias (torch CPU, pandas, scikit-learn, fastapi, uvicorn, transformers, sentencepiece, openpyxl, matplotlib, pytest).

## 2. Inventario de fuentes · SCRUM-97

`src/data/inventario.py` → `reports/inventario_fuentes.md`: por archivo, filas, columnas, idiomas, valores de categoría/prioridad/cola/etiquetas, nulos y licencia si se conoce.

## 3. Filtrado y traducción · SCRUM-98

**Filtrar antes de traducir** para no gastar tiempo:
- Fuente principal: conservar las colas `Technical Support`, `IT Support`, `Product Support` y `Service Outages and Maintenance`. Descartar `Billing and Payments`, `Returns and Exchanges`, `Sales and Pre-Sales`, `Human Resources`, `General Inquiry`. De `Customer Service`, conservar solo filas con etiquetas de TI (Login, Account, Network, Security, Hardware, IT).
- Eliminar tickets sin cuerpo o con menos de 5 palabras.
- Tomar como máximo unas **9 000 filas** balanceadas de la fuente principal (la traducción en CPU es lenta; medir velocidad con 100 filas y estimar el tiempo antes de lanzar todo).

**Traducir** con MarianMT (`Helsinki-NLP/opus-mt-en-es`, `opus-mt-de-es`, `opus-mt-it-es`):
- Por lotes, con caché en disco (`data/interim/traducciones_cache.parquet`) para poder reanudar si se corta.
- Conservar el texto original en `texto_original`.
- Proteger términos técnicos (VPN, Outlook, Wi-Fi, DNS, etc.) y marcadores como `<name>`, `<acc_num>`.
- Revisar una muestra aleatoria de 100 traducciones y anotar errores frecuentes en `reports/calidad_traduccion.md`.

## 4. Mapeo, depuración y unificación · SCRUM-99

**Esquema final** (`data/processed/tickets.csv`):

| Columna | Descripción |
|---|---|
| `id`, `fuente`, `idioma_original`, `texto_original` | trazabilidad |
| `titulo`, `descripcion` | texto en español (si no hay asunto, título = primera oración) |
| `categoria` | Hardware, Software, Red, Accesos, Correo, Seguridad |
| `prioridad` | Baja, Media, Alta, Crítica |
| `impacto`, `urgencia` | Bajo/Medio/Alto · Baja/Media/Alta |
| `usuarios_afectados` | entero (1, 5, 20, 100…) |
| `solucion` | respuesta del agente si existe |
| `origen_etiqueta` | `fuente` o `regla`, para saber cómo se obtuvo cada etiqueta |

**Categoría:**
- `Dataset_ticket.xlsx` por subcategoría: CPU, Disk, Keyboard, Memory, Monitor, Mouse → Hardware · DHCP, DNS, IP Address, VPN, Wireless → Red · Email → Correo · Antivirus → Seguridad · Operating System, Internal Application, DB2, MS SQL Server, Oracle → Software. Revisar si alguna subcategoría de Inquiry/Help encaja mejor en Accesos (permisos, carpetas, autorizaciones).
- `tech-support`: software → Software, hardware → Hardware, network → Red; descartar billing; revisar "other" a mano.
- Fuente principal y v1: reglas por etiquetas y palabras clave en español (ej. Login/Account/contraseña/permiso/bloqueo → Accesos; Security/phishing/virus/malware → Seguridad; correo/Outlook/buzón → Correo; red/VPN/wifi/internet → Red; impresora/laptop/disco/monitor → Hardware; resto de fallos de aplicación → Software). Documentar todas las reglas.

**Prioridad:** low → Baja, medium → Media, high → Alta, urgent → Crítica. Además, Crítica cuando es Alta y el texto indica caída total, servicio de producción o muchos usuarios afectados (etiquetas Outage/Disruption/Crash). Como referencia, en `issues.csv` las prioridades Highest + Blocker son ≈ 8 % de las conocidas; apuntar a una proporción similar.

**Impacto, urgencia y usuarios afectados:** reglas por palabras clave (ej. "toda la oficina", "servidor", "todos" → impacto Alto; "no puedo trabajar", "urgente", "caído" → urgencia Alta), coherentes con la prioridad según la matriz impacto × urgencia, con un pequeño porcentaje de excepciones para que el MLP no aprenda solo la matriz.

**Depuración:** quitar duplicados exactos y casi duplicados (similitud de texto alta), textos fuera de TI y registros sin etiqueta. Deduplicar la v1 contra la fuente principal.

**Balance:** objetivo ≥ 600 tickets por categoría. Si Accesos o Seguridad quedan cortas, ampliar con retrotraducción (es → en → es) de tickets reales de esas clases, marcando `origen_etiqueta`.

Todas las reglas van en `reports/reglas_etiquetado.md`, con su justificación.

## 5. EDA y división · SCRUM-11

`notebooks/01_eda.ipynb` + `reports/eda.md`: distribución de categorías y prioridades, longitud de textos, cruces categoría × prioridad, ejemplos por clase. División estratificada **70/15/15** con semilla 42 en `data/processed/train.csv`, `val.csv`, `test.csv`.

El conjunto de prueba escrito a mano por el equipo (SCRUM-100) irá en `data/processed/test_equipo.csv` cuando esté listo; dejar el código preparado para evaluarlo.

## 6. Datos auxiliares · SCRUM-101 y SCRUM-102

- `data/processed/tecnicos.csv`: 8 técnicos con aptitud 1–5 por categoría (al menos 2 técnicos aptos por categoría), límite de carga y área.
- `data/processed/historial_asignaciones.csv`: para cada ticket de entrenamiento, el técnico que lo atendió, su carga en ese momento, el tiempo de resolución y si hubo reasignación. Construido con reglas documentadas; las cargas y tiempos se calibran con las distribuciones reales de `issues.csv` (tickets por responsable, tiempo total por prioridad, pasos del proceso).
- `data/processed/soluciones_rapidas.json`: unas 50 entradas para errores comunes, cada una con `id`, `categoria`, `problema`, `frases_ejemplo` (3–5 formas de describirlo) y `pasos`. Semillas: las `answer` de la fuente principal y las `resolution_notes` de `tech-support`. Ejemplo: "mi equipo no tiene internet" → revisar cable o wifi, reiniciar equipo y router.

## 7. Modelos · SCRUM-13, 14, 15, 16

Todos en PyTorch, entrenables en CPU en minutos, con parada temprana sobre validación.

| Modelo | Arquitectura | Criterio de aceptación |
|---|---|---|
| **Modelo base** | TF-IDF + regresión logística (scikit-learn) | referencia |
| **GRU de clasificación** | tokenización por palabras (vocabulario del train, `max_len` 128) → Embedding 128 → GRU bidireccional 128 → max + mean pooling (embedding del ticket, 512 dims) → Dropout → Dense → 6 clases | F1 macro ≥ 0,85 en test y mejor que el modelo base |
| **MLP de prioridad** | [embedding del ticket + one-hot categoría + impacto + urgencia + log(usuarios)] → 256 → 128 → 4, Dropout, pesos por clase | F1 macro ≥ 0,80; recall de Crítica ≥ 0,85 |
| **MLP de asignación** | por cada par (ticket, técnico): [categoría, prioridad, aptitud del técnico en esa categoría, carga/límite, tiempo medio histórico] → 64 → 32 → puntaje | técnico esperado en primer lugar en ≥ 80 % de los casos |
| **Reglas de balanceo** | ordenar técnicos por puntaje; saltar los que superen su límite; si todos están al límite, el de menor carga | ningún técnico supera su límite si hay otro apto |
| **Similitud y soluciones rápidas** | similitud coseno entre embeddings; índice de tickets resueltos y de `frases_ejemplo` de soluciones rápidas; umbral configurable | 3 de 5 similares de la misma categoría en una muestra de 30 |

Si la GRU no llega al umbral, probar en este orden: más épocas, `max_len`, embedding 200, dos capas GRU, revisar errores de etiquetado en la matriz de confusión.

## 8. Reentrenamiento y versiones · SCRUM-18

- `src/training/reentrenar.py`: une los datos de entrenamiento con `data/correcciones.csv` (columnas: `titulo`, `descripcion`, `categoria_corregida`, `prioridad_corregida`, `tecnico_reasignado`), reentrena y evalúa contra un **conjunto de referencia fijo**.
- Publica la versión nueva solo si su F1 macro iguala o supera al de la vigente; si no, la descarta y lo registra.
- `models/registry.json`: versión, fecha, métricas, número de correcciones usadas y versión activa. Función para restaurar la anterior.

## 9. Servicio de inferencia · SCRUM-17

FastAPI en `src/service/app.py`, cargando la versión activa del registro:

| Endpoint | Entrada | Salida |
|---|---|---|
| `POST /api/analizar` | título, descripción, impacto, urgencia, usuarios afectados | categoría + probabilidades, prioridad + probabilidades, técnicos ordenados con carga, solución rápida (o nula), 5 similares con su solución, tiempo de respuesta |
| `POST /api/similares` | texto, k | k tickets similares |
| `GET/PUT /api/tecnicos` | — / cargas | estado de técnicos (para probar el balanceo) |
| `POST /api/correcciones` | corrección | la guarda en `data/correcciones.csv` |
| `POST /api/reentrenar` | — | comparación versión nueva vs vigente y si se publicó |
| `GET /api/modelos` | — | registro de versiones y métricas |
| `GET /api/metricas` | — | métricas y rutas de figuras de `reports/` |

- Documentación automática en `/docs`.
- Pruebas en `tests/` (respuesta válida, tiempos < 2 s en CPU, balanceo de carga, umbral de soluciones rápidas).
- `Dockerfile` que levanta el servicio con los modelos.

## 10. Página web de prueba · SCRUM-103

Página estática (HTML + CSS + JS sin framework) servida por el mismo FastAPI en `/` o `/laboratorio`. **No es el producto final**; su objetivo es demostrar los modelos en la revisión del sprint. Pestañas:

1. **Analizar ticket:** formulario (título, descripción, impacto, urgencia, usuarios afectados) y botones con ejemplos precargados. Muestra categoría y prioridad con barras de probabilidad, técnicos ordenados por adecuación con su carga, solución rápida sugerida y 5 similares.
2. **Balanceo de carga:** tabla de técnicos con su carga editable; al saturar al más apto, se ve cómo la asignación pasa al siguiente.
3. **Métricas:** F1, precisión y recall por modelo, matrices de confusión y comparación con el modelo base.
4. **Aprendizaje continuo:** registrar correcciones, lanzar el reentrenamiento y ver la comparación de versiones y cuál quedó activa.

## 11. Diseño para el Sprint 2 · SCRUM-12

`docs/modelo_datos.md` con el diagrama entidad-relación en Mermaid (usuarios, roles, técnicos, aptitudes, tickets, comentarios, historial de estados, soluciones, soluciones rápidas, correcciones, versiones de modelos) y `docs/contrato_api.md` con los endpoints de inferencia que usará el backend.

## 12. Evaluación final · SCRUM-19

`src/training/evaluar.py` → `reports/metricas.json`, `reports/figuras/*.png` (matrices de confusión, curvas de pérdida) e `reports/informe_modelos.md` con: datos usados, reglas de etiquetado, arquitectura de cada modelo, métricas frente a los umbrales y comparación con el modelo base, limitaciones.

---

## Calendario sugerido

| Día | Pasos |
|---|---|
| Vie 9 | 1, 2, 3 (lanzar traducción), 4 |
| Sáb 10 | 5, 6, 7 (modelo base, GRU, MLP de prioridad) |
| Dom 11 | 7 (asignación, similitud), 8, 9, 10 |
| Lun 12 | 11, 12, revisión del sprint con la página de prueba y retrospectiva |

## Tareas de Jira que se cierran

| Paso | Jira | Historia |
|---|---|---|
| 1 | SCRUM-4 | HU10 (SCRUM-69) |
| 2 | SCRUM-97 | HU01 (SCRUM-60) |
| 3 | SCRUM-98 | HU01 |
| 4 | SCRUM-99 | HU01 |
| 5 | SCRUM-11 | HU01 |
| — | SCRUM-100 (prueba escrita por el equipo) | HU01 |
| 6 | SCRUM-101, SCRUM-102 | HU09 (SCRUM-68), HU06 (SCRUM-65) |
| 7 | SCRUM-13, SCRUM-14, SCRUM-15, SCRUM-16 | HU02–HU09 (SCRUM-61 a SCRUM-68) |
| 8 | SCRUM-18 | HU11 (SCRUM-70) |
| 9 | SCRUM-17 | HU10 (SCRUM-69) |
| 10 | SCRUM-103 | HU10 |
| 11 | SCRUM-12 | HU12 (SCRUM-71) |
| 12 | SCRUM-19 | HU03, HU05 |
| Cierre | SCRUM-20 | — |
