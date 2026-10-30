# Contrato de la API

Una sola aplicación FastAPI (`src/service/app.py`) sirve la **API del sistema de tickets** (Sprints 2 y 3) y la **API de inferencia** (Sprint 1), que carga la versión activa de `models/registry.json`. Documentación interactiva en `/docs` (OpenAPI en `/openapi.json`).

- **Base:** `http://<servidor>:8001` (puerto configurable con `PUERTO_APP`). JSON UTF-8.
- **Autenticación:** `POST /api/auth/login` devuelve un token JWT (8 h). Las rutas protegidas lo reciben en la cabecera `Authorization: Bearer <token>`. Sin token → `401`; con un rol no permitido → `403`.
- **Roles:** Usuario, Soporte, Administrador. En las tablas, «Sesión» = cualquier usuario autenticado; «Abierta» = sin autenticación (solo lectura o análisis sin guardar).
- **Valores válidos:** categoría `Hardware | Software | Red | Accesos | Correo | Seguridad`; prioridad `Baja | Media | Alta | Crítica`; impacto `Bajo | Medio | Alto`; urgencia `Baja | Media | Alta`; estado `Abierto | En progreso | Resuelto | Cerrado`.
- **Errores** (en español, cuerpo `{"detail": …}`): `401` sin sesión o sesión vencida, `403` sin permiso, `404` «Recurso no encontrado.», `405` método no permitido, `409` reentrenamiento ya en curso, `422` entrada inválida (lista con el campo y el motivo, p. ej. `"titulo: Debe tener al menos 3 caracteres."`) o regla de negocio, `503` modelos no disponibles. Un error inesperado devuelve `500` con un mensaje genérico, sin detalles internos; las pruebas verifican que ninguna entrada inválida lo provoque.
- **Rendimiento:** análisis y registro de un ticket < 2 s en CPU (medianas medidas: 22 ms y 32 ms, `reports/rendimiento.md`).

## 1. Sistema de tickets

| Método y ruta | Rol | Uso |
|---|---|---|
| `POST /api/auth/login` | Abierta | `{"correo", "contrasena"}` → `{"token", "usuario"}` |
| `GET /api/auth/yo` | Sesión | Usuario de la sesión (incluye `tecnico_id` si es Soporte) |
| `GET /api/usuarios` | Administrador | Listar usuarios |
| `POST /api/usuarios` | Administrador | Crear usuario `{"nombre", "correo", "contrasena", "rol"}`. Si el rol es Soporte, se crea su ficha de técnico (área «Mesa de ayuda», límite 8, aptitudes 3) |
| `PUT /api/usuarios/{id}` | Administrador | Cambiar nombre, rol, `activo` o contraseña. Si deja de ser Soporte o se desactiva, su técnico queda no disponible; si vuelve a Soporte, disponible |
| `POST /api/tickets/analizar` | Sesión | Análisis de la IA **sin guardar** (al Usuario no se le muestran el ranking de técnicos ni los similares) |
| `POST /api/tickets` | Sesión | Registrar: análisis + asignación automática con la carga real de la BD. `resuelto_con_solucion_rapida: true` lo cierra al momento |
| `GET /api/tickets` | Sesión | Usuario: los suyos; Soporte: los asignados (orden de bandeja); Administrador: todos. Filtros `estado`, `categoria`, `prioridad` |
| `GET /api/tickets/{id}` | Sesión con acceso al ticket | Detalle, comentarios, historial y, para Soporte y Administrador, el análisis de la IA |
| `PUT /api/tickets/{id}/estado` | Soporte asignado o Administrador | `Abierto → En progreso → Resuelto` (`solucion` obligatoria para Resuelto) |
| `POST /api/tickets/{id}/comentarios` | Sesión con acceso al ticket | Agregar un comentario |
| `POST /api/tickets/{id}/confirmar` | Solicitante | `Resuelto → Cerrado` |
| `POST /api/tickets/{id}/reabrir` | Solicitante | `Resuelto → En progreso` |
| `POST /api/tickets/{id}/corregir` | Soporte asignado o Administrador | Corregir categoría/prioridad; se guarda en la BD y en `data/correcciones.csv` |
| `POST /api/tickets/{id}/reasignar` | Soporte asignado o Administrador | Sin cuerpo: la IA elige otro técnico. Con `tecnico_id` (solo Administrador): manual |
| `GET /api/admin/tecnicos` | Administrador | Técnicos con su carga actual |
| `PUT /api/admin/tecnicos/{id}` | Administrador | Límite de carga, disponibilidad y aptitudes (1 a 5) |
| `GET /api/panel/resumen` | Soporte (lo suyo) o Administrador (todo) | Métricas del servicio y de la IA |
| `GET /api/soluciones` | Soporte o Administrador | Catálogo de soluciones rápidas (con `activa`) |
| `POST /api/soluciones` | Soporte o Administrador | Guardar una solución rápida (HU26): `{"problema", "categoria", "frases_ejemplo": [...], "pasos": [...], "ticket_id"}`. Con `ticket_id`, el ticket debe estar Resuelto o Cerrado y ser accesible para quien la guarda. Se sugiere de inmediato |
| `PUT /api/soluciones/{id}` | Administrador | Editar problema, categoría, frases, pasos o `activa`. Se aplica de inmediato |

