# SKY v12.4 — API del Asistente Personal y del HUD

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
| POST | `/api/asistente/ejecutar` | `{action, params, dispositivo?, frase?}`: confirmación del dueño (con `frase`, SKY aprende el atajo si sale bien) |
| POST | `/api/asistente/correo` | `{para, asunto, cuerpo, en_respuesta_a?}`: envío confirmado por el dueño |
| POST | `/api/asistente/casa` | `{service, entity_ids, data?, frase?}`: confirmación para Home Assistant |
| GET / POST / DELETE | `/api/asistente/emergencia` | Estado, activar o levantar la parada de emergencia (levantarla requiere la llave del dueño) |
| GET | `/api/asistente/dispositivo` | Estado y capacidades del agente |
| GET | `/api/asistente/ayuda` | Ejemplos, capacidades, perfiles y dispositivos |
| GET / DELETE | `/api/asistente/voz[/{id}]` | Pendientes de la voz manos libres |

Respuestas de `/mensaje`: `respuesta` (puede traer `recordatorio`, `correos` o `acciones` de una rutina), `local`, `error`, `accion` (con `requiere_confirmacion`, `ejecucion`, `aviso` o `interfaz`), `casa` (con `requiere_confirmacion` y `ejecucion`) y `correo` (con `borrador`, siempre requiere confirmación).

Orden de decisión: parada de emergencia → reglas rápidas (agenda, rutinas, WhatsApp, correo, aprendizaje, KPIs, interfaz, equipo, casa) → atajos aprendidos → cerebro con herramientas (Ollama, `neural_core/sky_cerebro.py`) → respuesta de la IA.

Campos v12.2 en las respuestas: `ms` (tiempo real del turno), `nivel_riesgo` (1 bajo, 2 moderado, 3 alto: siempre requiere confirmación), `aprender` (frase a enviar en `/ejecutar` al confirmar), `aprendido` (resuelto por un atajo), `aprendido_ahora`, `modulo: "kpi"` + `kpi` (abre el panel de rendimiento) y `parada`.

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
| GET | `/api/hud/kpi?periodo=hoy\|semana` | KPIs reales: acciones, automatización, asistente, modelo, API (p50/p95/p99, disponibilidad), agente, voz, seguridad, servicio, serie por hora, problemas detectados, SLO, sistema y `texto` |
| POST | `/api/hud/kpi/evento` | `{tipo: voz\|tarea, nombre: primera_voz\|interrupcion\|error_microfono\|error_reproduccion\|cancelada, ms?, ok?}` (mediciones del navegador) |
| GET | `/api/hud/aprendizaje` · DELETE `/api/hud/aprendizaje/atajos/{frase}` | Lo aprendido y olvidar un atajo |
| GET | `/api/hud/memoria` · DELETE `/api/hud/memoria/{id}` | Exportar todo lo que SKY sabe del dueño (clasificado) y borrar un dato |
| GET / PUT | `/api/hud/perfil` | Perfil `USER.md` (`{texto}`, máx. 8000, sin contraseñas) |
| GET / POST | `/api/hud/skills` · DELETE `/api/hud/skills/{id}` · POST `/api/hud/skills/{id}/ejecutar` | Skills integradas y propias (`{nombre, descripcion?, frases?, pasos}`) |
| GET | `/api/hud/programadas` · PATCH `/{id}` `{activa}` · DELETE `/{id}` | Tareas programadas |
| GET | `/api/hud/borradores` · POST `/preparar` · PATCH `/{id}` `{cuerpo}` · POST `/{id}/enviar` · DELETE `/{id}` | Borradores de correo; `enviar` es la confirmación del dueño |
| GET | `/api/hud/whatsapp` · POST `/api/hud/whatsapp/prueba` | Estado del canal de WhatsApp y mensaje de prueba |
| GET | `/api/hud/habilidades` · PATCH `/api/hud/habilidades/{id}` `{activa}` | Catálogo completo (nativas, Builder, skills, integraciones, necesidades) |
| GET | `/api/hud/integraciones` | Vía, requisitos y estado de cada plataforma |
| POST | `/api/hud/builder/proponer` `{pedido}` | La IA diseña, revisa y prueba una habilidad (no la instala) |
| POST | `/api/hud/builder/version` `{manifiesto, codigo}` | Versión escrita por el dueño (se revisa y prueba igual) |
| GET | `/api/hud/builder/{id}?version=` | Manifiesto, código y reporte de pruebas |
| POST | `/api/hud/builder/{id}/aprobar` `{version, permisos}` | Aprobación del dueño: instala esa versión con esos permisos (vuelve a probar) |
| POST | `/api/hud/builder/{id}/desactivar` · DELETE `/api/hud/builder/{id}` | Quitar permisos / eliminar con todas sus versiones |
| GET | `/api/hud/creaciones/{imagenes\|musica\|presentaciones}[/{archivo}]` | Lo que creó SKY (nombre validado, sólo con la llave) |

Manifiesto del Skill Builder: `{nombre, descripcion, disparadores[], permisos[acciones, internet:<dominio>], fuentes[{nombre, url https}], pruebas[{entrada, contexto, espera[]}]}`; código: `def ejecutar(entrada, contexto) -> {"decir": str, "acciones": [{"orden": str}] (≤5)}`.

Pasos de rutinas y skills: `saludo`, `recordatorios_hoy`, `correo_resumen`, `correo_borradores`, `borradores_pendientes`, `decir{texto}`, `orden{texto}`, `skill{id}`, `noticias{tema}`, `aprender{tema}`, `intereses`, `kpi{diagnostico}`, `accion{action, params}`. Las rutinas aceptan `activa`.

### Puente de WhatsApp (`sky_whatsapp_puente.py`, 127.0.0.1:8770, sin llave de SKY)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/whatsapp/webhook` | Verificación de Meta (`hub.mode`, `hub.verify_token`, `hub.challenge`) |
| POST | `/whatsapp/webhook` | Mensajes; exige `X-Hub-Signature-256` válida (401 si no), cuerpo ≤ 1 MB |
| GET | `/salud` | `{"ok": true}` |
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
