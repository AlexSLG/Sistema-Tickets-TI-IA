# Resumen de la unificación (paso 4)

## Filas por etapa

- Entrada por fuente: {'multilang': 6419, 'dataset_ticket': 1800, 'v1': 812, 'tech_support': 149}
- Descartadas por no ser de TI (sin ninguna señal técnica y con vocabulario comercial): 72
- Depuración:
  - descripcion con menos de 3 palabras: 0
  - duplicados exactos: 35
  - casi duplicados (coseno ≥ 0.88): 49
  -   de ellos, entre fuentes distintas: 0
  -   de ellos, dentro de la misma fuente: 49
- **Tickets resultantes (antes del aumento): 9024**

## Distribución

### Categoría × fuente

| categoria   |   dataset_ticket |   multilang |   tech_support |   v1 |   All |
|:------------|-----------------:|------------:|---------------:|-----:|------:|
| Accesos     |               92 |         264 |              4 |   24 |   384 |
| Correo      |              100 |          43 |              0 |   27 |   170 |
| Hardware    |              592 |         519 |             46 |  297 |  1454 |
| Red         |              486 |         898 |             43 |  147 |  1574 |
| Seguridad   |              104 |        1337 |              0 |   18 |  1459 |
| Software    |              375 |        3292 |             52 |  264 |  3983 |
| All         |             1749 |        6353 |            145 |  777 |  9024 |

### Prioridad

| prioridad   | porcentaje   |
|:------------|:-------------|
| Baja        | 28.2 %       |
| Media       | 34.4 %       |
| Alta        | 29.5 %       |
| Crítica     | 7.9 %        |

### Prioridad × fuente

| prioridad   |   dataset_ticket |   multilang |   tech_support |   v1 |   All |
|:------------|-----------------:|------------:|---------------:|-----:|------:|
| Alta        |               27 |        2350 |             54 |  232 |  2663 |
| Baja        |             1390 |         981 |             22 |  153 |  2546 |
| Crítica     |                0 |         599 |             19 |   95 |   713 |
| Media       |              332 |        2423 |             50 |  297 |  3102 |
| All         |             1749 |        6353 |            145 |  777 |  9024 |

### Impacto × urgencia (cuenta)

| impacto   |   Alta |   Baja |   Media |
|:----------|-------:|-------:|--------:|
| Alto      |    753 |    818 |    1879 |
| Bajo      |    121 |    130 |    1524 |
| Medio     |    757 |    812 |    2230 |

Excepciones a la matriz impacto × urgencia: 6.6%

### Origen de la etiqueta

| origen_etiqueta   |   filas |
|:------------------|--------:|
| regla             |    8879 |
| fuente            |     145 |
