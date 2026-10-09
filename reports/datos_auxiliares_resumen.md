# Datos auxiliares: resumen (paso 6)

Plantel, historial y soluciones rápidas se derivan con las reglas de `reports/datos_auxiliares.md`.

## Calibración con `issues.csv`

- 58339 tickets de tipos Ticket/Service/HD Service/Task/Story; 365 responsables, 113 con ≥ 50 tickets.
- Mediana de tiempo total de los de prioridad Medium: 219 h.
- Razón del tiempo mediano frente a Medium: Baja 1.07, Media 1.00, Alta 0.54, Crítica 0.43; dispersión (σ del log, acotada a 0,9): Baja 0.90, Media 0.90, Alta 0.90, Crítica 0.90.
- Tasa de reaperturas: 3.4%. Pasos del proceso: mediana 3, p90 6.

## Técnicos

| id_tecnico   | nombre          | area                        |   limite_carga |   aptitud_hardware |   aptitud_software |   aptitud_red |   aptitud_accesos |   aptitud_correo |   aptitud_seguridad |
|:-------------|:----------------|:----------------------------|---------------:|-------------------:|-------------------:|--------------:|------------------:|-----------------:|--------------------:|
| T01          | Carolina Méndez | Infraestructura y hardware  |              6 |                  5 |                  3 |             3 |                 2 |                2 |                   2 |
| T02          | Diego Rojas     | Infraestructura y hardware  |              8 |                  4 |                  3 |             4 |                 2 |                2 |                   2 |
| T03          | Valeria Ortiz   | Aplicaciones                |              6 |                  2 |                  5 |             2 |                 3 |                3 |                   2 |
| T04          | Andrés Salazar  | Aplicaciones                |             12 |                  3 |                  4 |             2 |                 4 |                3 |                   3 |
| T05          | Marcela Vega    | Redes y comunicaciones      |              6 |                  3 |                  2 |             5 |                 2 |                2 |                   4 |
| T06          | Julián Paredes  | Redes y seguridad           |              6 |                  2 |                  3 |             4 |                 3 |                2 |                   5 |
| T07          | Lucía Herrera   | Accesos y correo            |             14 |                  2 |                  3 |             2 |                 5 |                5 |                   3 |
| T08          | Mateo Quispe    | Mesa de ayuda (generalista) |             14 |                  4 |                  4 |             3 |                 4 |                4 |                   2 |

## Historial

- 9379 asignaciones (todos los tickets: train, val y test), de 2026-03-02 09:11 a 2027-01-20 11:11; 5.48 tickets por hora laborable.
- Carga media al asignar: 0.74 del límite; asignaciones con el técnico saturado: 5.1%; reasignaciones: 3.3%.
- Aptitud del técnico asignado: 2: 2.8%, 3: 12.7%, 4: 44.1%, 5: 40.4%.
- Tiempo de resolución (h laborables): mediana 6.9, p90 24.3.

Tickets por técnico y categoría:

| tecnico   |   Accesos |   Correo |   Hardware |   Red |   Seguridad |   Software |   All |
|:----------|----------:|---------:|-----------:|------:|------------:|-----------:|------:|
| T01       |         4 |        8 |        647 |    46 |          23 |        113 |   841 |
| T02       |         8 |        5 |        228 |   485 |          22 |        149 |   897 |
| T03       |         6 |        4 |         18 |     8 |          16 |        981 |  1033 |
| T04       |        33 |       10 |         31 |    17 |         119 |       1332 |  1542 |
| T05       |         6 |        6 |         17 |   594 |         267 |         31 |   921 |
| T06       |         6 |        5 |          7 |   174 |         690 |         79 |   961 |
| T07       |       510 |      364 |         20 |    40 |         323 |        215 |  1472 |
| T08       |        27 |       37 |        180 |    73 |          21 |       1374 |  1712 |
| All       |       600 |      439 |       1148 |  1437 |        1481 |       4274 |  9379 |

Tiempo medio de resolución por prioridad (h):

| prioridad   |   mean |   median |
|:------------|-------:|---------:|
| Baja        |   13.5 |      9   |
| Media       |   12.9 |      8.2 |
| Alta        |    7   |      4.5 |
| Crítica     |    5.7 |      3.8 |

**Techo de la regla:** la asignación inicial coincide con el mejor puntaje determinista (aptitud y ocupación entre los técnicos libres) en el 90.5% de los casos; el resto es el ruido de la decisión, que ningún modelo puede recuperar. El criterio del paso 7 (≥ 80 % de técnico esperado en primer lugar) debe medirse contra la **asignación inicial** (`tecnico_inicial`).