## 2. Inferencia, laboratorio y modelos

| Método y ruta | Rol | Uso |
|---|---|---|
| `POST /api/analizar` | Abierta | Categoría, prioridad, técnicos, solución rápida y 5 similares (no guarda nada) |
| `POST /api/similares` | Abierta | `k` tickets similares a un texto |
| `GET /api/tecnicos` | Abierta | Estado de los técnicos del laboratorio (en memoria, independiente de la BD) |
| `PUT /api/tecnicos` | Administrador | Fijar cargas del laboratorio (para probar el balanceo) |
| `GET /api/correcciones` | Abierta | Correcciones guardadas en `data/correcciones.csv` |
| `POST /api/correcciones` | Administrador | Guardar una corrección desde el laboratorio |
| `POST /api/reentrenar` | Administrador | Reentrenar con las correcciones (mínimo 5) en un proceso aparte |
| `GET /api/reentrenar/estado` | Abierta | Estado, progreso, resultado, mínimo y número de correcciones válidas |
| `GET /api/modelos` | Abierta | Registro de versiones |
| `POST /api/modelos/activar` | Administrador | Restaurar o activar una versión publicada |
| `GET /api/metricas` | Abierta | Métricas de la versión activa y rutas de figuras |
| `GET /api/salud` | Abierta | Estado y versión cargada |

Páginas: `/` (sistema), `/laboratorio` (página de prueba de los modelos; pide iniciar sesión como Administrador para las acciones protegidas), `/docs`.

## 3. API de inferencia en detalle

### `POST /api/analizar`

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

- `tecnicos` viene **ordenado**: el primero (`recomendado: true`) es la asignación sugerida. Los técnicos que ya alcanzaron su límite de carga (`saturado: true`) pasan al final; si todos están al límite se recomienda al de menor ocupación. `nota` explica cuándo se salta al técnico más adecuado por estar saturado. `adecuacion` es el puntaje del MLP convertido a porcentaje entre técnicos (softmax con temperatura 5 para que sea legible).
- `solucion_rapida` es `null` cuando ninguna entrada supera el umbral de similitud (calibrado por versión; v1: 0,65). Es un detector conservador: funciona mejor con textos cortos y parecidos a los ejemplos.
- `similares` son 5 tickets ya atendidos; `solucion` es `null` si el caso no tiene solución registrada.
- La **prioridad** se calcula con impacto, urgencia y usuarios afectados (la categoría llega como probabilidades de la clasificación).
- Las **cargas** de los técnicos son las que mantiene el servicio (ver `PUT /api/tecnicos`). En el Sprint 2 el backend las calculará desde la base de datos y las enviará antes de analizar; ver la nota de integración.

### `POST /api/similares`

Entrada: `{"texto": "El correo no sincroniza en el móvil", "k": 5}` (`k` de 1 a 20). Salida: `{"similares": [ {…como en /api/analizar…} ], "tiempo_ms": 40.2}`.

### `GET /api/tecnicos` y `PUT /api/tecnicos`

`GET` devuelve la lista: `[{"id_tecnico": "T01", "nombre": "…", "area": "…", "limite_carga": 6, "carga": 2, "aptitudes": {"Hardware": 5, "Software": 3, "Red": 3, "Accesos": 2, "Correo": 2, "Seguridad": 2}}]`.
`PUT` (**Administrador**) recibe `{"cargas": {"T05": 6, "T07": 14}}` (solo los técnicos que cambian; enteros ≥ 0) y devuelve la lista actualizada. `422` si el técnico no existe o la carga es negativa. El estado vive en memoria y se conserva al cambiar de versión de modelos.

