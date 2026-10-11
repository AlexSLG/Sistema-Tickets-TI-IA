# Contrato de la API de inferencia

Servicio FastAPI que carga la **versión activa** de `models/registry.json`. El backend del Sprint 2 lo usa para analizar tickets; no guarda datos de negocio. Documentación interactiva en `/docs` (OpenAPI en `/openapi.json`).

- **Base:** `http://<servidor>:8000`. JSON UTF-8. Sin autenticación en el Sprint 1 (el backend del Sprint 2 debe protegerlo y no exponerlo a Internet).
- **Valores válidos:** categoría `Hardware | Software | Red | Accesos | Correo | Seguridad`; prioridad `Baja | Media | Alta | Crítica`; impacto `Bajo | Medio | Alto`; urgencia `Baja | Media | Alta`.
- **Errores:** `422` entrada inválida (detalle de FastAPI), `409` reentrenamiento ya en curso, `503` modelos no disponibles. Cuerpo: `{"detail": "…"}`.
- **Rendimiento:** respuesta de `/api/analizar` < 2 s en CPU (≈ 0,1–0,2 s medidos; la prueba automática exige < 2 s).

## Resumen

| Método y ruta | Uso |
|---|---|
| `POST /api/analizar` | Categoría, prioridad, técnicos, solución rápida y 5 similares |
| `POST /api/similares` | `k` tickets similares a un texto |
| `GET /api/tecnicos` | Estado de los técnicos (límite, carga y aptitudes) |
| `PUT /api/tecnicos` | Fijar cargas (para probar el balanceo) |
| `POST /api/correcciones` · `GET /api/correcciones` | Guardar y listar correcciones |
| `POST /api/reentrenar` · `GET /api/reentrenar/estado` | Reentrenar con las correcciones y consultar el estado |
| `GET /api/modelos` · `POST /api/modelos/activar` | Registro de versiones; restaurar o activar una versión publicada |
| `GET /api/metricas` | Métricas de la versión activa y rutas de figuras |
| `GET /api/salud` | Estado y versión cargada |

## `POST /api/analizar`

**Entrada**

```json
{
  "titulo": "No puedo conectarme a la VPN",
  "descripcion": "Desde esta mañana el cliente VPN da error al conectar desde casa y no puedo trabajar",
  "impacto": "Medio",
  "urgencia": "Alta",
  "usuarios_afectados": 1
}
```

| Campo | Tipo | Reglas |
|---|---|---|
| `titulo` | texto | 3–200 caracteres |
| `descripcion` | texto | 3–5 000 caracteres |
| `impacto` | texto | `Bajo \| Medio \| Alto` (por defecto `Medio`) |
| `urgencia` | texto | `Baja \| Media \| Alta` (por defecto `Media`) |
| `usuarios_afectados` | entero | 1–100 000 (por defecto 1) |

**Salida (`200`)**

```json
{
  "clasificacion": {
    "categoria": "Red",
    "probabilidades": {"Hardware": 0.06, "Software": 0.00, "Red": 0.81, "Accesos": 0.02, "Correo": 0.09, "Seguridad": 0.01}
  },
  "prioridad": {
    "prioridad": "Alta",
    "probabilidades": {"Baja": 0.00, "Media": 0.03, "Alta": 0.91, "Crítica": 0.06}
  },
  "tecnicos": [
    {"id_tecnico": "T05", "nombre": "Marcela Vega", "area": "Redes y comunicaciones", "aptitud": 5, "carga": 2, "limite_carga": 6,
     "saturado": false, "puntaje": -13.35, "adecuacion": 0.62, "recomendado": true, "nota": null},
    {"id_tecnico": "T06", "nombre": "Julián Paredes", "area": "Redes y seguridad", "aptitud": 4, "carga": 2, "limite_carga": 6,
     "saturado": false, "puntaje": -21.57, "adecuacion": 0.00, "recomendado": false, "nota": null}
  ],
  "solucion_rapida": {
    "id": "SR-03", "categoria": "Red", "problema": "No puedo conectarme a la VPN", "similitud": 0.91,
    "pasos": ["Verifica que tienes internet…", "Cierra y vuelve a abrir el cliente VPN…"]
  },
  "similares": [
    {"id": "ML-1234", "titulo": "…", "descripcion": "…", "categoria": "Red", "prioridad": "Media", "fuente": "multilang",
     "similitud": 0.91, "solucion": "…"}
  ],
  "version_modelos": "v1",
  "tiempo_ms": 187.3
}
```

- `tecnicos` viene **ordenado**: el primero (`recomendado: true`) es la asignación sugerida. Los técnicos que ya alcanzaron su límite de carga (`saturado: true`) pasan al final; si todos están al límite se recomienda al de menor ocupación. `nota` explica cuándo se salta al técnico más adecuado por estar saturado. `adecuacion` es el puntaje del MLP convertido a porcentaje entre técnicos.
- `solucion_rapida` es `null` cuando ninguna entrada supera el umbral de similitud (calibrado por versión; v1: 0,65). Es un detector conservador: funciona mejor con textos cortos y parecidos a los ejemplos.
- `similares` son 5 tickets ya atendidos; `solucion` es `null` si el caso no tiene solución registrada.
- La **prioridad** se calcula con impacto, urgencia y usuarios afectados (la categoría llega como probabilidades de la clasificación).
- Las **cargas** de los técnicos son las que mantiene el servicio (ver `PUT /api/tecnicos`). En el Sprint 2 el backend las calculará desde la base de datos y las enviará antes de analizar; ver la nota de integración.

