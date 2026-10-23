# SKY IA v12.3 — Inicio

## 1. Instalar (una sola vez)

Doble clic en **`INSTALAR_SKY_WINDOWS.bat`**. Deja todo listo: Python, librerías, **Ollama** con el modelo del cerebro, la **voz natural Piper** en español, la **escucha local** (faster-whisper), el modelo **Vosk** para manos libres, los permisos y `.env`. Si algo falla, volvé a ejecutarlo: salta lo que ya está instalado.

- `INSTALAR_SKY_WINDOWS.bat -Local` → modo 100 % local (nada sale del equipo).
- `INSTALAR_SKY_WINDOWS.bat -Modelo qwen2.5:7b` → elegir el modelo.
- `INSTALAR_SKY_WINDOWS.bat -Siempre` → SKY 24/7: arranca con Windows, el equipo no se suspende y los servicios se reinician solos.

## 2. Arrancar

`SKY_INICIAR.bat` → **0 · SKY COMPLETO**. Se abre la interfaz en **http://127.0.0.1:8765/**.

¿Algo no anda? Botón **DIAG** del HUD, opción **7** del menú o `python sky_diagnostico.py`: te dice qué falta y el comando para arreglarlo.

## 3. Hablar con SKY

| Botón | Qué hace |
|---|---|
| Núcleo / **MIC** / barra espaciadora / F2 | Hablar una vez |
| **SKY** | Escucha continua: decí "SKY, …" cuando quieras, sin tocar nada |
| **CONV** | Después de responder, SKY te vuelve a escuchar |
| **VOZ** | SKY responde en voz alta (Piper si está instalado) |
| Esc | Cortar la voz o la escucha |

SKY empieza a hablar con la primera frase de la respuesta. Si te pregunta "¿Lo hago?", respondé "sí" o "no".

**Podés hablarle con naturalidad.** Las órdenes conocidas se resuelven al instante, y las demás las interpreta el cerebro local: "está muy fuerte esto", "me aburrí de esta canción", "quiero algo relajante de fondo", "cerralo".

Ejemplos:
- **Música y video:** "reproduce Bad Bunny en Spotify" · "pon el video en pantalla completa" · "siguiente"
- **Equipo:** "abre Word" · "organiza las ventanas" · "abre mis documentos" · "toma una captura" · "bloquea la pantalla"
- **Agenda:** "recuérdame en 10 minutos sacar la ropa" · "pon una alarma a las 6:30" · "qué recordatorios tengo" · "buenos días"
- **Notas y tareas:** "crea una nota agenda que diga reunión el lunes" · "prepara una presentación sobre energía solar"
- **Mensajes:** "lee mis correos" · "responde al último correo diciendo gracias, lo reviso hoy" · "mándale un whatsapp a mamá que llego tarde"
- **Casa:** "enciende la luz de la sala" · "activa la escena cine"
- **Aprender:** "aprende sobre energía solar" · "sigue el tema Real Madrid" · "recuerda que mi equipo es el Real Madrid" · "qué sabes de mí" · "cuando diga modo cine, pon el video en pantalla completa" · "no, eso no era"
- **Rendimiento:** "mostrame tu rendimiento de hoy, cuántas tareas completaste y cuáles fallaron" · "analizá tu rendimiento y decime qué está fallando" · "cerrá el panel"
- **Skills y tareas:** "crea una skill modo trabajo que abra Word y ponga lofi para estudiar" · "todos los días a las 8 prepara las respuestas de los correos" · "qué tareas programadas tengo" · "qué borradores tengo"
- **Perfil:** "muéstrame mi perfil" (escribí quién sos, tus herramientas y suscripciones)
- **Emergencia:** "SKY, para todo" detiene toda acción al instante; para reanudar tocá **Reanudar** en la tarjeta.

## 4. Permisos

| Perfil | Qué hace | Sin pedir clic |
|---|---|---|
| `basico` | apps, música, volumen, webs, avisos, tareas | estado, música, volumen |
| `multimedia` | lo mismo | todo lo anterior |
| `completo` | + ventanas, carpetas y documentos, notas, escribir texto, capturas, portapapeles, bloqueo | lo de multimedia + bloquear |