### `POST /api/correcciones` y `GET /api/correcciones`

```json
{
  "titulo": "Mi VPN falla", "descripcion": "La VPN no conecta",
  "categoria_corregida": "Red", "prioridad_corregida": "Media",
  "tecnico_reasignado": "T05",
  "impacto": "Medio", "urgencia": "Media", "usuarios_afectados": 1
}
```

Obligatorios: `titulo`, `descripcion`, `categoria_corregida`, `prioridad_corregida`. Opcionales: `tecnico_reasignado` (debe existir), `impacto`, `urgencia`, `usuarios_afectados` (si faltan, se derivan de la prioridad). Respuesta: `{"guardada": true, "total_correcciones": 3}`. `POST` exige **Administrador** (en el sistema, Soporte corrige desde el ticket con `POST /api/tickets/{id}/corregir`). Se añaden a `data/correcciones.csv` (columnas `titulo, descripcion, categoria_corregida, prioridad_corregida, tecnico_reasignado, impacto, urgencia, usuarios_afectados, fecha`). `GET` devuelve todas las guardadas.

### `POST /api/reentrenar` y `GET /api/reentrenar/estado`

Exige **Administrador**. Entrada: `{"epocas": 6, "sincrono": false}` (épocas de 1 a 30; por defecto 6). Exige un mínimo de correcciones válidas (`MIN_CORRECCIONES_REENTRENAR`, 5 por defecto): si no se alcanza responde `422` con «Se necesitan al menos 5 correcciones válidas…». Se ejecuta en un **proceso aparte** (`python -m src.training.reentrenar`), sin bloquear las peticiones. Reentrena desde la versión vigente con `train.csv` + correcciones (cada una repetida ×3) y compara en un **conjunto de referencia fijo** (`test.csv`, tickets reales). **Solo se publica si su F1 macro de categoría iguala o supera al de la vigente**; si no, se descarta y queda registrada.

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

`GET /api/reentrenar/estado` → `{"estado": "inactivo | ejecutando | terminado | error", "mensajes": […], "resultado": {…}, "inicio": "…", "fin": "…", "minimo_correcciones": 5, "correcciones_validas": 2}`. Si se publica una versión, el servicio la carga sin reiniciarse.

### `GET /api/modelos` y `POST /api/modelos/activar`

`GET` devuelve el registro: `{"activa": "v1", "versiones": [{"version": "v1", "fecha": "…", "directorio": "models/v1", "metricas": {…}, "n_correcciones": 0, "estado": "publicada", "nota": "…"}]}`.
`POST` (**Administrador**) con `{"version": "v1"}` restaura (activa) una versión **publicada**; `422` si no existe, fue descartada o faltan sus archivos.

### `GET /api/metricas`

Devuelve para la versión activa: `resumen`, `categoria` (`base` y `gru`, cada una con `reales`, `todos` y `por_fuente`; en `reales`: `f1_macro`, `exactitud`, `por_clase` con `precision`, `recall`, `f1` y `soporte`, y `matriz_confusion`), `prioridad` (el MLP, sus variantes y las referencias), `asignacion`, `similitud` y `figuras` (rutas servidas bajo `/figuras/…`).

## 4. Integración entre el sistema y los modelos

1. Al registrar un ticket, `src/sistema/ia.py` usa el mismo objeto `Servicio` en memoria (sin HTTP), con las cargas, límites, aptitudes, disponibilidad y nombres de los técnicos **tal como están en la BD** (incluidos los técnicos creados después del entrenamiento), y guarda la respuesta en `analisis_ia`.
2. Las correcciones de Soporte se guardan en la tabla `correcciones` y en `data/correcciones.csv`, que es lo que usa el reentrenamiento.
3. Una versión publicada por el reentrenamiento o activada por el Administrador se carga sin reiniciar; los tickets nuevos la usan (queda en `analisis_ia.version_modelos`).
4. Las soluciones rápidas guardadas o editadas actualizan el índice en memoria de inmediato (`Servicio.recargar_soluciones`).
