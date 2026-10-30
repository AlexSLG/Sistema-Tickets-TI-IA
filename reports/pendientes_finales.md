# Pendientes finales y trabajo futuro

Reemplaza a la lista de pendientes del Sprint 2. Lo resuelto en el Sprint 3 está en `reports/resultados_pruebas.md` y `reports/aceptacion_final.md`.

## 1. Pendiente para completar la entrega (requiere al equipo)

**HU35 y parte de HU37: validación con el conjunto de prueba escrito por el equipo (SCRUM-100).** Todo el código está listo y probado; falta el archivo.

1. Cada integrante redacta tickets siguiendo `data/prueba_equipo/LEEME.md` (≥ 60 en total, ≥ 10 por categoría, ≥ 10 de prioridad Crítica, texto propio, no copiado de los datos del proyecto) y los guarda en `data/prueba_equipo/tickets_equipo.csv` con las columnas de `plantilla.csv`.
2. Ejecutar:

```bash
.venv\Scripts\python -m src.data.validar_prueba_equipo        # reports/prueba_equipo_validacion.md (excluye solapamientos)
.venv\Scripts\python -m src.training.evaluar_prueba_equipo    # reports/evaluacion_prueba_equipo.md, metricas_prueba_equipo.json, figuras/cm_prueba_equipo.png
.venv\Scripts\python -m src.training.ciclo_aprendizaje        # reports/aprendizaje_continuo_final.md (mitades A/B y prueba negativa; ≈ 10–20 min en CPU)
```

3. Con esos resultados: añadir a `reports/informe_modelos.md` las secciones «Validación con el conjunto independiente» y «Aprendizaje continuo verificado» con las conclusiones finales (sin maquillar resultados si quedan bajo los umbrales), actualizar `docs/crisp_ml_q.md` (fase 4 y 6) y marcar HU35 y HU37 como hechas en `reports/aceptacion_final.md`.
4. El ciclo puede publicar una versión nueva (solo si no empeora en `test.csv`); queda activa y registrada en `models/registry.json`. Si se quiere volver a v1: pantalla *Modelos de IA* → *Activar*.

## 2. Entrega del repositorio

- `git push` de los commits locales y de la etiqueta `v1.0` (`git push origin main --tags`): lo hace el equipo.
- `models/registry.json` registra una versión **v2** publicada por el equipo cuya carpeta `models/v2/` no está en el repositorio (`.gitignore`). En un clon nuevo, activar v2 responde «Faltan los archivos de la versión v2» (no falla). Decidir si se versiona `models/v2/` o se retira del registro.

## 3. Trabajo futuro

### Seguridad
- Tokens de 8 h sin refresco ni revocación en el servidor: expiración corta + refresco y cierre de sesión en el servidor.
- Forzar el cambio de las contraseñas de demostración en el primer inicio de sesión; política de contraseñas.
- HTTPS (proxy inverso con certificado) si el sistema sale de la red local.
- Copias de seguridad automáticas de la base y de `models/` y `data/` (hoy manuales, ver el manual de instalación).

### Datos y base de datos
- Migraciones con Alembic (hoy un cambio de tablas exige recrear la base).
- El código de ticket (`TK-0001`) se calcula con el máximo existente; con escrituras simultáneas podría repetirse: usar una secuencia.
- pgvector para guardar el embedding del ticket y buscar similares en la base (hoy en memoria, < 30 ms con ≈ 7 500 tickets).

### Funcionalidad
- Al marcar un técnico como no disponible, sus tickets abiertos no se reasignan solos.
- Corregir la categoría no reasigna al técnico de la nueva categoría (el Administrador puede hacerlo a mano).
- Listas sin paginación ni búsqueda por texto; panel sin filtros por fechas.
- Notificaciones por correo o en la interfaz.
- Zona horaria: fechas en UTC en la base y en la hora local del navegador.

### IA
- **Redacción real:** reportes como *«Recibí un correo falso de mi banco que me pide mi contraseña, es phishing»* se clasifican como Software o Correo. La mejora principal es reentrenar con tickets reales (los del equipo y los que se registren con correcciones).
- **Prioridad:** depende casi por completo de impacto y urgencia; guiar mejor al usuario al elegirlos o estimarlos con un modelo entrenado con tickets reales.
- **Historial de asignaciones** derivado por reglas: reentrenar el MLP de asignación con el historial real de la tabla `historial`.
- **Conjunto de referencia** del reentrenamiento = conjunto de prueba: usar además la mitad B del conjunto del equipo como segunda referencia.
- **Soluciones rápidas:** validar con Soporte las entradas del catálogo (en especial Correo y Seguridad) y ampliarlo con HU26.
- Reentrenamiento en horario de baja carga (usa la CPU del servidor varios minutos, aunque ya no bloquea las peticiones).

### Calidad
- Pruebas de carga con varios usuarios simultáneos.
- Las pruebas automáticas usan SQLite; PostgreSQL se verificó con la prueba de humo y la instalación limpia. Añadir una ejecución de `pytest` contra PostgreSQL.
- Revisión de accesibilidad con lector de pantalla y contraste.
