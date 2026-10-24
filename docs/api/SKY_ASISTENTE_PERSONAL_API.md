# SKY v12.1 — API del Asistente Personal y del HUD

Todas las rutas `/api/*` requieren `X-SKY-KEY` (llave del dueño) y, si el 2FA del creador está activo, `X-SKY-SESSION`.

## Arquitectura

```
HUD  /  ───────────┐                          ┌─ agente_dispositivo.py v6 (127.0.0.1:8766)
Clásico /sky ──────┤                          │   token + política local del dueño
Streamlit :8501 ───┼─► /api/asistente/* ─────►│   ~/.neuralt/device_agent_policy.json
Voz manos libres ──┘   /api/hud/*             │   ledger verificable (/actions_history)
                       │                      └─ equipos remotos vía Tailscale Serve (HTTPS)
                       ├─► Home Assistant (SKY_HA_URL, red local)
                       └─► IA: Ollama local (SKY_LOCAL_ONLY=1) o proveedores en la nube
```

`neural_core/sky_asistente_personal.py` une dos intérpretes y **sólo propone**; el agente vuelve a validar cada acción contra la política del dueño, que la API no puede modificar.

## Páginas

| Ruta | Descripción |
|---|---|
| `/` y `/hud` | Interfaz HUD (núcleo, voz, módulos en ventanas, paneles) |
| `/sky` | Interfaz clásica |
| `/asistente` | Redirige al HUD |

## Asistente

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/asistente/mensaje` | `{texto, historial?, proveedor?, dispositivo?, modo: "chat"\|"voz"}` |
| POST | `/api/asistente/stream` | Igual que `/mensaje`, en NDJSON: `{"delta": "…"}` mientras el modelo habla y `{"final": {...}}` al terminar |
| POST | `/api/asistente/ejecutar` | `{action, params, dispositivo?, approval_token}`: requiere un token de aprobación individual, excepto la consulta `status` |
| GET | `/api/asistente/verificar/{command_id}` | Consulta estado real del agente; `?dispositivo=local` por defecto |
| POST | `/api/asistente/correo` | `{para, asunto, cuerpo, en_respuesta_a?, approval_token}`: envío confirmado de borrador idéntico |
| POST | `/api/asistente/casa` | `{service, entity_ids, data?, approval_token}`: operación doméstica autorizada |\n| POST | `/api/asistente/casa/preparar` | Prepara token de un solo uso para controles rápidos de luces, ventiladores, escenas o interruptores |
| GET | `/api/asistente/dispositivo` | Estado y capacidades del agente |
| GET | `/api/asistente/ayuda` | Ejemplos, capacidades, perfiles y dispositivos |
| GET / DELETE | `/api/asistente/voz[/{id}]` | Pendientes de la voz manos libres |

Respuestas de `/mensaje`: `respuesta` (puede traer `recordatorio`, `correos` o `acciones` de una rutina), `local`, `error`, `accion` (con `requiere_confirmacion`, `ejecucion`, `aviso` o `interfaz`), `casa` (con `requiere_confirmacion` y `ejecucion`) y `correo` (con `borrador`, siempre requiere confirmación).

Orden de decisión: reglas rápidas (agenda, rutinas, WhatsApp, correo, equipo, casa) → cerebro con herramientas (Ollama, `neural_core/sky_cerebro.py`) → respuesta de la IA.

## Recibos de ejecución verificados (rama de desarrollo)

El agente conserva un registro por `command_id`, y SKY permite consultar su último estado
sin ejecutar de nuevo la orden.

`GET /api/asistente/verificar/cmd_123` requiere `X-SKY-KEY` y, si está habilitada, `X-SKY-SESSION`.
Los dispositivos remotos conservan el mecanismo de autorización por `X-SKY-DEVICE-TOKEN`.
La respuesta incluye `status`, `verified` y `record`, sin credenciales.

Significado de los estados:

| Estado | Significado | `verified` |
|---|---|---|
| `RECEIVED` | Recibida | `false` |
| `SENT` | Enviada al programa o sistema; el efecto no está acreditado | `false` |
| `PENDING` | Tarea en cola, pendiente de finalización | `false` |
| `RUNNING` | Iniciada, todavía sin comprobación final | `false` |
| `VERIFIED` | La herramienta reportó comprobación de la acción | `true` |
| `FAILED` | Falló | `false` |
| `NEEDS_CONFIRMATION` | Espera una autorización explícita | `false` |

Un acuse `SENT` de una tecla multimedia **no prueba** que la reproducción haya cambiado.
Tampoco `PENDING` demuestra que un documento esté terminado.
La verificación por `command_id` puede recuperarse del registro local tras reiniciar el agente.

Estos recibos dependen de la comprobación que realmente implemente cada herramienta;
`VERIFIED` no equivale a una inspección universal de cualquier aplicación.
La ejecución física completa de Windows, voz y otros dispositivos requiere pruebas allí.

## Confirmaciones de un solo uso (fase 2)

Los resultados de `POST /api/asistente/mensaje` y `/stream` con una propuesta que
requiere confirmación devuelven `approval_token` junto con la descripción. El HUD
presenta la orden, sus parámetros y solicita un clic del propietario antes de enviar
la aprobación.

- `POST /api/asistente/ejecutar` requiere `approval_token` para cualquier
  acción que no sea la consulta de estado `status`.
- `POST /api/asistente/correo` requiere aprobación del borrador exacto:
  destinatario, asunto, texto y referencia de respuesta.
- `POST /api/asistente/casa` requiere aprobación de servicio, entidad y datos
  exactos. Los botones de control rápido obtienen una aprobación desde
  `/api/asistente/casa/preparar` (únicamente dominios permitidos de bajo riesgo).
- `GET /api/asistente/voz` adjunta una aprobación efímera a cada propuesta
  pendiente de voz: no ejecuta las órdenes al leerlas.
- Los tokens se consumen **antes** de ejecutar, duran 180 segundos, no se pueden
  reutilizar y se vinculan al dispositivo, a los parámetros y a la sesión propietaria
  si existe, además de exigir la autenticación original de SKY.
- La política del agente local se revisa de nuevo antes de ejecutar.
- Este registro de aprobaciones es local al proceso: la configuración con varios
  workers requerirá un almacenamiento compartido atómico o afinidad explícita.
  Si se reinicia la API, las aprobaciones pendientes caducan por diseño.
- Para operaciones realmente críticas, un clic o una aprobación por voz no equivale
  a autenticación biométrica o MFA renovada: ese endurecimiento está pendiente.

## KPIs de ejecución

`GET /api/hud/kpis/ejecuciones` consulta hasta 500 transiciones recientes
del agente e informa acciones finales verificadas/fallidas y acciones en estados
enviado, pendiente o en progreso. La tasa de éxito se calcula **sólo sobre
estados finales**; si no hay resultados finales devuelve `null`.
El KPI no inventa un resultado cuando el agente está desconectado
(`available: false`). Los valores representan una muestra del ledger, no toda
la historia operativa del usuario.

## HUD

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/hud/estado` | Agente, motor de IA (`solo_local`, `ollama`), Home Assistant, voz local, versión |
| GET | `/api/hud/acciones` | Registro verificado (última línea por orden, más reciente primero) |
| GET | `/api/hud/tareas` | Tareas en segundo plano del agente |
| GET | `/api/hud/notas` | Nombres de las notas locales |
| GET | `/api/hud/casa` | Entidades de Home Assistant (sin token) |
| GET | `/api/hud/youtube?q=` | Videos incrustables vía YouTube Data API (`YOUTUBE_API_KEY`) |
| POST | `/api/hud/tts` | `{texto}` → WAV con Piper (voz local) |
| GET | `/api/hud/avisos` | Recordatorios y rutinas a decir en voz alta (se marcan como vistos) |
| GET | `/api/hud/agenda` · DELETE `/api/hud/agenda/{id}` | Recordatorios pendientes y rutinas |
| POST | `/api/hud/rutinas` | `{nombre, frases, hora?, dias?, pasos}`; pasos: `saludo`, `recordatorios_hoy`, `correo_resumen`, `decir`, `accion` |
| GET | `/api/hud/diagnostico` | Qué funciona, qué falta y cómo arreglarlo |
| POST | `/api/global-media/stt/transcribe` | Transcripción local con faster-whisper (usada por el HUD) |

