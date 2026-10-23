# SKY IA v11.1 — Asistente Personal

**Dirección conceptual:** Oscar Elieser Chamorro Guzmán. **BAQUEANO:** sin cambios.

SKY pasa de "abrir cuatro apps y una web" a ser un asistente personal que controla tu equipo con órdenes en español, por texto o por voz, **con tu autorización**: vos elegís en tu PC qué puede hacer y qué hace sin pedir confirmación.

## Funciones nuevas

- **Panel del Asistente Personal** en `http://127.0.0.1:8765/asistente`: chat, dictado por voz del navegador, lectura en voz alta de las respuestas, tarjetas de acción con *Ejecutar / Cancelar*, estado del equipo (batería, CPU, RAM), capacidades activas y pendientes del modo manos libres. Adaptado a celular.
- **Intérprete de órdenes en español** (`neural_core/sky_asistente_personal.py`): música y video (YouTube, YouTube Music, Spotify), pausa/siguiente/anterior, volumen (subir, bajar, silenciar, "volumen al 30"), abrir apps, búsquedas en Google/YouTube/Wikipedia/Mapas, carpetas, capturas, portapapeles, notificaciones y bloqueo. Lo que no es una orden va a la IA configurada (Gemini, Claude, GPT, Mistral, Groq, DeepSeek u Ollama).
- **Agente de dispositivo v5.0** con 12 capacidades: estado, webs, apps básicas, **17 apps más** (Spotify, VLC, Chrome, Firefox, Edge, VS Code, Word, Excel, PowerPoint, WhatsApp, Telegram, cámara, ajustes, Paint, Música, Correo, Calendario) y tus **apps personalizadas**, control multimedia, volumen, reproducir medios, notificaciones, archivos en carpetas autorizadas, capturas, portapapeles y bloqueo. Windows, macOS y Linux. Si una app no está instalada y tiene versión web, se abre la web.
- **Política del dueño** (`~/.neuralt/device_agent_policy.json`), sólo editable en la propia PC:
  - `python agente_dispositivo.py --perfil basico | multimedia | completo`
  - `--activar`, `--desactivar`, `--auto` (sin clic de confirmación), `--carpeta` (repetible), `--ver-politica`.
  - Opción **9** del menú `SKY_INICIAR.bat` para elegir el perfil.
- **Ejecución automática opcional**: las capacidades marcadas como `auto` se ejecutan al instante desde el panel y desde la voz manos libres; el resto pide un clic.
- **Lanzador de un clic** `INICIAR_SKY_ASISTENTE_WINDOWS.bat` / `iniciar_sky_asistente_linux_mac.sh` (opción **0** del menú): agente + API + panel. La primera vez activa el perfil *multimedia*.
- API nueva `/api/asistente/*` (ver `docs/api/SKY_ASISTENTE_PERSONAL_API.md`), protegida con la llave del dueño y el segundo factor si está activo.
- La sección "🎙️ SKY y dispositivos" de Streamlit y `sky_manos_libres.py` usan el intérprete ampliado.

## Correcciones

- El agente y la API usaban ambos el puerto **8765** por defecto y no podían correr juntos. El agente pasa a **8766** (`SKY_DEVICE_PORT` sigue funcionando). Si emparejaste un equipo por Tailscale, usá ahora `tailscale serve 8766`.
- El agente devuelve el motivo real cuando rechaza una acción (por ejemplo "capacidad desactivada… activala con…") en lugar de un HTTP genérico.
- Comparación del token con `hmac.compare_digest` sobre bytes (antes podía lanzar `TypeError` con cabeceras no ASCII).

## Seguridad: qué sigue sin hacer SKY, a propósito

Ni con el perfil completo: comandos de shell arbitrarios, abrir ejecutables o scripts (`.exe`, `.bat`, `.ps1`, `.sh`, `.py`, `.lnk`…), salir de las carpetas autorizadas (incluidos enlaces simbólicos), descargar e instalar programas ni pagar. El token del agente controla tu música y tus apps, pero no se convierte en control total de tu PC si alguien lo obtiene. La política no se puede cambiar por red. Cada acción queda en `~/.neuralt/device_agent_audit.jsonl` sin el token ni el contenido del portapapeles. Los textos de notificaciones y portapapeles viajan por variables de entorno, nunca interpolados en scripts.

## Evidencia y límites

- **51 pruebas nuevas** (`tests/test_sky_v11_1_asistente.py`) y las **23 de dispositivos** existentes aprobadas. Las 4 de API se verificaron contra el router real con autenticación del dueño equivalente, porque el entorno de desarrollo no permitía instalar las dependencias pesadas de la app completa (trimesh, torch). El job "legacy engines" del workflow v11 ahora incluye estas pruebas: **confirmar el run de GitHub antes de declarar el pipeline verde**.
- El panel se probó en Chromium (escritorio y 390 px de ancho) contra el agente v5 real con acciones del sistema simuladas, sin errores de consola.
- Las acciones del sistema operativo (teclas multimedia, osascript, playerctl, PowerShell) **no se pudieron ejecutar en un escritorio real** durante esta revisión: probalas en tu Windows con `python agente_dispositivo.py --perfil completo`.
- Volumen exacto en Windows se aproxima con pulsaciones de 2 %. En macOS el control multimedia actúa sobre Spotify o Música. En Linux requiere `playerctl`, `pactl`/`amixer`, `notify-send` y `xclip`/`wl-clipboard` según la capacidad.
- "Reproducir en YouTube/Spotify" abre la búsqueda; elegir y reproducir automáticamente el primer resultado necesitaría las APIs de esos servicios.
- No incluido: control de Android/iOS, recordatorios programados, responder mensajes de WhatsApp/Telegram por vos, automatización de clics dentro de otras apps.
