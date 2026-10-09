# Calidad de la traducción (paso 3)

Modelos: MarianMT `Helsinki-NLP/opus-mt-en-es`, `opus-mt-de-es` y `opus-mt-it-es` (preprocesamiento; no forman parte del sistema).
Ejecución en GPU (RTX 4060, fp16, lote 64). Código: `src/data/traduccion.py`. Muestra: `data/interim/muestra_calidad.csv`.

## Resumen de la ejecución

| Dato | Valor |
|---|---|
| Textos traducidos | 6 419 tickets de la fuente principal (título, cuerpo y solución), 1 800 de `Dataset_ticket.xlsx`, 162 de `tech-support` |
| Unidades (frases o grupos de ≤ 30 palabras) | 41 613 |
| Tiempo de traducción | ≈ 8 min por pasada completa (13 min la primera). CPU habría tardado ≈ 3,8 h (0,65 textos/s frente a 14,9 textos/s en GPU) |
| Marcadores `<name>`, `<tel_num>`, `<acc_num>`… | Se sustituyen por fichas y se restauran; se pierden 40 de ≈ 4 500 (< 1 %) |
| Unidades sin traducir | 2 (nombres de producto) más 8 títulos de una palabra o siglas |
| Posibles omisiones de frase | 16 unidades con salida < 55 % de la entrada (otras 14 se repararon frase por frase) |

## Problemas detectados en el proceso y cómo se corrigieron

1. **La columna `language` de la fuente principal no es fiable.** Unas 12 de 30 filas marcadas como alemán (`de`) están en inglés o mezcladas. El modelo alemán las dejaba sin traducir o las estropeaba (p. ej. "data sincronization"). *Solución:* el idioma se decide por unidad con palabras vacías (en/de/it); en empate se usa el de la fila.
2. **Textos largos con frases omitidas** (el modelo se saltaba la primera o la segunda frase). *Solución:* unidades de ≤ 30 palabras (una o dos frases) y reparación frase por frase de las salidas anormalmente cortas.
3. **Títulos en Title Case devueltos sin cambios** ("Data Security Concerns in Hospital Infrastructure"). *Solución:* reintento con el texto en minúsculas y, si no cambia, con el otro modelo. Quedan sin traducir los nombres de producto y siglas ("MacBook Pro", "UI-Issue").
4. **El modelo traducía la ficha `NAME_1` como `NOMBRE_1`.** *Solución:* alias en la restauración (pérdidas de marcadores: 460 → 40).
5. **Texto escapado en la fuente:** `\n` literales y `<br>` se normalizan a saltos de línea antes de traducir.

## Revisión de la muestra aleatoria (100 traducciones, semilla 42)

Composición: 60 de la fuente principal (30 en, 30 de), 30 de `Dataset_ticket.xlsx` (15 en, 15 it) y 10 de `tech-support`.
Se leyó el inicio de cada texto (primeros ≈ 130 caracteres de las traducciones largas); los defectos que solo aparezcan más adelante en un texto largo no están contados.

**Valoración:** unas 80 de 100 son correctas o tienen diferencias menores de estilo. Unas 20 presentan algún defecto, casi todos de estilo o gramática; ninguno invalida la clasificación del ticket. Calidad por fuente: `Dataset_ticket.xlsx` y `tech-support` (frases cortas y simples) salen mejor que la fuente principal (textos largos, más ruido en el original).

### Errores frecuentes

| Error | Ejemplo | Frecuencia | Tratamiento |
|---|---|---|---|
| "Dear Customer Support" → "Estimado cliente de atención/soporte" | #1, #8, #18, #27 | 168 apariciones en toda la fuente principal | Normalizar el saludo a "Estimado equipo de soporte" en el paso 4 (o eliminar el saludo del título/descripción) |
| "I am reaching out" → "Me estoy acercando para…" | #19 | 77 | Sustituir por "Me pongo en contacto para…" |
| "crashed" → "se ha estrellado / se desploma" | #12, #31 | ≈ 80 | Sustituir por "ha fallado / se ha caído" |
| "downtime" → "tiempo de inactividad" | #1 | 180 | Aceptable, se deja |
| Plural con tilde: "desconexiónes" | #14 | 14 | Corregir por expresión regular (`ónes` → `ones`) |
| Tono imperativo del inglés pasado a tercera persona: "Necesita ayuda…", "Requerir asistencia…" | #70, #98 | pocos, en `tech-support` y xlsx | Se deja (no afecta a la clasificación) |
| Giros poco naturales: "falta columnas", "Ajustes que no guardan", "línea de tiempo de liberación de productos", "oficina WiFi", "soportes o soportes" | #93, #99, #95, #97, #79 | casos aislados | Se dejan |
| Términos mal traducidos: "smart plug" → "caja de control inteligente" (visto en una pasada anterior) | — | aislado | Se deja |
| Palabras sueltas en inglés dentro de textos alemanes ("throughout", "Projektor", "Audiodruckbearbeitung") | #53, #29, #32 | 8 en toda la fuente principal | Se dejan |
| Fichas sin restaurar (`XXX_1`) | — | 4 | Se eliminan en el paso 4 |
| Originales de mala calidad (alemán incorrecto o incoherente) | #48, #50 | aislado | Traducción también incoherente; se podrían descartar en la depuración |

### Términos técnicos

VPN, Outlook, Wi-Fi, WiFi, DNS, DHCP, SQL Server, DB2, Oracle y similares se conservan (las traducciones de la muestra los mantienen). La verificación automática señala "ausencias" de *Teams* (100), *Wireless* (50) y *Office* (32), pero casi todas son usos genéricos legítimos ("equipos", "inalámbrico", "oficina"), no pérdidas del nombre de producto.

## Conclusión

La traducción es suficientemente fiel para entrenar los modelos de clasificación, prioridad y asignación: conserva el vocabulario técnico (VPN, Wi-Fi, DNS, Outlook, etc.) y el sentido de la incidencia. Los defectos recurrentes son de estilo y se reducen con una normalización posterior en el paso 4.
