# SKY Teléfono — llamadas, SMS, videoconferencias y control de números

**SKY IA** (OscarElieser/SKY). Integración incremental que preserva SKY CORE,
API existente, HUD holográfico, SKY Docente, memoria, control Windows y Android,
SENTINEL, voz y demás servicios.

## Lo que se implementó (código, sin configurar ni usar cuentas reales)

- `neural_core/sky_phone.py`: validación de números internacionales E.164,
  verificación del número propietario por SMS con Twilio Verify,
  SMS salientes mediante Programmable Messaging y llamadas mediante Twilio Voice.
- **Una llamada telefónica no sale del micrófono del HUD**. Twilio llama
  PRIMERO al número personal previamente verificado; al contestar conecta
  al destinatario. Son dos tramos de telefonía convencional y pueden generar
  dos costos. No graba llamadas.
- Videoconferencia **dentro del panel SKY** con Jitsi Meet External API cargado
  solamente después de pulsar Entrar. La sala se crea como invitación
  aleatoria de alta entropía; no se asegura que Jitsi haya reservado la
  sala hasta que el usuario se incorpore. En pantalla se ofrecen los
  permisos de cámara y micrófono del navegador.
- Bloqueo y desbloqueo **en SKY**: impide que SKY envíe SMS o inicie llamadas
  hacia números bloqueados. No modifica la lista de bloqueos de Android/iOS,
  el registro de tu SIM, la red Claro/Tigo ni los bloqueos de un operador.
- Se incorpora el mosaico **Teléfono** al HUD existente, sin una aplicación
  paralela. Botones de verificación de identidad, SMS, llamada, bloqueo,
  desbloqueo y sala de video.
- Los SMS enviados retornan `queued_unverified` (Twilio aceptó en cola,
  NO confirma que se entregó). Las llamadas también retornan
  `queued_unverified` (no garantiza que las partes hablaron).
- No hay bandeja de entrada SMS ni llamadas entrantes de carrier en esta fase:
  requieren número Twilio con webhook público HTTPS y firma verificada.
- **No habilita llamadas de emergencia**. El acceso a servicios de emergencia
  depende del teléfono físico y las normas del país.
- SKY no suplanta la identidad del número del usuario; el remitente de SMS y
  el identificador de llamada son el número configurado de Twilio.

## Seguridad y prevención de cargos

SKY Teléfono está **deshabilitado por defecto** y exige:
1. La llave personal del SKY API y la sesión del propietario.
2. PIN configurado en SENTINEL, solicitado en cada operación sensible.
3. Aprobación explícita del titular y verificación real por SMS de su número.
4. Activar `SKY_PHONE_ENABLED=1` y `SKY_PHONE_ALLOW_VERIFY=1`.
5. `SKY_PHONE_ALLOW_PAID=1` solo cuando desees permitir operaciones de pago.
6. Consentimiento del destinatario en cada SMS o llamada.
7. Países autorizados por `SKY_PHONE_ALLOWED_PREFIXES`, predeterminado
   **505 (Nicaragua)**; para llamadas internacionales agregar códigos
   explícitos, por ejemplo `505,1,34,52`. Además, habilitar esos países
   dentro de los controles Geo Permissions de Twilio. Los países, operadoras,
   números premium y teléfonos de prueba pueden estar restringidos por
   cobertura, normas locales y saldo.
8. Cuotas locales: máximo **5 SMS de verificación, 10 SMS y 3 llamadas
   salientes por día**. Estas cuotas se guardan en el equipo del dueño; no
   sustituyen límites y alertas financieras en Twilio. No habilitar este
   servicio en varios servidores sin un almacén central transaccional.

`SKY_LOCAL_ONLY=1` impide salidas a Twilio y videoconferencias externas.
No se accede a contactos sin consentimiento ni se extraen datos de la SIM.
La configuración contiene información sensible; no subir credenciales,
`~/.neuralt/sky_phone.json`, números ni `.env` al repositorio. La
persistencia local usa permisos restrictivos y escritura atómica, pero no es
un cifrado de extremo a extremo ni sustituye el cifrado del disco.

## Configuración privada

Variables de entorno locales:

```dotenv
SKY_PHONE_ENABLED=1
SKY_PHONE_ALLOW_VERIFY=1
SKY_PHONE_ALLOW_PAID=0
SKY_PHONE_ALLOWED_PREFIXES=505

TWILIO_ACCOUNT_SID=AC<valor_real>
TWILIO_AUTH_TOKEN=<secreto_privado>
TWILIO_VERIFY_SERVICE_SID=VA<valor_real>
TWILIO_PHONE_NUMBER=<numero_adquirido_en_twilio_E164>

SKY_VIDEO_CONFERENCE_HOST=meet.jit.si
SKY_VIDEO_ALLOWED_HOSTS=meet.jit.si
```

