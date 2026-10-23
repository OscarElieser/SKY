# SKY IA v12.1 — Cerebro con herramientas, voz fluida, agenda y mensajes

**Dirección conceptual:** Oscar Elieser Chamorro Guzmán.

## Entiende a la primera: cerebro con herramientas

- `neural_core/sky_cerebro.py`: cuando las reglas rápidas no entienden una orden, el **modelo local de Ollama** recibe las 18–20 herramientas de SKY (apps, música, volumen, reproductor, web, carpetas, ventanas, notas, tareas, recordatorios, captura, bloqueo, avisos, portapapeles, escribir, estado, casa y correo) y elige cuál usar con sus datos.
  - Ejemplos que antes no entendía: "está muy fuerte esto" (bajar volumen), "me aburrí de esta canción" (siguiente), "quiero algo relajante de fondo mientras trabajo" (reproducir).
- Usa la conversación previa para resolver referencias: "más fuerte", "otra", "cerralo".
- Cada herramienta se valida (apps permitidas, URLs `https`, nombres de nota, rangos) y se convierte en la misma propuesta que usan las reglas. El agente vuelve a aplicar tus permisos.
- Modelo recomendado: `qwen2.5:7b` (o `qwen2.5:3b` en equipos con poca memoria). `SKY_CEREBRO=reglas` lo desactiva.

## Voz fluida

- **Respuesta por frases:** nuevo `POST /api/asistente/stream` (NDJSON). El HUD empieza a hablar con la primera frase mientras el modelo sigue escribiendo.
- **Voz natural local con Piper** (`neural_core/sky_tts.py`, `POST /api/hud/tts`), voz `es_MX-claude-high`. Piper prepara la frase siguiente mientras suena la actual. El núcleo reacciona al audio real de la voz. Sin Piper, se usa una voz del sistema marcada como local.
- **Escucha continua "SKY…"** (botón SKY del HUD): con faster-whisper, el micrófono detecta cuándo hablás, transcribe en tu PC y sólo actúa si la frase empieza con "SKY". Sin faster-whisper usa el dictado del navegador y lo indica. Mientras SKY habla no se escucha a sí mismo.

## Agenda: recordatorios, alarmas y rutinas

- `neural_core/sky_rutinas.py`: "recuérdame en 10 minutos…", "recordame a las 5…", "recuérdame mañana a las 8…", "pon una alarma a las 6:30" (sin a. m./p. m. se entiende la próxima mañana), "despiértame a las 7", "qué recordatorios tengo".
- Rutina **"buenos días"** (saludo, recordatorios del día y correos nuevos) y rutinas propias con hora y días (`POST /api/hud/rutinas`). Sus acciones respetan tus permisos; lo no automático queda pendiente de confirmación.
- Reloj interno en la API (`SKY_AGENDA_ENABLED=1`): avisa en el HUD (lo dice en voz alta), en el escritorio y en el celular.
- Panel **Agenda** en el HUD, con opción de borrar.

## Mensajes y celular

- **Correo** (`neural_core/sky_correo.py`, Gmail, Outlook o Yahoo con contraseña de aplicación): "lee mis correos" lee los no leídos **sin marcarlos**; "responde al último correo diciendo…" y "mándale un correo a Ana diciendo…" preparan un borrador que **siempre** se confirma antes de enviar (`POST /api/asistente/correo`).
- **WhatsApp** (`neural_core/sky_contactos.py`): "mándale un whatsapp a mamá que llego tarde" abre WhatsApp con el mensaje ya escrito y vos tocás Enviar. WhatsApp no tiene API oficial para cuentas personales.
- **Contactos** en `~/.neuralt/contactos.json` (nombre → whatsapp y email).
- **Avisos al celular** vía la app de Home Assistant: `SKY_HA_NOTIFY=notify.mobile_app_tu_telefono`.

## Instalador único y autodiagnóstico

- `INSTALAR_SKY_WINDOWS.bat` (`instalar_sky.ps1`): Python, dependencias, Ollama y el modelo según tu memoria, Piper con la voz en español, faster-whisper `small`, el modelo Vosk en español, el perfil de permisos y `.env`. Se puede repetir sin problema: salta lo ya instalado. `-Local` activa el modo 100 % local.
- `SKY_INICIAR.bat` lo ejecuta solo la primera vez.
- **Diagnóstico:** `python sky_diagnostico.py`, el botón **DIAG** del HUD u opción 7 del menú. Muestra qué funciona y el comando exacto para arreglar lo que falta.

## Orden y CI

- Se eliminaron de la raíz 88 documentos que ya tenían copia idéntica en `docs/`, y otros 32 se movieron a `docs/changelogs`, `docs/guias`, `docs/manifiestos` y `docs/api`. La raíz pasó de unos 190 a 70 elementos.
- Workflows: reintentos de `apt` y límite propio para el paso de instalación. El run v12 de seguridad se había cancelado por un `apt-get` colgado en los servidores de GitHub; tras relanzarlo, **los 7 workflows de v12 terminaron en verde**.

## Evidencia y límites

- **602 pruebas aprobadas** en esta revisión (52 nuevas en `tests/test_sky_v12_1_mejoras.py`). Las 13 que fallan son las de matemática simbólica que requieren `sympy`, y fallan igual en la versión anterior. Se agregaron a ambos workflows.
- Probado en Chromium contra la API real: el streaming entrega frases cada 250 ms; una frase libre pasa por el cerebro y termina en una acción ejecutada; recordatorios, avisos, agenda, diagnóstico y modo SKY sin errores de consola.
- **No se pudo probar en un Windows real:** el instalador de PowerShell (no hay PowerShell en este entorno; las tres URLs de descarga se verificaron), Piper, faster-whisper, Ollama con un modelo real, el micrófono y las voces. Las integraciones de correo, IMAP/SMTP y Home Assistant se probaron con dobles de prueba.
- La calidad del cerebro depende del modelo: `qwen2.5:7b` elige bien las herramientas, mientras que modelos chicos (3B) se equivocan más con frases complejas.