## `POST /api/similares`

Entrada: `{"texto": "El correo no sincroniza en el móvil", "k": 5}` (`k` de 1 a 20). Salida: `{"similares": [ {…como en /api/analizar…} ], "tiempo_ms": 40.2}`.

## `GET /api/tecnicos` y `PUT /api/tecnicos`

`GET` devuelve la lista: `[{"id_tecnico": "T01", "nombre": "…", "area": "…", "limite_carga": 6, "carga": 2, "aptitudes": {"Hardware": 5, "Software": 3, "Red": 3, "Accesos": 2, "Correo": 2, "Seguridad": 2}}]`.
`PUT` recibe `{"cargas": {"T05": 6, "T07": 14}}` (solo los técnicos que cambian; enteros ≥ 0) y devuelve la lista actualizada. `422` si el técnico no existe o la carga es negativa. El estado vive en memoria y se conserva al cambiar de versión de modelos.

## `POST /api/correcciones` y `GET /api/correcciones`

```json
{
  "titulo": "Mi VPN falla", "descripcion": "La VPN no conecta",
  "categoria_corregida": "Red", "prioridad_corregida": "Media",
  "tecnico_reasignado": "T05",
  "impacto": "Medio", "urgencia": "Media", "usuarios_afectados": 1
}
```

Obligatorios: `titulo`, `descripcion`, `categoria_corregida`, `prioridad_corregida`. Opcionales: `tecnico_reasignado` (debe existir), `impacto`, `urgencia`, `usuarios_afectados` (si faltan, se derivan de la prioridad). Respuesta: `{"guardada": true, "total_correcciones": 3}`. Se añaden a `data/correcciones.csv` (columnas `titulo, descripcion, categoria_corregida, prioridad_corregida, tecnico_reasignado, impacto, urgencia, usuarios_afectados, fecha`). `GET` devuelve todas las guardadas.

## `POST /api/reentrenar` y `GET /api/reentrenar/estado`

Entrada: `{"epocas": 6, "sincrono": false}` (épocas de 1 a 30; por defecto 6). Reentrena desde la versión vigente con `train.csv` + correcciones (cada una repetida ×3) y compara en un **conjunto de referencia fijo** (`test.csv`, tickets reales). **Solo se publica si su F1 macro de categoría iguala o supera al de la vigente**; si no, se descarta y queda registrada.

- `sincrono: false` (por defecto): responde enseguida `{"estado": "ejecutando", …}` y el trabajo sigue en segundo plano; consultar `GET /api/reentrenar/estado`. `409` si ya hay uno en curso.
- `sincrono: true`: espera (varios minutos) y devuelve el resultado.

Resultado (en `estado.resultado` o en la respuesta síncrona):

```json
{
  "vigente": {"version": "v1", "f1_macro": 0.8736},
  "nueva": {"version": "v2", "f1_macro": 0.8731},
  "diferencia": -0.0005,
  "n_correcciones": 6,
  "referencia": "test.csv (tickets reales)",
  "publicada": false,
  "motivo": "La versión nueva empeora el F1 macro (0.8731 frente a 0.8736); se descarta.",
  "segundos": 226.0
}
```

`GET /api/reentrenar/estado` → `{"estado": "inactivo | ejecutando | terminado | error", "mensajes": […], "resultado": {…}, "inicio": "…", "fin": "…"}`. Si se publica una versión, el servicio la carga sin reiniciarse.

## `GET /api/modelos` y `POST /api/modelos/activar`

`GET` devuelve el registro: `{"activa": "v1", "versiones": [{"version": "v1", "fecha": "…", "directorio": "models/v1", "metricas": {…}, "n_correcciones": 0, "estado": "publicada", "nota": "…"}]}`.
`POST` con `{"version": "v1"}` restaura (activa) una versión **publicada**; `422` si no existe o fue descartada.

## `GET /api/metricas`

Devuelve para la versión activa: `resumen`, `categoria` (`base` y `gru`, cada una con `reales`, `todos` y `por_fuente`; en `reales`: `f1_macro`, `exactitud`, `por_clase` con `precision`, `recall`, `f1` y `soporte`, y `matriz_confusion`), `prioridad` (el MLP, sus variantes y las referencias), `asignacion`, `similitud` y `figuras` (rutas servidas bajo `/figuras/…`).

## Nota de integración para el Sprint 2

1. El backend llama a `POST /api/analizar` al crear el ticket, guarda la respuesta en `analisis_ia` y el `embedding` del ticket en `tickets` (ver `docs/modelo_datos.md`).
2. Las **cargas** de los técnicos deben salir de la base de datos (tickets abiertos por técnico): antes de analizar, el backend envía `PUT /api/tecnicos` con las cargas actuales, o se amplía el contrato con un campo opcional `cargas` en la petición (cambio previsto para el Sprint 2 para no depender de estado compartido).
3. Cada corrección de Soporte se envía a `POST /api/correcciones`; el reentrenamiento lo puede lanzar un administrador (`POST /api/reentrenar`).
4. Exigir en el backend que `impacto`, `urgencia` y `usuarios_afectados` sean datos del solicitante o de Soporte: el MLP de prioridad depende casi por completo de ellos.
5. Versionar el contrato: cualquier cambio de campos se refleja en `version` de la API (`/openapi.json`).