Ventanas, archivos, notas, escritura, portapapeles, correos y cerraduras **siempre** piden confirmación. Para cambiar el perfil: opción **6** del menú.

## 5. Correo, WhatsApp y contactos

- **Correo:** en `.env` poné `SKY_MAIL_USER` y `SKY_MAIL_APP_PASSWORD`. Es una *contraseña de aplicación*, no tu contraseña real; en Gmail se crea en myaccount.google.com/apppasswords con la verificación en dos pasos activada. SKY lee sin marcar como leído y **nunca envía sin tu confirmación**.
- **Contactos:** copiá `docs/ejemplos/contactos.json` a `C:\Users\TU_USUARIO\.neuralt\contactos.json` y completalo.
- **WhatsApp:** SKY abre WhatsApp con el mensaje escrito; vos tocás Enviar.

## 6. Casa y celular (Home Assistant)

En Home Assistant: Perfil → Seguridad → **Tokens de acceso de larga duración**. En `.env`:

```
SKY_HA_URL=http://homeassistant.local:8123
SKY_HA_TOKEN=el_token
SKY_HA_NOTIFY=notify.mobile_app_tu_telefono   # avisos de SKY en tu celular
```

## 7. Rutinas

"Buenos días" ya viene configurada (saludo, recordatorios del día y correos nuevos). Para crear las tuyas, con hora y días, usá `POST /api/hud/rutinas` (ver `docs/api/SKY_ASISTENTE_PERSONAL_API.md`).

## 8. Reproductor de YouTube dentro de SKY

Poné `YOUTUBE_API_KEY=` (YouTube Data API v3) en `.env`. Sin clave, SKY abre la búsqueda en tu navegador.

## 9. Intérprete de código

`SKY_INICIAR.bat` → **I**. SKY escribe código para lo que le pidas y **muestra cada bloque antes de ejecutarlo**; respondé `y` para ejecutarlo o `n` para saltarlo.

## 10. Desde el celular

Con Tailscale en la PC y el celular:
1. En la PC: `tailscale serve 8765`.
2. Agregá ese nombre (por ejemplo `mi-pc.mi-red.ts.net`) a `SKY_TRUSTED_HOSTS` en `.env`.
3. Abrí la dirección HTTPS en el celular. Si te pide la llave del dueño, está en `local_data/sky_api_token.txt`.

No uses Funnel ni abras puertos públicos.

## 11. Aprendizaje y KPIs

- SKY aprende sola: cuando entiende una frase nueva con el cerebro y la acción sale bien, la próxima vez la hace al instante. Lo que aprendió se ve (y se puede olvidar) en **Módulos → Rendimiento**.
- Con internet, "aprende sobre…" lee Wikipedia y noticias y lo guarda en tu PC con la fuente. `SKY_INTERNET=0` en `.env` lo apaga.
- Todo lo que sabe de vos se exporta con `GET /api/hud/memoria`. Nunca guarda contraseñas ni datos de tarjetas.
- Los KPIs son mediciones reales guardadas en `~/.neuralt/sky_metricas.sqlite3`. Los objetivos (`SKY_SLO_*`) se cambian en `.env`. SKY te avisa una vez por día si detecta un problema.
- Qué funciona de verdad y qué falta: `docs/ESTADO_REAL_SKY.md`.

## 12. WhatsApp, skills y cerebro en la nube

- **WhatsApp:** seguí `docs/guias/SKY_WHATSAPP.md` (app de Meta, 5 valores en `.env`, `tailscale funnel --bg 8770`). Opción **W** del menú.
- **Skills:** archivos en `C:\Users\TU_USUARIO\.neuralt\skills\`, o creadas por voz. Se ven en **Módulos → Automatización**.
- **Cerebro en la nube:** `SKY_CEREBRO=nube` (o `anthropic`, `openai`, `gemini`) en `.env`, con su clave. Por defecto SKY usa Ollama y nada sale del equipo.

## 13. Recomendación de equipo

Para que el cerebro local sea rápido: tarjeta NVIDIA de 8 GB o más y 16 GB de RAM, con `qwen2.5:7b`. Con 30 GB de RAM o más el instalador elige `qwen2.5:14b` (más inteligente). Sin tarjeta gráfica también funciona, pero más lento; con poca memoria elige `qwen2.5:3b`.
