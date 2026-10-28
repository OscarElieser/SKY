# SKY Mobile Agent (Android) — primer hito operativo

Módulo nativo Kotlin dentro del proyecto SKY existente. Reutiliza la API FastAPI y
el HUD; no duplica el cerebro, la memoria, SENTINEL ni el agente de Windows.

## Primera función

La persona propietaria puede pedir por texto o voz en SKY: «SKY, abrí YouTube
en mi teléfono» (también Chrome, WhatsApp y Gmail). Solo cuando hay un
Android emparejado, SKY deposita una orden de apertura en una cola privada.
La app nativa consulta esa cola mientras está VISIBLE, muestra un diálogo
local y únicamente entonces solicita a Android que abra la app autorizada.

Es necesaria **doble aprobación**: habilitar previamente cada app y confirmar
la orden con «Permitir una vez». Ninguna aplicación se abre automáticamente
en segundo plano, y no se lee pantalla, mensajes ni contactos.

**SENT no significa VERIFIED:** confirma que Android aceptó la solicitud de
apertura; no demuestra que la aplicación terminara de cargar.

## Instalación para pruebas de desarrollo

1. Abrí la carpeta mobile/android-agent como proyecto en Android Studio.
2. Utilizá JDK 17, Android SDK 35, Android Gradle Plugin 8.9.2 y Gradle 8.11.1.
3. Sincronizá y compilá la configuración app. Instalá la compilación debug solo
   en un teléfono Android tuyo o expresamente autorizado (Android 8+).
4. Iniciá SKY CORE en tu PC. Configurá un canal privado HTTPS válido, por ejemplo
   mediante Tailscale Serve y Tailscale en ambos equipos. No expongas el puerto
   FastAPI de SKY públicamente sin autenticación y protección de red.
5. En el HUD de SKY abrí el panel SKY Teléfono, buscá SKY Mobile Agent y elegí
   «Crear código para Android». Este código vence a los cinco minutos.
6. En la app Android ingresá la URL privada HTTPS de SKY, un nombre de
   dispositivo y el código. Tocá «Vincular teléfono».
7. Marcá «Permitir YouTube» en Android. En el HUD, enviá la orden o decí
   «SKY, abrí YouTube en mi teléfono». Confirmá «Permitir una vez» en Android.
8. Podés consultar el estado final en el panel. «Revocar acceso» invalida el
   token en el servidor. La revocación desde Android necesita conexión.

## Conectividad y seguridad

- El dueño se autentica con la clave original de SKY y su MFA si está activo.
- Para emparejar, SKY genera un código aleatorio de uso único con TTL de 300 s.
- El teléfono recibe un token diferente al del dueño, exclusivo para su ID.
- El token se cifra en el dispositivo mediante Android Keystore; el servidor
  conserva solamente SHA-256 del token.
- Sin privilegios root, servicios de accesibilidad, QUERY_ALL_PACKAGES,
  escucha oculta, SMS automático, shell ni permisos peligrosos.
- El servidor limita a 10 órdenes por minuto por teléfono, expira solicitudes
  a los 120 s y conserva el resultado (PENDING, CLAIMED, SENT, FAILED,
  REJECTED, EXPIRED o REVOKED).
- El teléfono no acepta comandos arbitrarios: lista blanca fija.
- La versión inicial hace consultas cada seis segundos solo con el
  Activity visible. No está diseñada para ejecución constante con pantalla
  apagada ni para iniciarse automáticamente tras un reinicio.

## Consultar el servidor doméstico

Desde la pantalla del agente Android, tocá **Estado de mi servidor SKY**.
La app consulta `GET /api/sky/mobile-agent/devices/{id}/home-status` sobre HTTPS,
con el token **del dispositivo** guardado en Android Keystore, no con la
clave maestra del propietario. Devuelve únicamente si el servidor responde,
si está disponible un modelo Ollama local y si hay proveedores remotos
configurados, sin revelar secretos, conversaciones ni datos personales.
Un teléfono no emparejado o revocado recibe HTTP 401. Esta comprobación no
consume órdenes pendientes ni concede capacidades de chat, memoria o control
del equipo de Windows. La app necesita estar visible para efectuar la consulta.

