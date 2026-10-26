# SKY — captura continua, respuestas e interrupción por voz

El servicio independiente `sky_manos_libres.py` conserva activo el reconocimiento Vosk mientras el trabajador serial procesa Ollama, el agente Windows y la síntesis local. No depende de que el HUD o Streamlit estén abiertos.

## Modo de funcionamiento

- **Escucha natural:** disponible únicamente si el dueño habilita `SKY_VOICE_ALWAYS_LISTEN=1` en su `.env` local. Si no, SKY exige la palabra de activación.
- **Consulta larga:** el micrófono continúa leyendo audio y acepta hasta **dos solicitudes pendientes** para atenderlas en orden. No se ejecutan comandos simultáneos. Si la cola está llena, SKY informa en consola que hay que repetir la solicitud.
- **Cuando SKY habla:** el micrófono continúa leyendo, pero para proteger contra el eco del propio altavoz no ejecuta comandos detectados durante TTS. Para interrumpir, decí «SKY, cállate», «SKY, silencio» o «SKY, dejá de hablar». También podés decir «SKY, ...» para pedir que se calle; **repetí la instrucción cuando termine el audio**. No se ejecuta automáticamente el texto recogido durante TTS.
- **Síntesis:** `pyttsx3` se inicializa y usa en un único hilo. La cancelación se consulta en eventos por palabra, cuando el motor los soporte, y entre frases; no se realizan llamadas COM desde el hilo del micrófono. La interrupción puede tardar algo según el motor.
- **Texto:** el chat del HUD/API sigue siendo independiente del micrófono y no necesita que el servicio de voz esté disponible.

## Iniciar

Desde la carpeta SKY, actualizá `main` sin sobrescribir cambios locales y usá `SKY_INICIAR.bat` opción **0**. La opción **8** habilita arranque al iniciar sesión en Windows (requiere que Windows esté despierto y el micrófono habilitado).

## Verificar

```powershell
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --status
.\.venv\Scripts\python.exe -m pytest -q tests/test_sky_voice_queue.py tests/test_sky_listening_status.py
```

Pruebas manuales: preguntar algo largo y hablar otra vez antes de que termine; verificar que la nueva solicitud se atiende después de la anterior. Mientras SKY habla, probar «SKY, silencio» y repetir luego una instrucción simple. Verificar que el audio de SKY **no ejecuta por sí solo órdenes**. Probar «SKY, abrí Word» con la autorización del agente habilitada y con la parada de emergencia activada.

## Limitaciones reales

No existe supresión acústica completa del eco: unos audífonos con micrófono ayudan. Durante el TTS sólo se aceptan interrupciones seguras; las demás frases deben repetirse. Cuando el modelo no permite cancelación HTTP, una consulta que ya está calculándose puede continuar hasta terminar, aunque el micrófono siga capturando nuevas intervenciones. La disponibilidad 24/7 no está garantizada ante suspensión del PC, fallo del dispositivo, saturación ni cierre del supervisor.
