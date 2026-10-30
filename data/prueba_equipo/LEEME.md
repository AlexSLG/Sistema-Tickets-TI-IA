# Conjunto de prueba del equipo (SCRUM-100 · HU35)

Tickets **redactados a mano por el equipo** para validar los modelos con textos que no vieron al entrenar. Es la prueba más honesta del sistema: los datos de entrenamiento siguen el estilo de sus fuentes; estos tickets, el de un usuario real.

## Qué hay que entregar

Un archivo **`tickets_equipo.csv`** en esta carpeta, con las mismas columnas que `plantilla.csv`:

| Columna | Qué poner |
|---|---|
| `id` | Identificador único corto, p. ej. `EQ-001`, `EQ-002`… |
| `titulo` | Título como lo escribiría quien reporta (3–200 caracteres) |
| `descripcion` | El problema con tus propias palabras (al menos una frase) |
| `impacto` | `Bajo`, `Medio` o `Alto` |
| `urgencia` | `Baja`, `Media` o `Alta` |
| `usuarios_afectados` | Número entero ≥ 1 |
| `categoria` | `Hardware`, `Software`, `Red`, `Accesos`, `Correo` o `Seguridad` (según tu criterio) |
| `prioridad` | `Baja`, `Media`, `Alta` o `Crítica` |
| `autor` | Quién lo escribió (Alex, Jeferson, Jesús, César) |

## Reglas

1. **Mínimo 60 tickets, 10 por categoría** (ideal: 120, 20 por categoría).
2. **Al menos 10 de prioridad Crítica**.
3. Redáctalos **como los escribiría un usuario real**, con tus propias palabras: con faltas de ortografía si te salen, sin copiar textos de los datos de entrenamiento ni de internet, y variando el estilo (cortos, largos, con contexto, sin contexto).
4. La **categoría** y la **prioridad** las decide quien escribe el ticket. La prioridad sigue la matriz impacto × urgencia de `reports/reglas_etiquetado.md` (apartado 4.1): se suman los niveles (Bajo/Baja = 1, Medio/Media = 2, Alto/Alta = 3); suma 2–3 → Baja, 4 → Media, 5 → Alta, 6 → Crítica. Si en algún caso crees que la prioridad debe ser otra, ponla: el validador solo lo informa.
5. Repartid las categorías entre los cuatro para que haya estilos distintos en cada una.
6. Guardad el archivo en **UTF-8** (en Excel: *Guardar como → CSV UTF-8*).

## Ejemplos (formato; no los copiéis al archivo final)

```csv
id,titulo,descripcion,impacto,urgencia,usuarios_afectados,categoria,prioridad,autor
EQ-001,no me agarra el wifi,desde ayer en la tarde mi laptop no se conecta al wifi de la oficina pero el celular si,Bajo,Media,1,Red,Baja,Alex
EQ-002,Se cayó el sistema de facturación,"Nadie en contabilidad puede entrar al sistema de facturación, sale error 500 desde las 9 am y hoy es cierre de mes",Alto,Alta,15,Software,Crítica,Jeferson
EQ-003,me llegó un correo raro del banco,me pide que actualice mi clave dando clic en un link y el remitente no es del banco. lo abrí pero no puse nada,Medio,Alta,1,Seguridad,Alta,César
```

## Qué pasa después

```bash
python -m src.data.validar_prueba_equipo        # revisa columnas, valores, vacíos, duplicados y solapamiento con los datos de entrenamiento
python -m src.training.evaluar_prueba_equipo    # evalúa la versión activa de los modelos
python -m src.training.ciclo_aprendizaje        # ciclo de aprendizaje continuo con la mitad A y evaluación en la mitad B
```

- La validación genera `reports/prueba_equipo_validacion.md` y deja los tickets válidos en `tickets_equipo_validos.csv`. Los tickets que se parecen demasiado (similitud TF-IDF ≥ 0,88) a alguno de entrenamiento, validación o prueba se **excluyen** y se informan.
- La evaluación genera `reports/evaluacion_prueba_equipo.md` y `reports/metricas_prueba_equipo.json`.
- El ciclo de aprendizaje genera `reports/aprendizaje_continuo_final.md`.
