# SKY IA v11.1 — Asistente Personal · Inicio

SKY es tu asistente personal: le hablás o le escribís en español y abre tus apps, pone tu música, maneja el volumen, busca en la web, abre tus documentos, toma capturas y bloquea el equipo. **Vos decidís qué puede hacer**, en tu propia PC.

## 1. Arrancar (Windows)

Doble clic en `SKY_INICIAR.bat` → opción **0 · ASISTENTE PERSONAL SKY**. Esto:

1. Crea el entorno e instala dependencias la primera vez.
2. Activa el perfil **multimedia** si nunca elegiste uno.
3. Inicia el agente del equipo (puerto 8766) y la API (puerto 8765).
4. Abre el panel: **http://127.0.0.1:8765/asistente**

En Linux/macOS: `./iniciar_sky_asistente_linux_mac.sh`.

## 2. Elegir qué controla SKY

| Perfil | Qué puede hacer | Sin pedir clic |
|---|---|---|
| `basico` | Estado, abrir webs, calculadora/editor/archivos/navegador | nada |
| `multimedia` | + 17 apps, música/video, volumen, Spotify/YouTube, notificaciones | estado, multimedia, volumen, reproducir, avisos |
| `completo` | + archivos en tus carpetas, capturas, portapapeles, bloqueo | lo anterior + abrir webs/apps y bloquear |

```bash
python agente_dispositivo.py --perfil completo --carpeta "C:\Users\Oscar\Music" --carpeta "C:\Users\Oscar\Documents"
python agente_dispositivo.py --activar clipboard           # una capacidad suelta
python agente_dispositivo.py --auto launch_app             # que no pida clic para esto
python agente_dispositivo.py --desactivar screenshot
python agente_dispositivo.py --ver-politica
```

O desde el menú `SKY_INICIAR.bat` → opción **9**. Reiniciá el agente después de cambiar la política para verla reflejada en el panel.

### Tus propias apps

Editá `~/.neuralt/device_agent_policy.json` y agregá en `custom_apps` (requiere la capacidad `apps_extra`):

```json
"custom_apps": {
  "obs": {"windows": ["C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe"], "linux": ["obs"]},
  "capcut": {"windows": ["C:\\Users\\Oscar\\AppData\\Local\\CapCut\\Apps\\CapCut.exe"]}
}
```

Se abren desde el panel con la acción `launch_app` y `{"app": "obs"}`.

## 3. Qué le podés decir

- **Música y video:** "reproduce Bad Bunny en Spotify", "pon lofi para estudiar", "quiero ver Stranger Things en YouTube", "pausa la música", "siguiente canción", "canción anterior"
- **Volumen:** "sube el volumen", "baja el volumen", "volumen al 30", "silencia"
- **Apps:** "abre Spotify / Word / Excel / WhatsApp / Telegram / VS Code / la cámara / la configuración / la calculadora"
- **Web:** "abre YouTube", "busca recetas de gallo pinto en Google", "busca en mapas León Nicaragua"
- **Archivos:** "abre mis documentos", "qué hay en mis descargas"
- **Equipo:** "toma una captura", "bloquea la pantalla", "copia hola mundo al portapapeles", "qué hay en el portapapeles", "avísame que tengo reunión a las 3", "estado de mi computadora"
- **Cualquier otra cosa** la responde la IA que configuraste en `.env` (Gemini, Claude, GPT, Mistral, Groq, DeepSeek u Ollama).

En el panel, el botón 🎙️ dicta por voz (Chrome o Edge) y la casilla **voz** lee las respuestas.

## 4. Manos libres con "SKY…"

```bash
pip install vosk sounddevice pyttsx3
python sky_manos_libres.py --model ruta/al/modelo-vosk-es
```

Decí "SKY, sube el volumen". Lo que marcaste como automático se ejecuta al instante; el resto aparece en **Pendientes de voz** del panel para confirmar.

## 5. Desde el celular u otra PC

Instalá Tailscale en ambos equipos. En la PC con el agente: `tailscale serve 8766`. Emparejá esa dirección HTTPS en Streamlit ("🎙️ SKY y dispositivos"); en el panel del asistente elegí el dispositivo en el selector y pegá su token cuando lo pida (queda sólo en esa pestaña). No uses Tailscale Funnel ni abras puertos públicos.

## 6. Seguridad

SKY nunca ejecuta comandos de shell, nunca abre programas ni scripts, nunca sale de las carpetas que autorizaste, nunca descarga ni instala nada y nunca paga. La política sólo se cambia en tu PC. Todo queda registrado en `~/.neuralt/device_agent_audit.jsonl`. Detalle técnico: `CHANGELOG_V11_1.md` y `docs/api/SKY_ASISTENTE_PERSONAL_API.md`.

## 7. Pruebas

```bash
PYTHONPATH=. pytest -q tests/test_sky_v11_1_asistente.py tests/test_sky_devices.py
```