## Acciones del agente v6

| Acción | Capacidad | Parámetros |
|---|---|---|
| `status` | status | — |
| `open_url` | open_url | `url` (HTTPS) |
| `launch_app` | launch_app / apps_extra | `app`: calculator, text_editor, file_manager, browser · chrome, edge, firefox, word, excel, powerpoint, outlook, vscode, spotify, vlc, whatsapp, telegram, camera, settings, paint, music, mail, calendar · apps personalizadas |
| `media_control` / `media_key` | media (volumen → volume) | `command`: play_pause, next, previous, stop · `key`: play_pause, next_track, previous_track, volume_up, volume_down, mute |
| `volume` | volume | `command`: up, down, mute, set · `level` 0-100 |
| `play_media` | play_media | `query` + `service` (youtube, youtube_music, spotify) **o** `path` autorizado |
| `notify` | notify | `title`, `message` |
| `task_action` | tasks | `subaction`: create_presentation, create_document, append · `topic` / `modification` |
| `open_file` | files | `target`: documentos, descargas, escritorio, imágenes, videos, música (con OneDrive) o nombre de documento |
| `open_path` / `list_path` | files | `path` dentro de `allowed_folders` |
| `window_action` / `organize_windows` | windows | `subaction`: list, focus, minimize, restore, close, organize · `target` |
| `note_create` / `note_append` / `note_trash` | notes | `name`, `content`, `confirmed: true` (lo agrega `/ejecutar`) |
| `type_text` | type_text | `text` (≤ 5000) |
| `screenshot` | screenshot | — |
| `clipboard_get` / `clipboard_set` | clipboard | `text` (≤ 10 000) |
| `lock_screen` | lock | — |
| `player_control`, `voice_control`, `holographic_window`, `social_action` | — | Acciones de interfaz: el agente responde `status: "UI"` |

Rutas GET del agente: `/status`, `/verify_action?command_id=`, `/actions_history`, `/tasks`.
Códigos: `200` ok · `400` parámetros o acción inválida · `401` token · `403` capacidad desactivada (con el comando para activarla) · `413` cuerpo > 32 KB.
