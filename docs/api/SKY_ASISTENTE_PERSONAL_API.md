# SKY v12 — API del Asistente Personal y del HUD

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
| POST | `/api/asistente/ejecutar` | `{action, params, dispositivo?}`: confirmación del dueño |
| POST | `/api/asistente/casa` | `{service, entity_ids, data?}`: confirmación para Home Assistant |
| GET | `/api/asistente/dispositivo` | Estado y capacidades del agente |
| GET | `/api/asistente/ayuda` | Ejemplos, capacidades, perfiles y dispositivos |
| GET / DELETE | `/api/asistente/voz[/{id}]` | Pendientes de la voz manos libres |

Respuestas de `/mensaje`: `respuesta`, `local`, `error`, `accion` (con `requiere_confirmacion`, `ejecucion`, `aviso` o `interfaz`) y `casa` (con `requiere_confirmacion` y `ejecucion`).

## HUD

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/hud/estado` | Agente, motor de IA (`solo_local`, `ollama`), Home Assistant, voz local, versión |
| GET | `/api/hud/acciones` | Registro verificado (última línea por orden, más reciente primero) |
| GET | `/api/hud/tareas` | Tareas en segundo plano del agente |
| GET | `/api/hud/notas` | Nombres de las notas locales |
| GET | `/api/hud/casa` | Entidades de Home Assistant (sin token) |
| GET | `/api/hud/youtube?q=` | Videos incrustables vía YouTube Data API (`YOUTUBE_API_KEY`) |
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
