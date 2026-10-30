# SKY Android — aislamiento de sesiones de escucha y voz

**Alcance:** exclusivamente `mobile/android-agent`. No altera SKY Windows, nube, permisos ni el modelo de lenguaje.

## Problema real corregido

Las llamadas `SpeechRecognizer.cancel()` y `destroy()` no garantizan que Android deje de enviar inmediatamente `onError` o `onResults` del reconocedor anterior. Antes, un callback tardío podía encontrar la variable global `listening=true` al iniciar un nuevo ciclo y modificar su estado, volver a cancelar el micrófono o despachar una transcripción equivocada.

`SkyRecognitionEpoch` invalida la generación anterior **antes** de cancelar el reconocedor. Cada listener conserva su identificador; únicamente el actual y activo puede modificar los estados y entregar resultados.

La voz sintetizada tiene un problema equivalente: un `TextToSpeech.onDone` de una respuesta ya reemplazada podía reactivar el micrófono mientras SKY seguía pronunciando otra frase. `SkySpeechTurnGuard` solo acepta el identificador vigente **una vez**. Las pausas externas anulan identificadores anteriores y el mecanismo de recuperación de 20 segundos sigue existiendo.

## Sueño y privacidad

- `SLEEP_LOCKED` continúa persistiendo mediante `SharedPreferences` y solo permite la frase explícita de despertar. Un «SKY» genérico, una confirmación o una orden de abrir apps no levantan el bloqueo.
- La interfaz ahora diferencia el sueño explícito de la simple espera.
- Una frase ambiental que termine en el nombre SKY no se considera autorización de ejecución. «Despierta SKY» sigue siendo una llamada válida.
- Ninguno de estos filtros verifica biométricamente al hablante; un impostor que diga la palabra de activación podría ser reconocido. Las acciones sensibles **deben seguir exigiendo** los permisos del sistema y consentimiento.
- El guardia de sesiones no almacena grabaciones ni transcripciones, y no utiliza servicios externos.

## Evidencia y límites

`SkyRecognitionEpochTest`, `SkySpeechTurnGuardTest` y la ampliación de `SkyWakePhraseTest` prueban callbacks tardíos, duplicados, pausas y frases ambientales. `SkyVoiceSessionRuntimeTest` valida en Android que el bloqueo se guarda y sigue negando órdenes al reabrir las preferencias.

El resultado requiere compilación estándar y pruebas en GitHub Actions, luego **comprobación física en Samsung**: pantalla encendida/apagada, cambio de actividades, sueño de 10 minutos, notificación del servicio, permiso de micrófono, batería y reconocimiento local disponible. Android puede detener la captura de audio a pesar de que la app tenga permiso y notificación. No declarar escucha 24/7, biometría o funcionamiento bajo bloqueo como certificados por tests unitarios.
