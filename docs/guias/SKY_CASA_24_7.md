# SKY 24/7: dónde vive SKY

SKY tiene dos partes:

- **El cerebro y la API** conversan, recuerdan, programan tareas, miden sus KPIs y reciben WhatsApp.
- **El agente del equipo** abre apps, controla la música, las ventanas y los archivos. Tiene que estar **en la computadora que controla**.

Por eso, la casa recomendada para SKY es **tu propia PC (o una mini PC) siempre encendida**.

## Opción A (recomendada): tu PC siempre lista

```
INSTALAR_SKY_WINDOWS.bat -Siempre
```

Esto hace tres cosas:

1. **Arranque automático:** SKY inicia sola al entrar a Windows, minimizada. Es lo mismo que la opción **8** de `SKY_INICIAR.bat`.
2. **Sin suspensión:** el equipo enchufado no se suspende ni hiberna. La pantalla sí puede apagarse.
3. **Supervisor:** si un servicio de SKY se cae (API, agente, voz, WhatsApp), lo reinicia solo, hasta 5 veces por hora. Si sigue fallando, lo deja detenido y lo marca en los KPIs (*reinicios*) para que lo revises, en lugar de reintentar sin fin.

Para que te llegue WhatsApp con la PC encendida y vos lejos:
- `tailscale funnel --bg 8770` queda activo aunque reinicies (ver [SKY_WHATSAPP.md](SKY_WHATSAPP.md));
- en Windows, **Configuración → Cuentas → Opciones de inicio de sesión**: si querés que SKY arranque sin que inicies sesión, configurá el inicio de sesión automático. Ojo: eso baja la seguridad física del equipo.

Para comprobar que está bien: botón **DIAG** del HUD, o `python sky_diagnostico.py`, y «mostrame tu rendimiento» (disponibilidad del agente y reinicios).

## Opción B: un servidor en la nube (sólo conversación)

En `deploy/` hay una referencia con Docker, Caddy (HTTPS) y Redis. **No está probada en un servidor real**: el propio archivo lo advierte, y requiere una revisión de seguridad antes de usarla. En la nube SKY puede:
- conversar con Claude, GPT o Gemini, recordar, avisarte y recibir WhatsApp;
- pero **no** puede abrir apps ni controlar tu PC, porque el agente vive en tu equipo.

Para eso, el agente de tu PC tendría que conectarse al servidor por Tailscale. Ese es el paso de la fase 9 (multidispositivo) de `docs/ESTADO_REAL_SKY.md`.

## Qué consume

Medido con los KPIs, en el panel Rendimiento → Equipo:
- **SKY sin modelo local:** unos 150 MB de RAM.
- **Ollama con `qwen2.5:7b`:** unos 5–6 GB de RAM o VRAM mientras está cargado. Se descarga solo tras 30 minutos sin uso.
- **Una mini PC con 16 GB de RAM** alcanza para todo.
