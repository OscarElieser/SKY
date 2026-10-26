# SKY — escucha persistente y chat escrito (Windows)

SKY utiliza un supervisor independiente del HUD que inicia:
- API de texto en `127.0.0.1:8765`;
- agente autorizado en `127.0.0.1:8766`;
- escucha Vosk local (`sky_manos_libres.py`), si existe el modelo.

La API y el micrófono no requieren que Streamlit ni una pestaña del navegador permanezcan abiertos. El chat escrito funciona cuando la API está iniciada y autenticada.

## Activar conversación natural, por decisión del propietario

En el `.env` **local** del equipo (no subir secretos al repositorio), añadir una sola vez:

```dotenv
SKY_VOICE_ALWAYS_LISTEN=1
```

Reiniciar SKY mediante `SKY_INICIAR.bat` > **0 — SKY COMPLETO**.
En este modo, Vosk admite preguntas o instrucciones dirigidas directamente a SKY sin palabra de activación, con continuidad de conversación. No interpreta automáticamente cualquier charla ambiental como una orden, y no omite la autorización del agente. Para exigir otra vez la palabra «SKY», poner `SKY_VOICE_ALWAYS_LISTEN=0` y reiniciar el supervisor.

La escucha natural del servicio Windows es independiente del modo de entrada del HUD: escribir en el chat no necesita apagar el micrófono. Si elegís un modo exclusivamente texto o pausás voz de forma explícita, SKY respeta esa decisión.

## Iniciar automáticamente después de iniciar sesión en Windows

En `SKY_INICIAR.bat`, opción **8 — Iniciar automáticamente con Windows**. El acceso directo creado ejecuta `iniciar_sky_autonomo.py --minimized`: abre los procesos sin exigir la pestaña web. Para desactivar:

```powershell
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --uninstall-startup
```

El inicio automático se realiza después de iniciar sesión en Windows; no puede escuchar si la PC está apagada, suspendida, bloqueada sin acceso al hardware o si el micrófono fue deshabilitado.

## Verificación de funcionamiento real

```powershell
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --status
```

Revisar las propiedades:
- `voice.escucha_continua`: **true** sólo si el consumidor de audio registra actividad reciente.
- `voice.microfono_recibiendo_audio`: captura de tramas reciente, no calidad o transcripción garantizadas.
- `voice.escucha_natural_sin_sky`: modo natural actualmente habilitado.
- `chat_texto.disponible`: API de texto accesible por `/api/health`.
- `voice.active`: sesión conversacional actual, distinta del estado del micrófono.

Si el proceso de voz se cierra, el supervisor intenta reiniciarlo, con límite de cinco reintentos por hora. Si `voice.escucha_continua` es falso, revisar el micrófono y los registros de consola. No presentar archivos de estado antiguos como una escucha real.

SKY no necesita subir audio a servicios externos para Vosk. Consultas de IA pueden ir a proveedores configurados por el dueño. Las acciones de dispositivo conservan las confirmaciones y la parada de emergencia.
