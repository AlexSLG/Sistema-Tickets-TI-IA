# Plan de pruebas

Casos de prueba por historia de usuario (HU01–HU37). Tipos: **A** = automática (`pytest`), **E2E** = navegador real con Playwright (`tests/e2e/`, se ejecuta aparte), **H** = prueba de humo contra la aplicación en marcha (`scripts/prueba_humo.py`), **M** = manual o con script de verificación.

## Cómo ejecutar

```bash
.venv\Scripts\python -m pytest                                   # todas las automáticas (las E2E se omiten)
.venv\Scripts\python scripts\prueba_humo.py http://localhost:8001  # humo contra la aplicación en marcha
$env:E2E_BASE="http://localhost:8001"; .venv\Scripts\python -m pytest tests/e2e -v   # E2E (requiere Playwright)
.venv\Scripts\python scripts\medir_rendimiento.py http://localhost:8001              # rendimiento
```

Las pruebas automáticas usan una base SQLite temporal, un archivo de correcciones temporal y una copia del catálogo de soluciones rápidas: no modifican `data/app.db`, `data/correcciones.csv` ni `data/processed/soluciones_rapidas.json`. La prueba de humo y la E2E sí dejan tickets nuevos en la base de la aplicación contra la que se ejecutan.

## Sprint 1 · Datos y modelos

| HU | Historia | Caso / pasos | Resultado esperado | Tipo | Cubierto por |
|---|---|---|---|---|---|
| HU01 | Conjunto de datos en español, etiquetado y dividido | Validar esquema, valores, balance, división por grupo, variantes y estratificación | Valores de la taxonomía, sin vacíos, sin fuga entre train/val/test | A | `tests/test_datos.py` (5 pruebas) |
| HU02–HU09 | Modelos: clasificación (GRU vs. base), prioridad (MLP), asignación (MLP) y balanceo, similitud, soluciones rápidas, datos auxiliares | Respuesta del análisis con probabilidades; ejemplos claros por categoría; matriz impacto × urgencia; balanceo (saturado, todos al límite, ninguno supera el límite); umbral de soluciones rápidas; similares; técnicos y historial coherentes | Criterios del Sprint 1 cumplidos (`reports/informe_modelos.md`) | A | `tests/test_api.py` (respuesta, categorías, prioridad, 3 de balanceo, soluciones rápidas, similares), `tests/test_datos.py` (técnicos, historial, soluciones rápidas) |
| HU10 | Servicio de inferencia y página de prueba | Endpoints de inferencia, validación de entradas, `/`, `/laboratorio`, `/docs` | 200 en uso válido, 422 en entradas inválidas | A, E2E | `test_api.py::test_validacion_de_entradas`, `::test_pagina_y_documentacion`, `e2e::test_laboratorio_pide_administrador_para_cambiar_datos` |
| HU11 | Reentrenamiento y versiones | Registrar versiones publicadas/descartadas; restaurar; reentrenar en proceso aparte | Solo se publica si no empeora; restaurar falla con versiones descartadas o inexistentes | A, M | `test_api.py::test_registro_de_versiones`, `::test_reentrenamiento_en_proceso_aparte`, `::test_modelos_y_metricas`; `reports/prueba_reentrenamiento.md` |
| HU12 | Diseño para el sistema | Revisión del modelo de datos y del contrato | Documentos coherentes con el código | M | `docs/modelo_datos.md`, `docs/contrato_api.md` |

## Sprint 2 · Sistema

