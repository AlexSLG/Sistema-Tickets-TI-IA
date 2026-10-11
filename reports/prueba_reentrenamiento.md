# Prueba del reentrenamiento (punto 3)

Se probó `python -m src.training.reentrenar` con 6 correcciones de ejemplo (`reports/prueba_correcciones.csv`) sobre la versión vigente `v1`
(F1 macro de categoría en el conjunto de referencia, test con tickets reales: **0,8736**). Registro resultante: `reports/prueba_reentrenamiento_registry.json`.

| Intento | Configuración | F1 macro nueva | Resultado |
|---|---|---:|---|
| v2 | 3 épocas, lr 5e-4 | 0,8731 | **descartada** (empeora) |
| v3 | 2 épocas, lr 1e-4 | 0,8707 | **descartada** (empeora) |
| v4 | 1 época, lr 0 (el modelo no cambia: prueba del camino de publicación) | 0,8736 | **publicada** y activa (iguala) |

- La regla «solo se publica si iguala o supera» funciona en ambos sentidos y deja cada intento en `registry.json` con su estado.
- `registro.restaurar('v1')` vuelve a la versión anterior; restaurar una versión descartada o inexistente lanza un error.
- Con 6 correcciones sobre ≈ 6 500 tickets el efecto es mínimo y cae dentro del ruido (±0,003): es esperable que las primeras correcciones no logren superar a la vigente. Después de la prueba se restauró el registro con solo `v1` y se borró `models/v4`.
