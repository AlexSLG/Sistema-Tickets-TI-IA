# Rendimiento del sistema

Fecha: 2026-10-30 08:49. Servidor: `http://localhost:8002` (local, uvicorn + SQLite). Versión de modelos: v1.
Equipo de medición: Windows 10, AMD64 Family 25 Model 68 Stepping 1, AuthenticAMD, 16 hilos. Los modelos se ejecutan **solo en CPU** (PyTorch sin GPU).

Tiempo de respuesta medido desde el cliente (incluye autenticación, base de datos, IA y red local). Criterio: **< 2 s** en mediana y p95.

| Operación | Peticiones | Mediana | p95 | Máximo | Criterio |
|---|---:|---:|---:|---:|---|
| Analizar ticket (`POST /api/tickets/analizar`) | 100 | 22 ms | 31 ms | 35 ms | cumple |
| Registrar ticket (`POST /api/tickets`: análisis + asignación + guardado) | 50 | 32 ms | 45 ms | 49 ms | cumple |

Tiempo interno de la IA por análisis (campo `tiempo_ms`): mediana 16 ms, p95 25 ms.

Textos: muestra fija (semilla 42) del conjunto de prueba `data/processed/test.csv`, con combinaciones variadas de impacto y urgencia.
Reproducir: `python scripts/medir_rendimiento.py http://localhost:8001`. La prueba automática `tests/test_api.py::test_tiempo_de_respuesta_menor_a_2_segundos` y `tests/test_tickets.py::test_registro_de_ticket_menor_a_2_segundos` lo verifican en cada ejecución de pytest.
