# Resumen de la unificación (paso 4)

## Filas por etapa

- Entrada por fuente: {'multilang': 6419, 'dataset_ticket': 1800, 'v1': 812, 'tech_support': 149}
- Descartadas por no ser de TI (sin ninguna señal técnica y con vocabulario comercial): 262
- Depuración:
  - descripcion con menos de 3 palabras: 0
  - duplicados exactos: 35
  - casi duplicados (coseno ≥ 0.88): 49
  -   de ellos, entre fuentes distintas: 0
  -   de ellos, dentro de la misma fuente: 49
- **Tickets resultantes (antes del aumento): 8834**

## Distribución

### Categoría × fuente

| categoria   |   dataset_ticket |   multilang |   tech_support |   v1 |   All |
|:------------|-----------------:|------------:|---------------:|-----:|------:|
| Accesos     |               92 |         235 |              4 |   23 |   354 |
| Correo      |              100 |          18 |              0 |   22 |   140 |
| Hardware    |              592 |         354 |             46 |  156 |  1148 |
| Red         |              484 |         778 |             43 |  132 |  1437 |
| Seguridad   |              102 |        1358 |              0 |   21 |  1481 |
| Software    |              375 |        3492 |             52 |  355 |  4274 |
| All         |             1745 |        6235 |            145 |  709 |  8834 |

### Prioridad

| prioridad   | porcentaje   |
|:------------|:-------------|
| Baja        | 32.1 %       |
| Media       | 31.9 %       |
| Alta        | 28.1 %       |
| Crítica     | 7.9 %        |

### Prioridad × fuente

| prioridad   |   dataset_ticket |   multilang |   tech_support |   v1 |   All |
|:------------|-----------------:|------------:|---------------:|-----:|------:|
| Alta        |               34 |        2197 |             54 |  194 |  2479 |
| Baja        |             1380 |        1297 |             22 |  141 |  2840 |
| Crítica     |                0 |         585 |             19 |   94 |   698 |
| Media       |              331 |        2156 |             50 |  280 |  2817 |
| All         |             1745 |        6235 |            145 |  709 |  8834 |

### Impacto × urgencia (cuenta)

| impacto   |   Alta |   Baja |   Media |
|:----------|-------:|-------:|--------:|
| Alto      |    717 |    713 |    1734 |
| Bajo      |    108 |    174 |    1493 |
| Medio     |    736 |   1085 |    2074 |

Excepciones a la matriz impacto × urgencia: 7.0%

### Origen de la etiqueta

| origen_etiqueta   |   filas |
|:------------------|--------:|
| regla             |    8689 |
| fuente            |     145 |
