# API de coordinación contextual de SKY v9.6

Rutas privadas bajo `/api/sky/intelligent` con `X-SKY-KEY` del propietario. Todas las revisiones requieren aprobación explícita.

## Preparar una propuesta contextual

`POST /api/sky/intelligent/message` con `message`, `project_id` opcional y `provider: "local"`. La salida `type: "proposal"` incluye `request.fingerprint`, etapas y `dependencies`: la dependencia de una etapa solo puede apuntar a resultados anteriores permitidos.

## Revisar un plan antes de autorizar

`POST /api/sky/intelligent/requests/{id}/revise-plan`

```json
{"instruction":"Quitá el mundo 3D y añadí criterios de evaluación", "expected_fingerprint":"<huella SHA-256 vigente>"}
```

- El plan se revalida y recibe una huella nueva.
- `409` si ya fue aprobado o la huella ya no coincide.
- No crea mundos, documentos ni proyectos al editar la propuesta.
- `POST /requests/{id}/approve` sigue requiriendo la **huella nueva**.

## Revisar un entregable del proyecto

`POST /api/sky/intelligent/requests/{id}/revisions`

```json
{"source_item_id":"sky-xxxxxxxxxxxxxxxx","instruction":"Añadí una actividad grupal al final"}
```

- Confirma que el entregable original está completo y **asociado a ese proyecto**.
- Devuelve `id`, `fingerprint`, `status: awaiting_approval` y descripción de la revisión.
- No modifica el archivo original durante la preparación.

`POST /api/sky/intelligent/revisions/{revision_id}/approve`

```json
{"approve":true,"expected_fingerprint":"<huella de revisión>"}
```

- Ejecuta una nueva tarea del catálogo seguro SKY Workbench, sin comandos shell.
- Vincula el nuevo resultado al proyecto y conserva el anterior.
- Repetir la aprobación devuelve `409`.
- Resultado incierto tras interrupción: `needs_review`, sin reintento automático.

`GET /api/sky/intelligent/revisions/{revision_id}` devuelve el estado (solo propietario).

`GET /api/sky/intelligent/requests/{id}` incluye el historial resumido de revisiones junto con progreso, entregables y descarga ZIP del proyecto.

## Límites

- El sistema es **local** y basado en reglas, con persistencia SQLite. No garantiza comprensión universal.
- La edición de DOCX/PPTX/PDF preserva el borrador y agrega el nuevo requisito como sección de revisión; las experiencias y mundos generan una nueva propuesta visual/procedural.
- Para XLSX/CSV existente se exige usar la edición especializada de Office Studio.
- Solicitudes de Excel sin datos CSV aportados son rechazadas; ninguna API inventa datos numéricos.
