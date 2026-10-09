# Datos auxiliares: reglas de derivación (paso 6)

Ninguna fuente trae el plantel de técnicos, el historial de asignaciones ni las soluciones rápidas en el formato del sistema.
Se derivan con las reglas de este documento. Código: `src/data/auxiliares.py` y `src/data/soluciones_rapidas.py`. Resultados y cifras: `reports/datos_auxiliares_resumen.md`.

## 1. Plantel de técnicos (`data/processed/tecnicos.csv`)

8 técnicos con área, límite de carga y aptitud de 1 (mínima) a 5 (experto) en cada categoría.

- **Aptitudes:** definidas a mano por área (infraestructura y hardware, aplicaciones, redes y comunicaciones, redes y seguridad, accesos y correo, mesa de ayuda generalista). Restricción: **al menos 2 técnicos con aptitud ≥ 4 en cada categoría** (comprobada por el código y por `tests/test_datos.py`). Correo es la categoría con menos cobertura (2 técnicos: la especialista en accesos y correo y el generalista), lo que sirve para demostrar el balanceo cuando la especialista se satura.
- **Límite de carga** (tickets abiertos a la vez): proporcional a la distribución real de tickets por responsable de `issues.csv`. Se toman los 113 responsables con ≥ 50 tickets, se calculan 8 cuantiles de su carga, se normalizan a media 1 y se multiplican por 10 (acotado a 6–14). Se asignan en orden de mayor a menor al generalista, accesos y correo, aplicaciones, infraestructura… Resultado: límites de 6 a 14.
- Los nombres son de ejemplo; no corresponden a personas reales.

## 2. Historial de asignaciones (`data/processed/historial_asignaciones.csv`)

Una fila por ticket del conjunto (los 9 379 de train, val y test, identificados por `subconjunto`): quién lo atendió, con qué carga, cuánto tardó y si se reasignó. Incluye las cargas de **los 8 técnicos** en el instante de la asignación (`carga_T01…carga_T08`) para poder construir ejemplos negativos de cada par (ticket, técnico).

**Simulación en orden cronológico:**

1. **Llegadas:** orden aleatorio (semilla 42) de los tickets, con tiempos entre llegadas exponenciales en horas laborables (8 h/día, lunes a viernes, desde el 02/03/2026). La tasa se calcula para que la carga media del equipo sea ≈ 78 % de la suma de sus límites (5,5 tickets por hora laborable).
2. **Decisión de asignación:** para cada técnico se calcula `aptitud en la categoría − 1,6 × (carga / límite) + ruido N(0; 0,15)`. Se elige el de mayor puntaje **entre los que no superan su límite**. Si todos están al límite, el de menor ocupación (`saturado = 1`). Es la misma lógica que el modelo debe aprender (aptitud, carga) más las reglas de balanceo del plan.
3. **Reasignación:** con probabilidad igual a la tasa de reaperturas de `issues.csv` (3,4 %), ×1,8 si el técnico tiene aptitud ≤ 2 y ×1,5 si el ticket es Crítico, el ticket pasa al siguiente mejor puntaje disponible (`reasignado = 1`; `tecnico_inicial` conserva el primero y `tecnico` el que lo atendió).
4. **Tiempo de resolución** (horas laborables): lognormal con mediana `8 h × razón` y dispersión σ. La **razón** entre prioridades sale del tiempo total mediano de `issues.csv` frente a prioridad Medium (Baja 1,07; Media 1; Alta 0,54; Crítica 0,43: lo urgente se resuelve antes). σ sale de los cuartiles reales (≈ 1,9), **acotada a 0,9** para que el tiempo sea aprendible. Se multiplica por `1 + 0,25 × (3 − aptitud)/2` (menos aptitud, más lento) y `1 + 0,3 × ocupación` (más carga, más lento), y por 1,5 si hubo reasignación.
5. **Pasos del proceso:** `1 + Poisson(mediana real − 1 [+0,5 si Alta o Crítica])`, +1 si hubo reasignación (mediana real de `processing_steps`: 3).

**Para el paso 7:** la asignación esperada del modelo es `tecnico_inicial`. Con el ruido de la decisión, la regla determinista reproduce `tecnico_inicial` en el **90,5 %** de los casos: ese es el techo; el criterio ≥ 80 % se mide contra él.

## 3. Soluciones rápidas (`data/processed/soluciones_rapidas.json`)

50 entradas: Red 9, Hardware 9, Software 9, Accesos 9, Correo 7, Seguridad 7. Campos: `id`, `categoria`, `problema`, `frases_ejemplo` (3 a 5 formas de describir el problema) y `pasos` (3 a 6), más `semilla` con el origen de la idea.

- **Hardware, Red, Accesos y Software** parten de las notas de resolución (`resolution_notes`) de `tech-support` (reiniciar router y actualizar firmware, reinstalar controladores, restablecer credenciales, borrar la caché, reinstalar el cliente VPN, etc.).
- **Correo y Seguridad** no tienen semilla directa: las `answer` de la fuente principal son respuestas genéricas de plantilla, sin pasos concretos. Se redactaron con criterio de mesa de ayuda y **deben ser validadas por el equipo**.
- Las `frases_ejemplo` se indexan junto con los tickets resueltos para la similitud (paso 7); el umbral de similitud decide cuándo se muestra la solución rápida.

## 4. Limitaciones

- Todo el historial es una **simulación** coherente con las distribuciones de `issues.csv`, no registros de trabajo real: sirve para entrenar y demostrar el algoritmo de asignación, no para medir rendimiento de técnicos reales. Al integrarlo en el Sprint 2 se sustituirá por el historial real del sistema.
- La asignación se explica solo con aptitud y carga; la realidad tiene más factores (turnos, vacaciones, preferencias).
- Las cargas y tiempos se calibraron con la **forma** de las distribuciones de `issues.csv` (cocientes entre prioridades, reparto entre responsables, reaperturas), no con sus valores absolutos, que son de días o semanas por tratarse de proyectos de software.