Esto es un primer avance de la app móvil: el chat Android completo y
las sesiones móviles con permisos granulares permanecen pendientes.

## API reutilizada

Endpoints protegidos por autenticación de propietario (y MFA):
- POST /api/sky/mobile-agent/pair/start
- GET /api/sky/mobile-agent/devices
- POST /api/sky/mobile-agent/devices/{id}/commands
- GET /api/sky/mobile-agent/devices/{id}/commands/{command_id}
- DELETE /api/sky/mobile-agent/devices/{id}

Endpoints para Android, con código efímero o token de dispositivo:
- POST /api/sky/mobile-agent/pair/complete
- GET /api/sky/mobile-agent/devices/{id}/next
- POST /api/sky/mobile-agent/devices/{id}/commands/{command_id}/complete
- POST /api/sky/mobile-agent/devices/{id}/revoke-self

El Android envía su token como cabecera X-SKY-MOBILE-TOKEN. La clave maestra
SKY_API_KEY no debe copiarse al teléfono.

## Por validar y ampliar

Compilación en CI, instalación y pruebas físicas en teléfono Android, firma
de APK, reconexión, incidencias por suspensión del sistema, experiencia
holográfica Flutter y notificaciones para órdenes pendientes cuando la app
no está abierta. Android limita lanzamientos de apps y servicios en segundo
plano: no se debe prometer control continuo incondicional.

## Ojo animado y conversación hablada (en desarrollo, rama main)

La interfaz nativa incluye un ojo que cambia de estado (en espera, escucha,
procesamiento, respuesta y error), un botón **Hablar con SKY**, un botón
**Detener** y la opción **SKY responde con voz**. El reconocimiento usa
`SpeechRecognizer` y la lectura de respuestas usa el motor Android
`TextToSpeech` disponible en el teléfono. Se conecta al mismo endpoint de
chat `/api/sky/mobile-chat/chat`: no reemplaza la autenticación ni la
memoria existente del servidor.

Para probar: vincular primero el agente con HTTPS privado; activar el chat
autorizado por el propietario con su código temporal; tocar **Hablar con SKY**,
autorizar el micrófono y dictar una pregunta. El texto reconocido pasa al
chat y, cuando llega una respuesta, SKY la lee en voz alta si la casilla está
activada. El usuario puede detener la salida de voz.

**Límites**: no hay palabra de activación permanente, ni escucha cuando
la app no está visible, ni voz neuronal propia. El reconocimiento y la calidad
de las voces dependen del servicio configurado en Android y pueden requerir
internet; la aplicación no controla cómo procesa audio ese proveedor. El
chat sigue sujeto a autorización independiente y los permisos existentes.
La APK de CI requiere aún pruebas físicas de micrófono, audio, idioma,
tiempos de respuesta y ciclo de vida. No se garantiza una experiencia Alexa
completa con este primer incremento.

## SKY expresiva: dos ojitos amigables

La interfaz del chat de voz usa SkyFriendlyEyesView.kt, con dos ojos grandes
y redondeados, cejas, sonrisa, mejillas de colores pastel y animaciones
dibujadas directamente en Android. No utiliza ojos realistas ni estética
de terror.

- Parpadeo periódico, mirada móvil y movimientos suaves.
- Escucha: pupilas atentas; procesamiento: mirada curiosa y burbujas;
  habla: sonrisa animada y destellos; error: duda suave, sin agresividad.
- Al tocar los ojos rota por alegría, curiosidad, sorpresa, cariño,
  sueño y calma; las expresiones regresan al modo normal automáticamente.
- Los saludos, agradecimientos y frases afectuosas activan gestos amables.
- La respuesta hablada utiliza el TTS de Android, si está habilitado.

La animación no requiere micrófono ni conexión; la conversación sigue
dependiendo del reconocimiento, la autorización del chat y la API SKY.
Esta versión no agrega escucha permanente ni permisos invasivos.