| HU | Historia | Caso / pasos | Resultado esperado | Tipo | Cubierto por |
|---|---|---|---|---|---|
| HU13 | Iniciar sesión con roles | Login correcto e incorrecto; sin token; token inválido; Usuario en rutas de Administrador | 200 / 401 / 401 / 403 | A, E2E | `test_sistema.py` (login, 401, 403), E2E (entrar y salir con los tres roles) |
| HU14 | Administrar usuarios | Crear, cambiar rol, desactivar, contraseña; el Administrador no se quita su rol; **un usuario Soporte nuevo es técnico y recibe tickets** | Cambios aplicados; 422 al quitarse el rol; ficha de técnico T09 disponible | A | `test_sistema.py::test_administrador_gestiona_usuarios`, `::test_administrador_no_puede_quitarse_el_rol`, `test_admin.py::test_usuario_soporte_nuevo_es_tecnico_y_recibe_tickets` |
| HU15 | Administrar técnicos | Editar límite, disponibilidad y aptitudes; efecto en la asignación | Solo Administrador; la IA usa los nuevos valores | A | `test_admin.py` (4 pruebas) |
| HU16 | Registrar un ticket | Registrar con IA | Ticket con categoría, prioridad, técnico y análisis | A, E2E, H | `test_tickets.py::test_registrar_ticket_tiene_categoria_prioridad_tecnico_y_analisis`, E2E incidente crítico, humo paso 2 |
| HU17 | Consultar mis tickets | Usuario ve solo los suyos; no ve tickets ajenos | 403/404 en ajenos | A, E2E | `test_tickets.py::test_permisos_sobre_tickets_ajenos`, E2E |
| HU18 | Bandeja de Soporte | Orden Crítica primero y más antiguo | Orden correcto | A, H | `test_tickets.py::test_bandeja_ordenada_por_prioridad`, humo paso 3 |
| HU19 | Atender el ticket | En progreso → Resuelto con solución obligatoria; comentarios | Transiciones válidas; 422 sin solución | A, E2E, H | `test_tickets.py::test_tecnico_ve_el_ticket_y_lo_resuelve`, `::test_comentarios`, E2E, humo |
| HU20 | Confirmar o reabrir | Solicitante confirma (Cerrado) o reabre (En progreso) | Solo el solicitante | A, E2E | `test_tickets.py::test_usuario_confirma_o_reabre`, E2E |
| HU21 | Análisis de la IA antes de registrar | `POST /api/tickets/analizar` no crea ticket; al Usuario no se le muestran técnicos ni similares | Sin ticket nuevo | A | `test_tickets.py::test_analizar_antes_de_guardar_no_crea_ticket` |
| HU22 | Solución rápida | Sugerencia y cierre por autoservicio | Ticket Cerrado con `resuelto_con_solucion_rapida` | A, E2E, H | `test_tickets.py::test_solucion_rapida_resuelta_cierra_el_ticket`, E2E, humo paso 1 |
| HU23 | Asignación y reasignación | Técnico al límite o no disponible no recibe; reasignación manual y automática | Pasa al siguiente con capacidad | A, H | `test_tickets.py` (3 pruebas), humo paso 5 |
| HU24 | Corregir la clasificación | Corrección en BD y en `data/correcciones.csv` | Fila en ambos | A, H | `test_tickets.py::test_correccion_guarda_fila_en_bd_y_en_csv`, humo paso 4 |
| HU25 | Casos similares | 5 similares en el análisis del ticket | Lista con similitud ≤ 1 | A | `test_api.py::test_similares`, `test_tickets.py::test_registrar_ticket…` |
| HU26 | Guardar solución rápida (Sprint 3) | Guardar desde un ticket Resuelto → se sugiere de inmediato; desactivar → deja de sugerirse; reactivar y editar; permisos (Usuario no; Soporte no edita); ticket abierto → 422 | Índice actualizado sin reiniciar | A, E2E | `tests/test_soluciones.py` (2 pruebas), E2E (botón visible al resolver) |
| HU27 | Modelos y reentrenamiento (Administrador) | Endpoints de modelos; operaciones del laboratorio solo para Administrador; mínimo de correcciones | 401/403 sin permiso; 422 con menos de 5 correcciones | A, E2E | `test_admin.py::test_endpoints_de_modelos_siguen_disponibles`, `test_api.py::test_operaciones_del_laboratorio_exigen_administrador`, `::test_reentrenar_exige_un_minimo_de_correcciones`, E2E |
| HU28–HU30 | Panel de métricas | Solo Administrador y Soporte; panel vacío; totales coherentes; Soporte ve solo lo suyo | Cifras coherentes con la BD | A, H | `tests/test_panel.py` (4 pruebas), humo paso 6 |
| HU31 | Docker Compose | Levantar en un entorno limpio y ejecutar la prueba de humo | Humo correcto | M, H | `reports/verificacion_instalacion.md` |

## Sprint 3 · Pruebas, cierre y entrega

| HU | Historia | Caso / pasos | Resultado esperado | Tipo | Cubierto por |
|---|---|---|---|---|---|
| HU32 | Manual de instalación verificado | Seguir el manual en un clon limpio con Docker en otro puerto | Sistema en marcha y humo correcto | M | `docs/manual_instalacion.md`, `reports/verificacion_instalacion.md` |
| HU33 | Manual de usuario con capturas | Capturas generadas con la aplicación real | 17 capturas, un capítulo por rol | M | `docs/manual_usuario.md`, `scripts/capturas_manual.py` |
| HU34 | Plan de pruebas, seguridad y regresión | Este plan; endpoints protegidos; errores en español sin 500 con entradas inválidas (cuerpos nulos, listas, textos de 100 000 caracteres, inyección SQL/HTML, JSON mal formado) | Ningún 500; ningún error crítico ni alto abierto | A, E2E, H | `test_api.py::test_errores_en_espanol_y_sin_500`, `reports/resultados_pruebas.md` |
| HU35 | Validación con tickets del equipo | Validar el archivo (columnas, taxonomía, duplicados, solapamiento ≥ 0,88 con los datos del proyecto); evaluar la versión activa | Informe de validación y de evaluación | A, M | `tests/test_prueba_equipo.py` (6 pruebas del validador); ejecución pendiente del archivo del equipo |
| HU36 | Datos de demostración | Semilla con todos los estados, reaperturas, correcciones, comentarios y una solución rápida de Soporte; repetible sin duplicar | Un comando: `python -m src.sistema.semilla --reiniciar` | A | `test_semilla.py::test_semilla_de_historial`, `test_sistema.py::test_semilla_crea_usuarios_y_tecnicos` |
| HU37 | Rendimiento y aprendizaje continuo | Análisis y registro < 2 s; ciclo A/B con el conjunto del equipo; prueba negativa | < 2 s; correcciones reproducidas; la versión con etiquetas erróneas no se publica | A, M | `test_api.py::test_tiempo_de_respuesta_menor_a_2_segundos`, `test_tickets.py::test_registro_de_ticket_menor_a_2_segundos`, `reports/rendimiento.md`, `test_prueba_equipo.py::test_ciclo_aprendizaje_division_y_correcciones`; ciclo completo pendiente del archivo del equipo |

## Criterios de salida

1. `pytest` sin fallos; prueba de humo y E2E correctas.
2. Ningún error de severidad crítica o alta abierto (`reports/resultados_pruebas.md`).
3. Análisis y registro < 2 s (mediana y p95).
4. Regresión completa después de cada corrección.
