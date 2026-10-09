# Aumento por retrotraducción (paso 4)

Retrotraducción con idioma intermedio inglés, alemán o italiano (MarianMT; ida con haz de 4, vuelta con muestreo top-p 0,92) de tickets **reales** de las categorías con menos de 600. Las variantes conservan las etiquetas del original, llevan `origen_etiqueta = aumento` y el mismo `grupo`. Se descartan las que cambian demasiado de longitud (fuera de 0,6–1,6×) o se parecen demasiado al original (Jaccard ≥ 0,88).

| Categoría | Reales | Candidatos | Variantes por ticket | Aumentados | Total |
|---|---:|---:|---:|---:|---:|
| Accesos | 354 | 354 | 2 | 246 | 600 |
| Correo | 140 | 140 | 4 | 299 | 439 |
