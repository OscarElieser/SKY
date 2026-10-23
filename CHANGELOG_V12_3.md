# SKY IA v12.3: los 7 pasos de un Jarvis personal, con WhatsApp

**Dirección conceptual:** Oscar Elieser Chamorro Guzmán.
Rama `sky-v12.3`, que parte de `sky-v12.2`. Se integra con un Pull Request revisado por el dueño.

| Paso | Qué agrega SKY v12.3 |
|---|---|
| 1. Una casa 24/7 | `INSTALAR_SKY_WINDOWS.bat -Siempre`: arranque con Windows, sin suspensión y supervisor que reinicia los servicios caídos (máx. 5 por hora; si sigue fallando, se detiene y lo marca en los KPIs). Guía en `docs/guias/SKY_CASA_24_7.md` |
| 2. Un cerebro | Ollama local, o **Claude, GPT, Gemini, Groq, DeepSeek o Mistral** |
| 3. Un arnés de herramientas | Las mismas ~24 herramientas validadas ahora funcionan también con los cerebros en la nube (`SKY_CEREBRO=nube` o el proveedor elegido en el HUD) |
| 4. Quién sos | **Perfil `USER.md`** (`~/.neuralt/USER.md`), editable en *Módulos → Perfil*. El cerebro y la IA lo leen en cada mensaje |
| 5. Conectar todo | **WhatsApp con la API oficial de Meta**: le escribís a SKY desde tu celular, con texto o notas de voz |
| 6. Skills | Carpeta `~/.neuralt/skills/`, 4 skills integradas y creación por voz |
| 7. Que trabaje sola | **Tareas programadas por voz** y en *Módulos → Automatización*: activar, pausar y borrar |

## WhatsApp (`neural_core/sky_whatsapp.py`, `sky_whatsapp_puente.py`)

- **Puente aislado** en `127.0.0.1:8770` con sólo `/whatsapp/webhook` y `/salud`. Es lo único que se publica (`tailscale funnel --bg 8770`); la API y el agente siguen privados.
- **Firma HMAC-SHA256 obligatoria** (`SKY_WA_APP_SECRET`). Sólo responde al número del dueño, con límite de 20 mensajes por minuto, sin duplicados y sin textos en los registros.
- **Confirmaciones:**
  - lo automático se ejecuta solo y lo demás pide «sí»;
  - el **nivel 3** pide «CONFIRMO 1234», con un código que vence a los 10 minutos;
  - las cerraduras sólo se abren desde el HUD;
  - la parada de emergencia funciona también desde WhatsApp.
- **Notas de voz** transcriptas en tu PC (faster-whisper).
- **Avisos** al WhatsApp: recordatorios, tareas programadas y problemas detectados.
  - Dentro de la ventana de 24 h de Meta, con texto libre.
  - Fuera de la ventana, sólo con tu plantilla aprobada (`SKY_WA_PLANTILLA`).
- **Costos de WhatsApp** (precios de Meta desde el 1/10/2026):
  - cada número tiene 1000 mensajes de servicio gratis por mes;
  - SKY cuenta lo que envía y avisa al llegar al 90 %.
- `python sky_whatsapp_puente.py --probar "…"` prueba la conversación sin Meta. También está la opción **W** en `SKY_INICIAR.bat`. Guía paso a paso: `docs/guias/SKY_WHATSAPP.md`.

## Skills y tareas programadas (`neural_core/sky_skills.py`)

- **Skills integradas:**
  - *Resumen del día*;
  - *Preparar respuestas de correo*;
  - *Novedades de mis temas*;
  - *Revisar rendimiento*.
- **Crear una skill por voz:** «crea una skill modo trabajo que abra Word, ponga lofi para estudiar y baje el volumen al 30». Cada parte se valida: si alguna no se entiende, la skill no se crea.
- **Programar por voz:**
  - «todos los días a las 8 prepara las respuestas de los correos»;
  - «de lunes a viernes a las 7:30 haz el resumen del día»;
  - «los sábados a las 10 de la mañana pon música relajante».

  Para gestionarlas: «qué tareas programadas tengo», «pausa / activa / borra la tarea…».
- **Pasos nuevos** para rutinas y skills: `orden`, `skill` (anidada, hasta 3 niveles), `correo_borradores`, `borradores_pendientes`, `noticias`, `aprender`, `intereses`, `kpi`. Si un paso falla, la skill no se detiene: se informa el error y sigue con el siguiente.

## Borradores de correo (`neural_core/sky_borradores.py`)

- A la hora programada, SKY lee los no leídos (sin marcarlos) y redacta respuestas breves. **Nunca las envía sola.**
- El correo recibido se pasa al modelo como datos, con la instrucción explícita de no seguir órdenes que contenga.
- Podés aprobarlas, editarlas o descartarlas en *Automatización*, con «envía el borrador 1» (confirmación en el HUD) o por WhatsApp con el código.

## Cerebro en la nube (`neural_core/sky_cerebro.py`)

- Se usan las APIs oficiales de Anthropic (Messages + tools), OpenAI y las compatibles (Groq, DeepSeek, Mistral) y Gemini (function calling).
- **`auto` nunca manda datos a la nube**: usar la nube es una decisión explícita (`SKY_CEREBRO` o el proveedor elegido en el HUD). `SKY_LOCAL_ONLY=1` lo impide siempre.
- **KPIs:**
  - tokens reales por proveedor;
  - costo estimado si definís `SKY_COSTO_<PROVEEDOR>_USD_1K`;
  - aviso al 80 % de `SKY_PRESUPUESTO_USD_MES`.

## Evidencia y límites

- **685 pruebas aprobadas, 0 fallidas** en el entorno de revisión. Hay 32 pruebas nuevas en `tests/test_sky_v12_3_jarvis_completo.py`, con todas las APIs externas simuladas, incluido el puente HTTP real con firma.
- Probado en Chromium contra la API real, en escritorio y celular:
  - programar por voz;
  - crear una skill;
  - el módulo Automatización;
  - editar y guardar el perfil;
  - sin errores de consola.
- **No probado contra Meta, Anthropic, OpenAI ni Gemini reales**: este entorno no tiene acceso a esas APIs ni a tus credenciales. Los formatos siguen la documentación oficial, pero la primera conexión real hay que verificarla siguiendo la guía.
- **WhatsApp exige:**
  - una app de Meta;
  - un número de WhatsApp Business (sirve el número de prueba que da Meta);
  - una dirección HTTPS pública para el puente.

  No existe una API oficial para usar tu WhatsApp personal como canal del bot.
- Las tareas programadas sólo corren mientras SKY está encendida (de ahí el paso 1).
