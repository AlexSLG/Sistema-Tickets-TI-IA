# Reglas de etiquetado (paso 4)

Implementación: `src/data/mapeo.py` (reglas), `src/data/unificar.py` (unificación y depuración) y `src/data/aumentar.py` (aumento).
Este documento recoge las **reglas finales**, con las correcciones derivadas de la auditoría manual (`reports/auditoria_etiquetas.md`, apartado 8).
Todas las reglas se aplican sobre el texto **en español**, en minúsculas y sin acentos. Semilla fija: 42.
Los datos auxiliares (prioridad derivada, impacto, urgencia, usuarios afectados) no vienen de ninguna fuente y se derivan con las reglas de este documento.

## 1. Categoría

### 1.1 Por fuente

| Fuente | Regla | `origen_categoria` |
|---|---|---|
| `Dataset_ticket.xlsx` | Subcategoría → categoría: CPU, Disk, Keyboard, Memory, Monitor, Mouse → **Hardware**; DHCP, DNS, IP Address, VPN, Wireless → **Red**; Email → **Correo**; Antivirus → **Seguridad**; Operating System, DB2, MS SQL Server, Oracle → **Software** | fuente |
| `Dataset_ticket.xlsx` · Internal Application | Son peticiones de permisos y autorizaciones (revisadas: "¿Puedo tener permiso para…?") → **Accesos**; si el texto apunta con claridad a Seguridad, Correo o Red se usa esa categoría | fuente / regla |
| `tech-support` | software → Software, hardware → Hardware, network → Red. `billing` se descarta (38 filas). Las 18 filas `other` se revisaron a mano: permisos, acceso de un nuevo miembro y supresión de cuenta → **Accesos**; acceso remoto → **Red**; las 13 consultas comerciales (garantía, SLA, demo, RGPD, documentación de producto, comentarios…) se descartan | fuente |
| Fuente principal y v1 | Reglas por palabras clave (1.2) | regla |

### 1.2 Reglas por palabras clave (fuente principal y v1)

Se suman pesos por coincidencia de patrón; la categoría con más puntos gana. **El título cuenta el doble que la descripción.**
Las etiquetas `tag_1..tag_8` de la fuente principal suman un voto pequeño (p. ej. `Security` +1, `Data Breach` +2, `Login` +2, `Network` +1,5, `Hardware` +1,5, `Software` +1).
Empates: Seguridad > Accesos > Correo > Red > Hardware > Software. Sin ninguna señal: Software ("resto de fallos de aplicación").

| Categoría | Señales fuertes (peso 2–4) | Señales débiles (peso 0,75–1,5) |
|---|---|---|
| **Seguridad** | phishing, malware, ransomware, virus, antivirus, brecha, vulnerabilidad, ciberataque, intrusión, acceso no autorizado, fuga de datos, cortafuegos, cifrado, amenaza, protección/seguridad de los datos | "seguridad", "medidas de seguridad", "ataque" |
| **Accesos** | contraseña, restablecer clave, inicio de sesión, credenciales, autenticación, 2FA/MFA/SSO, cuenta bloqueada, permiso, autorización, privilegios, "dar/obtener acceso", acceso denegado, "no puedo acceder", cuenta de usuario, alta de usuario | "acceso" |
| **Correo** | Outlook, buzón, bandeja de entrada, SMTP/IMAP, spam, Gmail, cliente/servidor/cuenta de correo, "enviar/recibir correos", casilla, carpeta de enviados, adjuntos | "correo (electrónico)", "email" |
| **Red** | VPN, Wi-Fi, DNS, DHCP, dirección IP, ancho de banda, latencia, Ethernet, LAN/WAN, proxy, router, módem, conectividad, internet, red | "conexión", "conectar" |
| **Hardware** | impresora, portátil, disco duro, SSD, monitor, teclado, ratón, RAM, CPU, procesador, ventilador, batería, tarjeta gráfica, sobrecalentamiento, proyector, USB, pantalla, ordenador, PC | "memoria", "dispositivo", "equipo", "no enciende" |
| **Software** | aplicación, software, programa, actualización, parche, bug, sistema operativo, Windows/Linux, instalación, licencia, base de datos, SQL, API, integración, plataforma, SaaS, guardar/exportar, CRM | "error", "fallo", "lento", "rendimiento", "configuración", "compatibilidad" |

**Mención incidental del correo.** En la fuente principal muchos tickets piden "enviar la información en un correo detallado". Esas frases ("por/en un correo…", "envíe… correo") se eliminan antes de puntuar, para que no cuenten como categoría Correo.

### 1.3 Validación

Se compararon las reglas por palabras clave con las categorías de referencia de las fuentes que sí las traen:

| Referencia | Filas | Coincidencia |
|---|---:|---:|
| `Dataset_ticket.xlsx` (sin Internal Application) | 1 700 | 88,1 % |
| `tech-support` | 144 | 73,6 % |

