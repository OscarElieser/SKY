# SKY Intelligent Workspace API · v9.5

Servicio privado integrado en SKY Engine API. Autenticación: encabezado `X-SKY-KEY` con la clave del propietario. Ninguna ruta de este documento acepta tokens sociales como sustituto.

## Crear una propuesta desde una única conversación

`POST /api/sky/intelligent/message`

```json
{
  "message": "Crea mi proyecto completo de aula virtual con mundo 3D y materiales",
  "provider": "local",
  "project_id": null,
  "share_project_context": false,
  "share_project_history": false
}
```

Responde con `type: "proposal"` y `request` (ID, fingerprint SHA-256, etapas, progreso). Si el mensaje no pide claramente una creación, responde `type: "answer"` y utiliza el asistente existente. Esta clasificación es una detección local conservadora, no comprensión universal. Un proveedor externo solo se utiliza si fue elegido por el propietario.

## Revisar y autorizar

- `GET /api/sky/intelligent/requests` — trabajos recientes, sin secretos.
- `GET /api/sky/intelligent/requests/{id}` — estado y entregables del trabajo.
- `POST /api/sky/intelligent/requests/{id}/approve` — aprobación expresa.

```json
{"approve": true, "expected_fingerprint": "<64 caracteres hexadecimales mostrados en la propuesta>"}
```

Si el fingerprint no coincide, se devuelve `409`; si no se aprueba, `403`. La operación de aprobación es de un solo uso. Una interrupción a mitad de la activación deja la solicitud en `needs_review` para evitar un segundo flujo sin revisión.

## Consultar resultados

`GET /api/sky/intelligent/requests/{id}/conversation` recupera intercambios guardados del proyecto. La respuesta de estado incluye `project_id`, `flow_id`, `completed_percent`, `deliverables`, `project_export` y `error`.

Los archivos se obtienen por las rutas existentes: `/api/sky/files/{id}` para Office Studio, `/api/sky/experiences/{id}/html` para diseños, y `/api/sky/projects/{id}/export.zip` para el ZIP que contiene únicamente entregables existentes, sin notas personales, chats ni claves. Las rutas siguen requiriendo `X-SKY-KEY`.

Las acciones de pausa, reanudación y cancelación se reutilizan del motor estable de v9.4: `/api/sky/workflows/{flow_id}/pause`, `/resume` y `/cancel`.

## Alcance técnico

- El orquestador **reutiliza** SKY Projects, SKY Workbench, SKY Workflows, SKY Office, SKY World y SKY Experience, sin duplicar sus motores de ejecución.
- Estados persistidos en una base SQLite propia: `sky_intelligent.sqlite3`. Incluida en preflight y en respaldos extendidos.
- Etapas posibles actualmente: planificación determinista, mundo 3D procedural, diseño HTML editable, borrador DOCX/PPTX/PDF. No se presenta un borrador como documento terminado sin revisión humana.
- Sin credenciales externas ni automatización de BAQUEANO, pagos o shell.

## Extensión de v9.6

La API de Intelligent Workspace se amplía de forma compatible con revisión contextual de planes y nuevas versiones de entregables. Ver `SKY_CONTEXTUAL_API.md`. La interfaz básica sigue en `/sky` y BAQUEANO sigue reservado al creador.