No son claves que SKY pueda fabricar: debés crear o conectar una cuenta
de Twilio, habilitar Verify, adquirir/configurar un número con capacidades
requeridas y consultar disponibilidad, tarifas y condiciones por país.
Algunos números Twilio no admiten SMS en determinados países.
No configurar `SKY_PHONE_ALLOW_PAID=1` sin límites de gasto y alertas
en Twilio. No activar datos de facturación automáticamente.

En Twilio Trial, los destinatarios pueden tener que estar verificados
también en la consola. Nunca generar listas masivas de destinos.
Se recomienda limitar Geo Permissions de Verify, SMS y Voice a los países
que uses realmente, y habilitar mitigaciones contra SMS pumping/toll fraud.

## Cómo opera el panel

1. Abrí SKY → **Módulos → Teléfono**.
2. Introducí tu propio número E.164, por ejemplo `+505XXXXXXXX`.
3. Solicitá código de verificación y autorizá mediante PIN. Completá el OTP.
4. Escribí el destino (con código de país). Confirmá permiso del destinatario.
5. Seleccioná **Enviar SMS** o **Iniciar llamada**. La interfaz vuelve a pedir
   confirmación; el backend exige PIN y permisos.
6. Para bloquear, ingresá el número y pulsá **Bloquear**. Para desbloquear,
   usá el identificador en la lista privada.
7. Para videoconferencia, prepará sala, compartí voluntariamente el enlace
   y luego elegí **Entrar**. SKY carga el servicio externo solamente en ese
   momento. Para asegurar que solo entren invitados, configurá en Jitsi
   autenticación/lobby y políticas del proveedor. Poseer un enlace de sala
   no implica acceso controlado ni cifrado extremo a extremo garantizado.
8. Usá **Salir** para terminar la vista en el panel. La cámara y micrófono
   siguen sujetos al navegador, Jitsi y permisos del dispositivo.

## API SKY privada

- `GET /api/sky/phone/capabilities`, `GET /api/sky/phone/status`
- `POST /api/sky/phone/verify/start`, `POST /api/sky/phone/verify/check`
- `POST /api/sky/phone/verify/revoke`
- `GET /api/sky/phone/blocked`, `POST /api/sky/phone/blocked`
- `DELETE /api/sky/phone/blocked/{block_id}`
- `POST /api/sky/phone/sms`, `POST /api/sky/phone/voice/callback`
- `POST /api/sky/phone/video/meeting`

Todas las rutas aprovechan SKY `require_key` y el middleware de seguridad
original. Los envíos de pago y modificaciones exigen además PIN obligatorio
del propietario; no se ejecutan bajo comandos libres interpretados por LLM.

## Qué queda para una segunda fase

- Softphone WebRTC para hablar desde el micrófono de SKY (Twilio Voice JS
  SDK 2.x u operador SIP autorizado), con Access Tokens de corta duración,
  TwiML seguro y verificación de callback. La fase actual usa el teléfono
  real verificado, porque simplifica autenticación y reduce exposición.
- SMS y llamadas entrantes: webhooks HTTPS con validación criptográfica
  y protección contra spoofing.
- Bloqueos del sistema operativo: solo mediante una app Android con rol
  Call Screening autorizado por el usuario, sujeto al sistema; la PWA
  no tiene esa capacidad. En iOS se requiere una extensión Call Directory
  y los permisos del sistema, si están disponibles para el caso de uso.
- Salas de videoconferencia autenticadas y con retención/control propia;
  Jitsi público puede requerir que un moderador inicie sesión.
- Recibos de entrega por webhooks validados, métricas de costos y auditoría
  de los operadores (no confundir queued con delivered).

## Comprobaciones

La CI prueba sin cargos: normalización internacional, OTP simulado, límites,
permisos, bloqueo local, integridad de TwiML, llamadas al número verificado
primero, URLs de video, modo local y regresiones de SKY Aula.

En la PC y teléfono se debe verificar todavía acceso real a Twilio,
SMS, audio de llamada, micrófono/cámara, sala compartida y soporte del navegador.
**No marcar 100 % hasta esas comprobaciones.**

### Documentación oficial

- Twilio Verify: https://www.twilio.com/docs/verify/api
- Twilio Messaging: https://www.twilio.com/docs/messaging/api/message-resource
- Twilio Voice: https://www.twilio.com/docs/voice/api/call-resource
- Twilio Voice SDK: https://www.twilio.com/docs/voice/sdks/javascript
- Jitsi iframe API: https://jitsi.github.io/handbook/docs/dev-guide/dev-guide-iframe/