Parte del desacuerdo no es error de las reglas sino de la referencia: p. ej. un ticket de subcategoría "Operating System" que habla de un segundo monitor, o un ticket `network` de `tech-support` que dice "no se puede acceder a la unidad compartida" (las reglas dicen Accesos). Estas dos fuentes usan siempre su etiqueta de origen; las reglas solo etiquetan la fuente principal y la v1, donde no hay referencia, así que su exactitud se midió con la auditoría manual (apartado 8): ≈ 85 % en categoría y ≈ 93 % en prioridad sobre una muestra sin ajustar (n = 60), con un 79 % / 80 % antes de corregir las reglas.

## 2. Relevancia de TI y depuración

| Paso | Regla |
|---|---|
| Fuera de TI | Se descarta un ticket de la fuente principal o de la v1 si su texto trata un tema puramente comercial (campañas y métricas de marketing, redes sociales, SEO, tráfico del sitio, facturación, reembolsos, precios, garantía, SLA, cuenta demo, documentación de producto, estrategias de inversión) **y** no menciona nada técnico (servidor, plataforma, sistema, software, aplicación, herramienta, base de datos, API, integración, error, fallo, caída, VPN, red, acceso, contraseña, correo, dispositivo, conexión, actualización, configuración, sincronización, lentitud…). Un relato comercial con un problema técnico ("la plataforma de campañas se cayó") se conserva. Descartadas: 262 (incluye la regla dura de la auditoría: facturación, precios, publicidad, suscripciones, métricas de campañas, etc., que se descarta aunque aparezca una palabra técnica) |
| Muy corto | Descripción con menos de 3 palabras: 0 |
| Duplicados exactos | Mismo título + descripción normalizados: 35 |
| Casi duplicados | Coseno TF-IDF (palabras, 1–2-gramas) ≥ 0,88; se conserva la fuente de mayor rango (`tech-support` > principal > xlsx > v1): 49, todos dentro de la misma fuente |
| v1 contra la principal | Sin solapamiento: la similitud máxima de los 812 tickets de la v1 contra los 6 419 traducidos es 0,21 (TF-IDF de palabras); no son los mismos tickets. Las etiquetas de la v1 se descartaron y se recalcularon con las reglas nuevas |
| Sin etiqueta | Ningún ticket quedó sin categoría: lo que no tiene señal específica pasa a Software (unas decenas en la fuente principal) |

Normalizaciones de estilo aplicadas a la traducción (detectadas en `reports/calidad_traduccion.md`): "Estimado cliente de atención/soporte" → "Estimado equipo de soporte"; "me estoy acercando para" → "me pongo en contacto para"; plurales con tilde (`desconexiónes` → `desconexiones`); "se ha estrellado/se desploma" → "ha fallado/se cae"; eliminación de fichas de marcador sin restaurar.

## 3. Prioridad

| Origen | Regla | `origen_prioridad` |
|---|---|---|
| `low`, `medium`, `high` | → Baja, Media, Alta | fuente |
| `urgent` (`tech-support`) | → **Crítica** | fuente |
| `high` en fuente principal y v1 | → **Crítica** si el texto indica caída total, servicio de producción, sistema crítico, "toda la empresa", "todos los usuarios", pérdida de datos, ransomware, brecha de datos…; o si, además, lleva una etiqueta `Outage` / `Data Breach` y habla de interrupción, caída, colapso, indisponibilidad o varios sistemas afectados | regla |
| `Dataset_ticket.xlsx` (sin prioridad) | Impacto y urgencia que indica el texto (puntajes de 3.2), pasados por la matriz de 3.1 | regla |

Referencia: en `issues.csv` Highest + Blocker son ≈ 8,4 % de las prioridades conocidas. Resultado: **Crítica = 7,6 %** del conjunto final (7,9 % de los tickets reales).

## 4. Impacto, urgencia y usuarios afectados

### 4.1 Matriz impacto × urgencia → prioridad

Se suman niveles (Bajo/Baja = 1, Medio/Media = 2, Alto/Alta = 3): suma 2–3 → **Baja**; 4 → **Media**; 5 → **Alta**; 6 (Alto + Alta) → **Crítica**.

### 4.2 Cómo se asignan

1. Puntaje de **impacto** del texto: sube con "toda la empresa/oficina", "todos los usuarios", "miles de", "varios productos/sistemas", "caída total", "entorno de producción", "red corporativa", "brecha", "ransomware", "pérdida de datos" (Alto), y con "equipo", "departamento", "usuarios", "servidor", "plataforma" (Medio); baja con "mi portátil/cuenta/correo…", "yo", "no puedo" (Bajo).
2. Puntaje de **urgencia**: sube con "urgente", "inmediato", "cuanto antes", "no puedo trabajar", "bloqueado", "caído", "fuera de servicio", "sin servicio", "no responde"; baja con "consulta", "información", "orientación", "documentación", "mejores prácticas", "guía", "cuando sea posible".
3. Entre las combinaciones (impacto, urgencia) cuya matriz da la **prioridad ya asignada**, se elige la más cercana a los puntajes del texto. Así impacto y urgencia siempre son coherentes con la prioridad y a la vez reflejan el relato.
4. **Excepciones:** con probabilidad 7 % se elige una combinación cuya matriz da la prioridad contigua (una más o una menos), para que el MLP no aprenda solo la matriz. Resultado: 6,7 % de las filas (`excepcion_matriz = True`).
5. **Usuarios afectados:** Bajo → 1–3; Medio → 5–30 (5–20 si el texto habla de departamento o equipo); Alto → 50–500 (200–1000 si habla de toda la empresa o miles). Se elige entre esos valores con la semilla fija.

