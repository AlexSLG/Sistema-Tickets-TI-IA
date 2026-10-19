# Pendientes para el Sprint 3 (20/10 – 26/10)

Lo que quedó fuera o limitado del Sprint 2. Ordenado por importancia para la entrega.

## Fuera de alcance acordado (plan del Sprint 2)

- **HU26: guardar la solución de un ticket como solución rápida.** Requiere reconstruir el índice de soluciones rápidas (`python -m src.training.entrenar_similitud --solo-soluciones` ya reconstruye solo ese índice; falta el flujo en la interfaz y decidir quién valida la entrada).
- **pgvector:** guardar el embedding del ticket en `tickets` y buscar casos similares en la base de datos (cambio aditivo: hoy los similares se calculan con el índice en memoria de `models/<versión>/`).
- **Proteger con login los endpoints del laboratorio** (`/api/analizar`, `/api/tecnicos`, `/api/reentrenar`, `/api/modelos/…`, `/api/correcciones`): siguen abiertos para la página de prueba. Hoy cualquiera con acceso a la red puede reentrenar o activar versiones; no exponer el servicio fuera de una red de confianza.
- Notificaciones (correo o avisos en la interfaz) y mejoras visuales.

## Seguridad y datos

- Cambiar `SECRETO_JWT` y las credenciales de PostgreSQL (`tickets/tickets`) del `docker-compose.yml`; sacarlas a un archivo `.env`.
- Los tokens duran 8 h sin refresco; añadir expiración corta + refresco y cierre de sesión en el servidor.
- Las contraseñas de demostración son conocidas: forzar el cambio en el primer inicio de sesión.
- Sin migraciones (Alembic): los cambios de tablas hoy exigen borrar la BD. Introducirlas antes de tener datos reales.
- El código de ticket (`TK-0001`) se calcula con el máximo existente; con escrituras simultáneas puede repetirse. Usar una secuencia de la BD.

## Funcionalidad

- **Usuarios con rol Soporte creados desde la interfaz no tienen perfil de técnico**: no reciben tickets. Falta crear el técnico (límite y aptitudes) al dar de alta o cambiar el rol.
- La administración de técnicos no permite crear ni dar de baja técnicos, solo editar los 8 existentes.
- Marcar a un técnico como no disponible o desactivar a un usuario de Soporte no reasigna sus tickets abiertos: solo deja de recibir tickets nuevos y los abiertos siguen suyos hasta reasignarlos a mano.
- Listas sin paginación ni búsqueda por texto.
- Fechas en UTC en la base y en hora local del navegador en pantalla; sin selector de zona horaria.
- El panel no tiene filtros por fechas ni gráficos interactivos (barras HTML/CSS). Chart.js si se quiere.
- Corregir la categoría de un ticket no reasigna al técnico apropiado de la nueva categoría (el administrador puede reasignar a mano).
- Eliminar comentarios o editar tickets no está contemplado.

## IA (modelos y datos)

- La clasificación de reportes con redacción real es débil: *«Recibí un correo falso de mi banco que me pide mi contraseña, es phishing»* sale como Software/Correo. El guion usa una redacción que el modelo clasifica bien; con *«El servidor de archivos no responde y todo el piso no puede trabajar»* (sin mencionar la red) sale Software/Alta. Recoger tickets reales y reentrenar, y usar el conjunto de prueba escrito por el equipo (SCRUM-100).
- Las **soluciones rápidas** solo se activan con textos cortos y parecidos a los ejemplos (umbral 0,7). Se añadió la entrada SR-51 (correo con contraseña incorrecta) para el guion; validar con Soporte las 51 entradas (las de Correo y Seguridad no tienen semilla en los datos) y ampliarlas.
- El MLP de prioridad depende de impacto y urgencia: pedirlas al solicitante con claridad (hoy son listas desplegables con valores por defecto) o estimarlas con un modelo entrenado con tickets reales.
- El **historial de asignaciones** de entrenamiento es una simulación; sustituirlo por el real (`tickets` + `historial` de la BD) y reentrenar el MLP de asignación.
- El reentrenamiento compara con `test.csv`, el mismo conjunto de evaluación. Crear un conjunto de referencia distinto para decidir las publicaciones. Con pocas correcciones (≈ 1–10) el F1 apenas se mueve y casi siempre se descarta la versión nueva; definir un mínimo de correcciones antes de permitir reentrenar.
- Reentrenar consume la CPU del servidor durante varios minutos y ralentiza las respuestas; ejecutarlo en un proceso aparte.
- El índice de soluciones rápidas de `models/v1/` se reconstruyó con la entrada nueva; `models/v2/` (creado por el equipo) conserva el índice anterior de 50 entradas (los ids siguen siendo compatibles).

## Pruebas y calidad

- La interfaz (JavaScript) se probó a mano en el navegador y con `scripts/prueba_humo.py`; faltan pruebas automáticas de interfaz (p. ej. Playwright).
- Pruebas de carga (varios usuarios a la vez) y de la compatibilidad con PostgreSQL más allá del flujo principal (las pruebas automáticas usan SQLite; PostgreSQL se probó con `docker compose` y la prueba de humo).
- Accesibilidad: las pantallas tienen etiquetas y foco visible, pero no se ha revisado con un lector de pantalla ni el contraste en todos los estados.
- La advertencia `on_event is deprecated` de FastAPI: migrar a *lifespan*.
- Línea base de pytest: 53 pruebas. Las dos advertencias restantes son de FastAPI y de PyJWT (clave corta en pruebas).

## Entrega

- Revisar y fusionar el trabajo en `main`; subir los commits locales del Sprint 2 (en este sprint no se hizo `git push`).
- Documentar en `docs/` la arquitectura final (diagrama de componentes) y actualizar `docs/modelo_datos.md` con las tablas reales (`historial`, `correcciones` simplificada).
- Ensayar la presentación con el guion del README y preparar respuestas sobre las limitaciones de la IA.
