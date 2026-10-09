# Auditoría de etiquetas (categoría y prioridad)

Objetivo: comprobar con una revisión manual si la categoría y la prioridad asignadas por las reglas del paso 4 son correctas, y corregir las reglas ante errores sistemáticos.
Código: `src/data/auditoria.py` (muestras, veredictos y medición); reglas en `src/data/mapeo.py`; criterios en `reports/reglas_etiquetado.md`.

## Método

- **Quién revisó:** una sola revisión manual, leyendo título y descripción de cada ticket. No es un etiquetado por pares ni por el equipo; ver "Limitaciones".
- **Qué se considera correcto:**
  - *Categoría:* la que un técnico de mesa de ayuda asignaría por el problema principal. Un ticket que no es de TI (facturación, marketing, información comercial) cuenta como error (`FUERA_TI`: no debía estar en el conjunto).
  - *Prioridad:* la que correspondería por el texto (caída de varios sistemas, pérdida de datos o intrusión → alta; consulta o petición de información → baja). Se aceptó una diferencia de criterio razonable en los casos dudosos, por lo que los números no son más estrictos que eso.
- **Muestras** (solo tickets reales, sin los aumentados, estratificadas por categoría):

| Muestra | n | Semilla | Se revisó con | ¿Se usó para ajustar reglas? |
|---|---:|---:|---|---|
| 1 | 200 (33–34 por categoría) | 42 | reglas del paso 4 originales | **Sí** (los errores de esta muestra motivaron las correcciones) |
| 2 | 60 (10 por categoría) | 7 | reglas tras la primera ronda de correcciones | **Sí** (segunda ronda) |
| 3 | 60 (10 por categoría) | 99 | reglas finales | **No**: es la estimación sin sesgo de las reglas finales |

## Resultados

| Momento | Muestra | Acierto en categoría | Acierto en prioridad |
|---|---|---:|---:|
| Reglas originales (paso 4) | 1 (n = 200) | **79,0 %** (158/200) | **80,0 %** (160/200) |
| Tras la 1.ª ronda de correcciones | 2 (n = 60, nueva) | 80,0 % (48/60) | 80,0 % (48/60) |
| Reglas finales, medidas sobre las muestras usadas para ajustar | 1 y 2 | 89,5 % y 91,7 % | 91,5 % y 90,0 % |
| **Reglas finales, muestra sin ajustar** | **3 (n = 60, nueva)** | **85,0 %** (51/60) | **93,3 %** (56/60) |

Lectura honesta: las cifras 89–92 % de las muestras 1 y 2 están **infladas** porque se ajustaron las reglas mirando esos mismos tickets. La estimación fiable de las reglas finales es la de la muestra 3: **≈ 85 % en categoría y ≈ 93 % en prioridad**, con un margen de ±9 puntos por el tamaño de la muestra (60). La mejora real respecto al 79 % / 80 % original es de unos 6 y 13 puntos, pero queda un 15 % de ruido en la categoría que no se elimina con reglas.

## Errores de la muestra 1 (reglas originales)

Por fuente (categoría / prioridad):

| Fuente | n | Categoría | Prioridad |
|---|---:|---:|---:|
| `Dataset_ticket.xlsx` (etiquetas de la fuente + prioridad derivada) | 54 | 94,4 % | 98,1 % |
| Fuente principal (reglas por palabras clave) | 125 | **72,8 %** | **71,2 %** |
| v1 (reglas por palabras clave) | 18 | 72,2 % | 83,3 % |
| `tech-support` (etiquetas de la fuente) | 3 | 100 % | 100 % |

Por categoría asignada (acierto en categoría): Seguridad 91 %, Red 76 %, Accesos 76 %, Software 85 %, Hardware 76 %, Correo 70 %.
El problema está en la **fuente principal y la v1**: relatos largos y genéricos donde una palabra suelta (correo, acceso, equipo, hardware) decide la categoría.

### Errores sistemáticos encontrados

| # | Patrón | Casos (muestra 1) | Causa |
|---|---|---:|---|
| 1 | **Tickets que no son de TI** (información del producto, publicidad, facturación, suscripciones, métricas de campañas, previsiones de inversión, consultoría con precios) | 10 | El filtro de "fuera de TI" se anulaba si aparecía cualquier palabra técnica |
| 2 | **Incidentes de seguridad con prioridad baja o media** (acceso no autorizado, violación de datos, brecha) | 11 | La prioridad venía del campo `priority` de la fuente, que no distingue los incidentes de las consultas |
| 3 | **Consultas y peticiones de información con prioridad Alta/Crítica** (guías de integración, buenas prácticas de seguridad, "solicito detalles") | 12 | Ídem |
| 4 | **Incidencias con prioridad Baja** (avería "urgente", interrupción de varios productos, pérdida de datos) | 6 | Ídem |
| 5 | **Interrupciones de servicio y fallos de plataforma etiquetados como Correo, Red, Hardware o Accesos** (deberían ser Software) por citar un producto (Outlook, Mailchimp) o la palabra "dispositivo"/"equipo" | 24 | "equipo" casi siempre es el equipo de trabajo, no hardware; Outlook aparece en listas de productos afectados |
| 6 | **Acceso no autorizado etiquetado como Accesos o Red** en vez de Seguridad | 4 | No había patrón para "no autorizado", "sospechoso", "comprometido" |
| 7 | **Peticiones de mejora de interfaz o funciones** etiquetadas como Accesos ("interfaz de permisos de usuario") | 1 | La palabra "permisos" pesaba más que la petición |
| 8 | **Marcas de antivirus** (Kaspersky, Bitdefender…) sin pista de categoría | 1 | Sin patrón |