## 5. Origen de la etiqueta

`origen_etiqueta`: `fuente` si categoría y prioridad vienen directamente del mapeo de la fuente (145 filas de `tech-support`), `regla` si alguna se derivó con reglas (8 689) y `aumento` para las variantes por retrotraducción (545). Además, `origen_categoria` y `origen_prioridad` dan el detalle por campo.

## 6. Balance y aumento

Objetivo: ≥ 600 tickets por categoría. Antes del aumento: Software 4 274, Red 1 437, Seguridad 1 481, Hardware 1 148, Accesos 354, Correo 140.
Se aumentan solo Accesos y Correo, por retrotraducción de tickets reales con idioma intermedio inglés, alemán o italiano (ver `reports/aumento_resumen.md`).

| Categoría | Reales | Aumentados | Total |
|---|---:|---:|---:|
| Accesos | 354 | 246 | **600** |
| Correo | 140 | 299 | **439** |

**Correo no llega a 600 (439):** la fuente tiene pocos tickets de correo y las variantes de textos tan cortos se parecen demasiado al original. Dos de cada tres tickets de Correo son variantes (32 % reales; de los 140 reales, 100 son frases cortas de `Dataset_ticket.xlsx`, 22 de la v1 y solo 18 de la fuente principal), y el 41 % de Accesos (59 % real).
Para no contaminar la evaluación, cada variante conserva el `grupo` de su ticket original y **la división train/val/test del paso 5 debe mantener cada grupo completo en un solo subconjunto**; las métricas de Correo y Accesos deben leerse con esta salvedad, y conviene que el conjunto de prueba escrito a mano (SCRUM-100) incluya tickets reales de estas dos clases.

## 7. Limitaciones conocidas

- Las etiquetas de categoría de la fuente principal y la v1 son de **reglas**, no de personas: el tope de F1 de los modelos está limitado por ellas. La clase Seguridad (1 459, casi toda de la fuente principal) mezcla incidentes reales con peticiones de buenas prácticas.
- Prioridad de `Dataset_ticket.xlsx`: derivada del texto, tiende a Baja (79 % de sus tickets); es la fuente de menor calidad para esa etiqueta.
- Impacto, urgencia y usuarios afectados no existen en ninguna fuente; son una aproximación coherente con la matriz y con el relato, no una medida.
- Los textos de la fuente principal siguen un estilo de plantilla (relatos de hospital, agencia de marketing, firma financiera) que no se parece al de usuarios reales.

## 8. Ajustes tras la auditoría de etiquetas

La revisión manual de 200 tickets (acierto inicial 79 % en categoría y 80 % en prioridad) mostró errores sistemáticos, corregidos así (detalle en `reports/auditoria_etiquetas.md`):

- **Seguridad:** nuevos patrones para "no autorizado", "sospechoso", "comprometido", "violado" y marcas de antivirus (Kaspersky, Bitdefender, Norton, McAfee, Avast, ESET).
- **Software:** interrupciones del servicio, tiempo de inactividad, sobrecarga del servidor, sincronización, mejoras de interfaz y herramientas de campañas por correo (Mailchimp, SendGrid) pasan a Software.
- **Correo:** Outlook baja de peso (3,5 → 2,5) porque aparece en listas de productos afectados.
- **Hardware:** "equipo" deja de ser señal (casi siempre es el equipo de trabajo); en empate, Software va antes que Hardware.
- **Fuera de TI, regla dura:** facturación y reembolsos, precios, publicidad, suscripciones, seguros, información de producto, previsiones de inversión, métricas de compromiso de campañas. Se aplica a todas las fuentes, incluido `Dataset_ticket.xlsx`.
- **Prioridad** (`ajustar_prioridad`, no sobre `tech-support`): un incidente de seguridad (acceso no autorizado, violación, brecha, malware) sube a **Alta** como mínimo; una consulta o petición de información sin incidencia con prioridad Alta o Crítica baja a **Baja**; "urgente" o una interrupción que afecta a varios sistemas con prioridad Baja sube a **Media**; la pérdida de datos sube a **Alta** como mínimo. Estas filas pasan a `origen_prioridad = regla`.

Con las reglas finales, sobre una muestra nueva de 60 tickets que no se usó para ajustar: **85 % de acierto en categoría y 93 % en prioridad**.
