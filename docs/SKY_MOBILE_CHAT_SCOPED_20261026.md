# SKY Mobile Chat — sesión independiente de texto para Android

## Alcance real
Este hito amplía el Android Agent Kotlin **existente** (no crea otra SKY).
El propietario, autenticado en la API SKY y con MFA si está activo, puede
emitir un código de chat para un dispositivo Android **ya emparejado**.
Android canjea ese código junto con su token de agente por un token
**independiente**, limitado a texto y válido **24 horas**.

- Se conserva la API SKY: los endpoints antiguos y el agente Windows no cambian.
- Este chat invoca únicamente el motor de texto de SKY Home, sin acciones, archivos
  o exportación automática de memoria. No habilita acceso de propietario.
- El token de agente nunca puede usarse como token de chat.
- El token de chat nunca puede autorizar órdenes al agente, emparejamiento,
  acciones Windows ni rutas del propietario.
- Ambos tokens se guardan cifrados en Android Keystore (AES-GCM);
  el servidor almacena hashes SHA-256, nunca tokens en claro.
- El código de autorización dura 5 minutos, es de un solo uso y queda ligado
  a un teléfono concreto. Reemitir sesión revoca las anteriores.
- Máximo 12 solicitudes de chat por minuto, por token; la revocación del
  Android Agent también bloquea su chat.
- Texto del chat solo en memoria temporal en Android (máximo 8 entradas).
  El módulo de sesión **no** guarda mensajes ni historiales en SQLite.
  La API/los proveedores existentes pueden tener telemetría independiente:
  revisar su política antes de enviar datos confidenciales.
- En la app, cada mensaje se clasifica como privado y las casillas de envío a
  la nube y autorización de datos privados **se desmarcan después de enviar**.
  El historial de esa conversación se comparte solamente cuando ambas
  autorizaciones están activas, y el cliente lo indica expresamente.
  La clasificación del texto no detecta automáticamente secretos: el usuario
  debe revisar el contenido antes de autorizar un proveedor remoto.
- Sin internet, el servidor puede usar Ollama local si está instalado y activo.
  El teléfono **no** puede hablar remotamente con la PC de casa cuando se cae
  su conexión; no se afirma que exista chat Android autónomo sin conexión.

## Pasos para las pruebas autorizadas

1. Iniciar SKY en la PC de casa con la API atada a 127.0.0.1:8765,
   usando conexión HTTPS privada dentro de una red Tailscale. No usar
   port forwarding público ni Tailscale Funnel para la API SKY.
2. Emparejar el teléfono con el Android Agent existente usando el HUD y
   el código temporal habitual. No trasladar SKY_API_KEY al teléfono.
3. Consultar el ID del dispositivo desde el propietario:
   GET /api/sky/mobile-agent/devices (X-SKY-KEY + X-SKY-SESSION si exige MFA).
4. Desde un cliente API **en el equipo del propietario**, solicitar:
   POST /api/sky/mobile-chat/invite
   cuerpo JSON: {"device_id":"ID_DE_32_HEX"}
   con X-SKY-KEY y, si corresponde, X-SKY-SESSION.
   La respuesta muestra un código temporal; no se pega en repositorios,
   capturas públicas ni registros.
5. En Android abrir **SKY CHAT**, introducir únicamente ese código en
   “Código temporal de chat autorizado por el dueño” y pulsar
   “Activar chat por 24 horas”. La app canjea el código por un token
   cifrado y no solicita la clave principal.
6. Escribir en “Escribí a SKY…” y pulsar “Enviar mensaje a SKY”.
   Sin autorización de nube, el servidor utiliza el modelo local si
   existe; si no existe, devuelve HTTP 409 sin fingir una respuesta.
7. Para una consulta remota, leer primero el contenido, autorizar la nube
   y por separado la transmisión de datos privados de ese **mensaje e historial**.
   Las casillas vuelven a falso para la próxima consulta.
8. Revocar chat independientemente con POST /api/sky/mobile-chat/revoke
   como propietario, cuerpo {"device_id":"ID_DE_32_HEX"}, o revocar
   el Android Agent y comprobar que el chat deja de funcionar.

## Contrato específico

Rutas propietarias: require_key y MFA existente:
- POST /api/sky/mobile-chat/invite
- POST /api/sky/mobile-chat/revoke

Rutas de dispositivo:
- POST /api/sky/mobile-chat/pair: código temporal, device_id,
  encabezado X-SKY-MOBILE-TOKEN (agente emparejado).
- POST /api/sky/mobile-chat/chat: device_id, texto, historial,
  proveedor, datos, autorizar_nube, autorizar_datos_privados;
  encabezado X-SKY-CHAT-TOKEN (credencial diferente).

El chat reutiliza HomeChat (longitud de texto <=4000, historial <=8,
proveedor explícito y controles de nube); no instala agentes nuevos.
Las sesiones se revocan también cuando se revoca el agente Android.

## Validación y límites

Pruebas automáticas: credenciales separadas, uso único, caducidad,
renovación, bloqueo tras revocación, límite por minuto, rechazo sin sesión
antes de invocar IA, compilación Android debug. Estos resultados solo validan
el código en los entornos CI. Las pruebas en Android físico, Wi-Fi/datos,
reconexión, HTTPS/Tailscale, latencia, audio, estabilidad 24/7 y consumo RAM
de la PC i3/8GB deben hacerse en los equipos reales.

**Todavía NO incluye** dictado ni respuestas habladas Android, control de apps
mediante el chat, sincronización de historial entre dispositivos, permisos
de teléfono en segundo plano, push notifications, biometría o iOS.
