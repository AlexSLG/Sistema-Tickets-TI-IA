# Resumen del filtrado (paso 3a)

## Fuente principal (multi-lang)

| Paso | Filas |
|---|---:|
| Filas originales | 28 587 |
| Colas de TI (+ Customer Service con etiqueta específica) | 19 655 |
| Sin etiquetas comerciales (billing  payment  sales  marketing…) | 17 816 |
| Cuerpo con ≥ 5 palabras | 17 666 |
| Sin cuerpos duplicados | 17 666 |
| Muestra por cuotas (≤ 1600 por categoría) | 6 419 |

Categoría aproximada antes del muestreo: {'Software': 8096, 'Seguridad': 5412, 'Red': 2539, 'Hardware': 978, 'Accesos': 459, 'Correo': 182}

Categoría aproximada de la muestra: {'Software': 1600, 'Red': 1600, 'Seguridad': 1600, 'Hardware': 978, 'Accesos': 459, 'Correo': 182}

Idiomas de la muestra: {'en': 3255, 'de': 3164}

## Dataset_ticket.xlsx

1800 filas conservadas. Idiomas detectados: {'en': 912, 'it': 888}

## tech-support

200 → 162 filas (se descartó `billing`; sin mínimo de palabras).
