# Acta de aceptación final

Proyecto: Sistema de tickets TI con IA. Equipo: Alex (Scrum Master), Jeferson (Product Owner), Jesús y César. Fecha: 2026-10-30.
Evidencia de pruebas: `reports/resultados_pruebas.md` (pytest 68/68, E2E 4/4, humo correcto, rendimiento < 2 s). Casos por historia: `docs/plan_pruebas.md`.

| HU | Historia | Estado | Evidencia / observaciones |
|---|---|---|---|
| HU01 | Datos en español, etiquetados y divididos sin fugas | Hecho con observaciones | `reports/*_resumen.md`, `tests/test_datos.py`. Etiquetas por reglas con ≈ 85 % de acierto en categoría (auditoría) |
| HU02–HU09 | Modelos: GRU de categoría, modelo base, MLP de prioridad, MLP de asignación + balanceo, similitud, soluciones rápidas, datos auxiliares | Hecho con observaciones | `reports/informe_modelos.md`: todos los umbrales cumplidos salvo «GRU mejor que el modelo base» (empate estadístico, documentado); la prioridad depende casi por completo de impacto y urgencia |
| HU10 | API de inferencia y página de prueba | Hecho | `/docs`, `/laboratorio`; acciones de cambio protegidas en el Sprint 3 |
| HU11 | Reentrenamiento con regla de no regresión y versiones | Hecho | `reports/prueba_reentrenamiento.md`, `models/registry.json`, pruebas automáticas |
| HU12 | Diseño de datos y contrato para el sistema | Hecho | `docs/modelo_datos.md` y `docs/contrato_api.md` (actualizados a lo implementado) |
| HU13 | Inicio de sesión con roles | Hecho | `tests/test_sistema.py`, E2E |
| HU14 | Administrar usuarios | Hecho | Incluye Soporte ↔ técnico automático (Sprint 3) |
| HU15 | Administrar técnicos | Hecho | `tests/test_admin.py` |
| HU16 | Registrar ticket analizado por la IA | Hecho | `tests/test_tickets.py`, E2E, humo |
| HU17 | Consultar mis tickets | Hecho | Permisos sobre tickets ajenos probados |
| HU18 | Bandeja de Soporte priorizada | Hecho | Orden Crítica → antigüedad |
| HU19 | Atender: estados, solución, comentarios | Hecho | E2E del técnico asignado |
| HU20 | Confirmar o reabrir | Hecho | Pruebas y datos de demostración con 3 reaperturas |
| HU21 | Análisis antes de registrar | Hecho | |
| HU22 | Soluciones rápidas (autoservicio) | Hecho | Cobertura del catálogo limitada (52 entradas) |
| HU23 | Asignación con balanceo y reasignación | Hecho | Cargas reales de la BD; técnicos nuevos incluidos |
| HU24 | Corregir la clasificación | Hecho | BD + `data/correcciones.csv` |
| HU25 | Casos similares | Hecho | |
| HU26 | Guardar una solución como solución rápida, editar y desactivar | Hecho | `tests/test_soluciones.py`: se sugiere de inmediato sin reiniciar; pantalla Soluciones rápidas |
| HU27 | Modelos y reentrenamiento desde la administración | Hecho | Mínimo de 5 correcciones; proceso aparte; restauración de versiones |
| HU28–HU30 | Panel de métricas del servicio y de la IA | Hecho | `tests/test_panel.py` |
| HU31 | Instalación con Docker Compose | Hecho | Verificada en entorno limpio (`reports/verificacion_instalacion.md`) |
| HU32 | Manual de instalación verificado | Hecho | `docs/manual_instalacion.md` |
| HU33 | Manual de usuario por rol con capturas | Hecho | `docs/manual_usuario.md`, 17 capturas reales |
| HU34 | Plan de pruebas, seguridad, regresión | Hecho | `docs/plan_pruebas.md`, `reports/resultados_pruebas.md`; ningún error crítico ni alto abierto |
| HU35 | Validación con tickets escritos por el equipo | **Pendiente** | Plantilla, validador y evaluación listos y probados; falta que el equipo entregue `data/prueba_equipo/tickets_equipo.csv` (≥ 60 tickets) |
| HU36 | Datos de demostración en todos los estados | Hecho | `python -m src.sistema.semilla --reiniciar`; automático en Docker |
| HU37 | Rendimiento < 2 s y aprendizaje continuo verificado | Hecho con observaciones | Rendimiento cumplido (22 ms de mediana). Regla de no regresión verificada (`reports/prueba_reentrenamiento.md`); el ciclo con datos del equipo (mitades A/B y prueba negativa, `src/training/ciclo_aprendizaje.py`) queda pendiente del mismo archivo que HU35 |

## Resultado

36 de 37 historias **hechas** (10 de ellas con observaciones documentadas: HU01, HU02–HU09 y HU37) y **1 pendiente** (HU35); además, la verificación del ciclo de aprendizaje con datos del equipo (parte de HU37) depende del mismo archivo. Lo pendiente no requiere cambios de código: al entregar el archivo del equipo se ejecutan tres comandos (`reports/pendientes_finales.md`).

| Rol | Nombre | Conformidad |
|---|---|---|
| Product Owner | Jeferson | |
| Scrum Master | Alex | |
| Equipo de desarrollo | Jesús, César | |
