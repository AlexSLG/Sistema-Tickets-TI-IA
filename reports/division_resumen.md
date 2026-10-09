# División del conjunto (paso 5)

División **70/15/15 por grupo**, estratificada por categoría y prioridad, semilla 42 (`src/data/dividir.py`).
Un `grupo` reúne un ticket real y sus variantes aumentadas; cada grupo está completo en un solo subconjunto.

## Tamaño

| Subconjunto | Tickets | % | Reales | Aumentados | Grupos |
|---|---:|---:|---:|---:|---:|
| train | 6545 | 69.8% | 6174 | 371 | 6174 |
| val | 1417 | 15.1% | 1329 | 88 | 1329 |
| test | 1417 | 15.1% | 1331 | 86 | 1331 |

## Categoría

| categoria   |   train |   val |   test |
|:------------|--------:|------:|-------:|
| Software    |    2989 |   642 |    643 |
| Seguridad   |    1034 |   224 |    223 |
| Red         |    1005 |   216 |    216 |
| Hardware    |     800 |   174 |    174 |
| Accesos     |     418 |    91 |     91 |
| Correo      |     299 |    70 |     70 |

Porcentaje de cada categoría dentro de cada subconjunto:

| categoria   |   train |   val |   test |
|:------------|--------:|------:|-------:|
| Software    |    45.7 |  45.3 |   45.4 |
| Seguridad   |    15.8 |  15.8 |   15.7 |
| Red         |    15.4 |  15.2 |   15.2 |
| Hardware    |    12.2 |  12.3 |   12.3 |
| Accesos     |     6.4 |   6.4 |    6.4 |
| Correo      |     4.6 |   4.9 |    4.9 |

## Prioridad

| prioridad   |   train |   val |   test |
|:------------|--------:|------:|-------:|
| Baja        |    2140 |   461 |    461 |
| Media       |    2128 |   459 |    459 |
| Alta        |    1785 |   386 |    386 |
| Crítica     |     492 |   111 |    111 |

| prioridad   |   train |   val |   test |
|:------------|--------:|------:|-------:|
| Baja        |    32.7 |  32.5 |   32.5 |
| Media       |    32.5 |  32.4 |   32.4 |
| Alta        |    27.3 |  27.2 |   27.2 |
| Crítica     |     7.5 |   7.8 |    7.8 |

## Comprobaciones

- Grupos compartidos entre subconjuntos: {'train∩val': 0, 'train∩test': 0, 'val∩test': 0} (deben ser 0).
- Ningún `id` está repetido y la unión de los tres subconjuntos es el conjunto completo.
- Tickets reales de val/test con un vecino en train de similitud TF-IDF ≥ 0,8: val 2.2%, test 2.9% (≥ 0,9: val 0.2%, test 0.5%). Es parecido por plantilla, no repetición: los casi duplicados exactos ya se eliminaron en el paso 4 (umbral 0,88 dentro de la misma fuente).

## Cómo evaluar

Val y test contienen también variantes aumentadas (de los grupos que les tocaron). Para las métricas finales usa solo las filas con `origen_etiqueta != "aumento"`; `src/training/evaluar.py` hará ese filtrado y reportará además el resultado con todas las filas.
