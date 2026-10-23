# SKY v11.1 — API del Asistente Personal

Todas las rutas requieren `X-SKY-KEY` (llave del dueño) y, si el 2FA del creador está activo, `X-SKY-SESSION`.

## Arquitectura

```
Panel /asistente ─┐                       ┌─ agente_dispositivo.py (127.0.0.1:8766)
Streamlit ────────┼─► /api/asistente/* ──►│   valida token + política local del dueño
Voz manos libres ─┘   (metaverse/          │   ~/.neuralt/device_agent_policy.json
                       asistente_api.py)  └─ equipos remotos vía Tailscale Serve (HTTPS)
```

`neural_core/sky_asistente_personal.py` interpreta el texto y **sólo propone**; el agente vuelve a validar cada acción contra la política del dueño, que la API no puede modificar.

## Rutas

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/asistente` | Panel web (público, la página pide la llave) |
| GET | `/api/asistente/ayuda` | Ejemplos, capacidades, perfiles y dispositivos |
| GET | `/api/asistente/dispositivo?dispositivo=local` | Estado y capacidades activas del agente |
| POST | `/api/asistente/mensaje` | `{texto, historial?, proveedor?, dispositivo?}` → respuesta |
| POST | `/api/asistente/ejecutar` | `{action, params, dispositivo?}` → confirmación del dueño |
| GET | `/api/asistente/voz` | Propuestas pendientes de la voz manos libres |
| DELETE | `/api/asistente/voz/{id}` | Descartar una propuesta |

Para dispositivos remotos (`dispositivo` ≠ `local`) enviá `X-SKY-DEVICE-TOKEN`; el servidor no lo guarda.

### Respuestas de `/mensaje`

```json
{"tipo": "respuesta", "mensaje": "...", "proveedor": "gemini"}
{"tipo": "local", "mensaje": "Resultado: 575.0"}
{"tipo": "error", "mensaje": "Configurá un proveedor de IA..."}
{"tipo": "accion", "propuesta": {"action": "volume", "params": {"command": "up"}, "description": "Subir el volumen"},
 "mensaje": "...", "requiere_confirmacion": false, "ejecucion": {"ok": true, "message": "Volumen: up"}}
{"tipo": "accion", "propuesta": {...}, "requiere_confirmacion": true, "aviso": "La capacidad \"files\" está desactivada..."}
```

## Acciones del agente

| Acción | Capacidad | Parámetros |
|---|---|---|
| `status` | status | — |
| `open_url` | open_url | `url` (HTTPS) |
| `launch_app` | launch_app / apps_extra | `app`: calculator, text_editor, file_manager, browser · spotify, vlc, chrome, firefox, edge, vscode, word, excel, powerpoint, whatsapp, telegram, camera, settings, paint, music, mail, calendar · apps personalizadas |
| `media_control` | media | `command`: play_pause, next, previous, stop |
| `volume` | volume | `command`: up, down, mute, set · `level` 0-100 |
| `play_media` | play_media | `query` + `service` (youtube, youtube_music, spotify) **o** `path` de audio/video autorizado |
| `notify` | notify | `title`, `message` |
| `open_path` / `list_path` | files | `path` dentro de `allowed_folders` |
| `screenshot` | screenshot | — (se guarda en `~/.neuralt/capturas`) |
| `clipboard_get` / `clipboard_set` | clipboard | `text` (≤ 10 000) |
| `lock_screen` | lock | — |

Códigos del agente: `200` ok · `400` parámetros inválidos o acción inexistente · `401` token · `403` capacidad desactivada (con el comando para activarla) · `413` cuerpo > 32 KB.
