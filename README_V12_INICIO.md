# SKY IA v12 — Inicio

## 1. Arrancar

**Windows:** doble clic en `SKY_INICIAR.bat` → **0 · SKY COMPLETO**. Se inician el agente del equipo, la API, la voz manos libres (si tenés el modelo Vosk) y se abre la interfaz: **http://127.0.0.1:8765/**

**Linux / macOS:** `./iniciar_sky_asistente_linux_mac.sh`

La primera vez se activa el perfil **multimedia**. Cambialo con la opción **6** del menú.

## 2. Hablar con SKY

- Tocá el **núcleo**, el botón **MIC**, la **barra espaciadora** o **F2** y hablá.
- **CONV**: conversación continua (SKY te vuelve a escuchar después de responder).
- **VOZ**: SKY responde en voz alta.
- Si SKY pregunta "¿Lo hago?", respondé "sí" o "no".
- Esc corta la voz o la escucha.

Ejemplos: "reproduce Bad Bunny en Spotify" · "pon el video en pantalla completa" · "sube el volumen" · "abre Word" · "organiza las ventanas" · "abre mis documentos" · "crea una nota agenda que diga reunión el lunes" · "prepara una presentación sobre energía solar" · "enciende la luz de la sala" · "toma una captura" · "bloquea la pantalla" · y cualquier pregunta.

## 3. 100 % local

1. Instalá Ollama y descargá un modelo: `ollama pull llama3.1`
2. En `.env`: `SKY_LOCAL_ONLY=1` y `OLLAMA_MODEL=llama3.1`
3. Voz local: `pip install faster-whisper`, descargá un modelo de faster-whisper a una carpeta y poné `SKY_STT_MODEL_DIR=esa\carpeta`.

El HUD muestra **IA · LOCAL** y **VOZ · LOCAL** cuando está todo en tu equipo.

## 4. Permisos

| Perfil | Qué hace | Sin pedir clic |
|---|---|---|
| `basico` | apps, música, volumen, webs, avisos, tareas | estado, música, volumen |
| `multimedia` | lo mismo | todo lo anterior + abrir apps/webs, reproducir, avisos, tareas |
| `completo` | + ventanas, carpetas y documentos, notas, escribir texto, capturas, portapapeles, bloqueo | lo de multimedia + bloquear |

Ventanas, archivos, notas, escritura y portapapeles **siempre** piden confirmación. Detalle: `python agente_dispositivo.py --help`.

## 5. Casa (Home Assistant)

En Home Assistant: Perfil → Seguridad → **Tokens de acceso de larga duración**. En `.env`:

```
SKY_HA_URL=http://homeassistant.local:8123
SKY_HA_TOKEN=el_token
```

Reiniciá SKY. El panel **Casa** muestra tus luces, enchufes y escenas.

## 6. Reproductor de YouTube dentro de SKY

Creá una clave de **YouTube Data API v3** en Google Cloud y poné `YOUTUBE_API_KEY=` en `.env`. Sin clave, SKY abre la búsqueda en tu navegador.

## 7. Intérprete de código

`SKY_INICIAR.bat` → **I**, o `python sky_interprete.py`. SKY escribe código para lo que le pidas y **te muestra cada bloque antes de ejecutarlo** (respondé `y` o `n`).

## 8. Desde el celular

Con Tailscale en la PC y el celular: `tailscale serve 8765` en la PC, agregá ese nombre (por ejemplo `mi-pc.mi-red.ts.net`) a `SKY_TRUSTED_HOSTS` en `.env` y abrí la dirección HTTPS en el celular. Si te pide la llave del dueño, está en `local_data/sky_api_token.txt`. No uses Funnel ni abras puertos públicos.