### Correcciones aplicadas a las reglas

1. **Fuera de TI, regla dura** (`NO_TI_DURO`): facturación y reembolsos, precios y tarifas, publicidad, suscripciones, seguros, funciones/información de producto, previsiones de inversión, métricas y caída de compromiso de campañas, equipo de seguridad. Se descartan aunque mencionen algo técnico; también se aplica a `Dataset_ticket.xlsx` (p. ej. "factura de VPN más alta de lo habitual"). Se evitó una versión demasiado amplia: la primera descartaba 373 tickets, incluidos tickets de TI que solo mencionaban facturación o consultoría de pasada; la final descarta 262.
2. **Ajuste de prioridad** (`ajustar_prioridad`), sobre la fuente principal, la v1 y `Dataset_ticket.xlsx` (no sobre `tech-support`, que conserva la prioridad de su fuente):
   - incidente de seguridad (no consulta) → mínimo **Alta**;
   - consulta o petición de información sin incidencia → **Baja** si venía Alta o Crítica;
   - "urgente/inmediato" o interrupción que afecta a varios sistemas con prioridad Baja → **Media**;
   - pérdida de datos → mínimo **Alta**.
3. **Categoría:**
   - Seguridad: patrones de "no autorizado", "sospechoso", "comprometido", "violado" y marcas de antivirus.
   - Software: interrupciones del servicio, tiempo de inactividad, sobrecarga del servidor, sincronización, mejoras de interfaz, herramientas de campañas por correo (Mailchimp, SendGrid).
   - Correo: Outlook deja de ser señal fuerte (peso 3,5 → 2,5).
   - Hardware: se quitó "equipo" como señal.
   - Empates: Software pasa por delante de Hardware.
4. El aumento se regeneró con las reglas nuevas.

Efecto en el conjunto: 8 834 tickets reales (antes 9 024), prioridad Baja 32,1 %, Media 31,9 %, Alta 28,1 %, **Crítica 7,9 %**; categorías: Software 4 274, Seguridad 1 481, Red 1 437, Hardware 1 148, Accesos 600 (354 reales + 246 aumentados), Correo 439 (140 reales + 299 aumentados).

## Errores que quedan (muestra 3, reglas finales)

- **Categoría (9 de 60):** fallos de plataforma o navegador que las reglas ven como otra cosa (navegador que se bloquea → Hardware; desinstalación de VPN → Red; cámara del portátil → Software), un ticket de marketing (Software), un ticket cuyo texto es solo un saludo (Correo) y casos ambiguos entre Accesos, Seguridad y Software.
- **Prioridad (4 de 60):** una recomendación de seguridad con prioridad Alta, un ticket de marketing, una avería de impresora en Alta y un fallo de acceso al sitio en Alta.
- La fuente principal es la más débil: con textos de plantilla y relatos ajenos a TI (hospital, marketing, inversión), la categoría correcta depende del problema y no de las palabras.

## Limitaciones

1. **Un solo revisor, ajeno al equipo.** Los veredictos son de una única revisión y no sustituyen la revisión del equipo. Recomendación: que alguien del equipo revise las 60 filas de `data/interim/auditoria_muestra3.csv` (con las etiquetas finales) y contraste los veredictos de `src/data/auditoria.py` antes de dar por buena la cifra.
2. **Tamaño de muestra.** Con 60 tickets el intervalo de confianza del 85 % es de ±9 puntos aproximadamente.
3. **La evaluación de los modelos hereda este ruido.** Si ≈ 15 % de la categoría en la fuente principal es discutible, un F1 macro ≥ 0,85 en test (criterio del paso 7) es exigente: parte del "error" del modelo será error de la etiqueta. La matriz de confusión del paso 7 y el conjunto de prueba escrito por el equipo (SCRUM-100) permitirán separarlos.
4. **Las variantes aumentadas heredan la etiqueta** del ticket original, con sus errores.
5. **Los datos de impacto, urgencia y usuarios afectados no se auditaron:** no existen en ninguna fuente y se derivan de la prioridad con la matriz.

## Reproducir

```bash
python -m src.data.unificar          # aplica las reglas y escribe data/processed/tickets_base.csv
python -m src.data.aumentar          # (entorno CUDA) añade las variantes y escribe data/processed/tickets.csv
python -m src.data.auditoria medir   # recalcula el acierto sobre las tres muestras con sus veredictos
```
