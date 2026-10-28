# SKY IA Android 0.6 — modo independiente (prueba personal)
## SKY Android 0.6.3 — aceptar claves de autorización de Google

Google AI Studio emite **auth keys**, no solo claves antiguas con el
alfabeto limitado de SKY 0.6.2. La app ya no presupone un formato
específico: admite caracteres ASCII imprimibles para el encabezado
`x-goog-api-key`, normaliza espacios invisibles del portapapeles y
rechaza entradas de proyecto, prefijos, controles e inserciones Unicode
peligrosas. **La autenticidad la verifica Google por HTTPS antes de
guardar la clave cifrada.**

Nunca copies ni pegues tu clave en un chat o un repositorio. Esta
modalidad continúa siendo beta privada; una app publicada requiere
backend autenticado y controles de cuota.

## SKY Android 0.6.2 — pegar claves sin espacios invisibles

Esta actualización añade **PEGAR CLAVE COPIADA** en Ajustes. Lee el
portapapeles sólo cuando el usuario toca ese botón, limpia espacios y
caracteres Unicode invisibles que pueden introducir algunos teclados
Android y verifica el acceso a Gemini antes de cifrar la clave en
Android Keystore. No imprime, almacena en GitHub, ni incluye claves en
la APK. Si el portapapeles contiene el ID de proyecto, JSON, encabezados
Bearer o caracteres visibles no válidos, explica el problema.

No compartas una clave API en chats, fotos, incidencias ni repositorios.
La integración directa en APK sigue siendo únicamente para pruebas
privadas; para distribución general se necesita un backend seguro.

## Versión 0.6.1 — diagnóstico y verificación de claves de Gemini

En la primera configuración, tocá **Copiar clave** en Google AI Studio.
**NO copies** el nombre/número del proyecto (por ejemplo `projects/...`).
SKY ahora explica si el formato pegado es incorrecto sin mostrar la clave
y comprueba la conexión real con Gemini antes de activar el chat.
La contraseña se guarda cifrada únicamente tras una respuesta válida;
no se almacena en GitHub ni en SKY Windows.

En cada modificación de `mobile/android-agent/**` sobre `main`, el flujo
`SKY Android Signed Release Candidate` compila automáticamente una APK
firmada con el certificado de distribución previamente configurado.
El ZIP privado del artefacto de GitHub Actions requiere iniciar sesión;
la APK se encuentra dentro del ZIP. No distribuir la beta de clave personal
a otros usuarios sin reemplazar la integración por un backend autenticado.


SKY Android funciona sin que SKY Windows esté encendida. Esta actualización
**solo modifica el subproyecto Android**: no altera módulos, puertos,
archivos de configuración ni API de SKY Windows.

## Cómo activar la conversación sin Windows

1. Actualizar la APK **release** firmada con el MISMO certificado privado que
   usaste antes (versión Android 0.6.0, code 7). No instalar la APK debug sobre
   una release; Android no permite actualización entre firmantes distintos.
2. Abrir SKY Android > Ajustes. Se muestra primero el **modo independiente**.
   Ya no es obligatorio introducir HTTPS de Tailscale o un código temporal.
3. Para la versión de **pruebas personales**, obtener una clave de Gemini API
   propia en https://aistudio.google.com/apikey .
4. Introducirla solamente en Ajustes de tu teléfono, leer y marcar la
   autorización de envío de mensajes a Google y seleccionar
   **ACTIVAR SKY ANDROID INDEPENDIENTE**. SKY cifra la clave con Android
   Keystore y no la registra en GitHub, logs ni archivos de código.
5. Abrir Conversación, escribir una pregunta o tocar Hablar con SKY. La
   respuesta de Gemini se presenta y, si el motor TTS está habilitado, se
   escucha. Esta ruta funciona con Wi-Fi o datos móviles y SIN SKY Windows.
6. El botón **Desactivar nube y borrar mi clave** revoca el uso local de la
   clave y elimina su cifrado del teléfono. Revocar la clave en AI Studio
   también cuando deje de usarse.

La integración de pruebas utiliza el endpoint HTTPS oficial Gemini
`models/gemini-3.5-flash-lite:generateContent` y el encabezado
`x-goog-api-key`. Se limita el historial a los últimos cuatro turnos
y se conserva sólo en memoria durante la sesión. La app no envía archivos,
contactos ni herramientas del teléfono a Gemini. Comandos locales,
apertura de apps autorizadas, notas, alarmas, ojos y chistes permanecen
locales como antes.

**Advertencia crítica:** Google recomienda NO utilizar claves API
directamente desde aplicaciones cliente de producción, aunque se almacenen
con Android Keystore, ya que un atacante con control del dispositivo o del
tráfico de su aplicación puede extraerlas. Este modo es únicamente una
**beta privada con una clave propia**; no distribuir públicamente esa APK
como producto de uso general. Para publicar SKY, sustituir el transporte por
un servicio de backend móvil con autenticación, límites y App Check, o
Firebase AI Logic. El usuario es responsable de cuotas y posibles cargos.

Si Gemini rechaza la clave, comprobar las restricciones, el modelo y las
cuotas en AI Studio. Se usa el modelo estable `gemini-3.5-flash-lite`;
la disponibilidad depende de la cuenta y la región.

## SKY Windows sigue opcional

El botón **Conexión Windows (opcional)** mantiene el emparejamiento
anterior sin modificar su implementación ni su servidor. El modo
independiente tiene prioridad cuando está activado. Esta versión NO
introduce escucha en segundo plano, control indiscriminado de apps,
envío de mensajes, ni IA totalmente offline: requiere internet para
conversaciones Gemini. Las funciones Android locales siguen disponibles
sin internet.

Documentación oficial:
- https://ai.google.dev/gemini-api/docs/api-key
- https://ai.google.dev/api/generate-content
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite

---

# SKY IA Android 0.5 — aplicaciones dinámicas y compañía divertida

SKY mantiene el diseño de **ojitos expresivos flotantes**, interfaz minimalista
y voz. Esta versión incorpora el lanzamiento supervisado de **cualquier app con
icono de inicio visible para Android**, sin lista fija ni instalar integraciones
de cada marca. El catálogo se consulta en el teléfono cada vez que se solicita:
si instalás una app o un videojuego nuevo, SKY puede descubrirlo sin actualizar
el código, siempre que Android la exponga como aplicación iniciable.

## Cómo utilizarlo

- «SKY, abre Spotify / TikTok / Instagram / Facebook / X / Threads /
  Snapchat / Word / Excel / PowerPoint / ChatGPT / Claude / Gemini / Copilot».
- «SKY, abre Minecraft» (u otro juego que esté instalado).
- «SKY, mostrame mis aplicaciones»: abre el catálogo buscable, con acceso
  a la apertura supervisada. También disponible desde **Ajustes**.
- «SKY, comparte en Instagram: Texto para mi publicación»: prepara un
  contenido mediante Android Share, solo si esa aplicación admite
  recibir texto. **Nunca pulsa Publicar ni Enviar**.
- «SKY, voy en bus» o «SKY, voy caminando»: inicia modo acompañante
  contextual, con conversación y propuestas ocasionales mientras la
  aplicación permanece visible.
- «SKY, contame un chiste», «SKY, silba», «SKY, sorprendeme»:
  chistes originales y un silbido corto sintetizado.
- «SKY, desactiva modo acompañante» detiene las propuestas opcionales.

## Supervisión, seguridad y límites verificables

1. SKY **confirma antes de abrir** cualquier app, salvo que el propietario
   seleccione **«Confiar y abrir»** para ese paquete. Una aplicación de
   confianza puede abrirse inmediatamente tras una orden expresa por voz
   o chat; desde el catálogo puede **quitarse la confianza**. SKY vuelve
   a verificar que la app sigue instalada. Este permiso **no** concede
   acceso automático a datos internos, mensajes, cuentas ni publicaciones.
2. El catálogo se construye con `ACTION_MAIN + CATEGORY_LAUNCHER` y
   `<queries>`, sin `QUERY_ALL_PACKAGES`; se queda **en el celular**.
   Android puede filtrar apps no visibles, sin icono o pertenecientes
   a perfiles restringidos. No es posible garantizar que detecte todas.
3. El uso de Share no implica soporte de escritura en todo editor ni
   envío autónomo. La **escritura asistida** de campos vacíos mediante
   Accesibilidad sigue limitada a WhatsApp y Gmail, voluntaria y sin
   pulsar Enviar. Otras automatizaciones requieren APIs oficiales o
   integraciones explícitas con cada aplicación.
4. El modo acompañante se activa solo por una orden de voz/chat o
   desde Ajustes; hace propuestas **solo cuando SKY está visible** y
   limita la frecuencia y duración. No mantiene escucha continua con
   pantalla bloqueada, ni lee ubicación, acelerómetro o conversaciones
   externas. Al caminar, debe priorizarse la seguridad vial.
5. Para conversaciones de IA avanzadas sigue siendo necesario que SKY
   Core o un proveedor remoto autorizado esté disponible; los comandos
   locales, chistes y catálogo no dependen de ese servidor.
6. Compilación aprobada en CI no equivale a pruebas reales de APK en
   Samsung. Comprobar TTS, micrófono, batería, instalación, app de reloj,
   variaciones de paquetes y perfiles de usuario.

Consulta [distribución Android](apk/) para la APK de GitHub Actions.

---

# SKY IA Android 0.4 — acciones locales y asistente animada

La aplicación Android mantiene **ojos expresivos, voz, paneles bajo demanda,
chat y configuración segura**. Esta versión añade un ejecutor REAL pero
limitado de acciones locales, independiente de que el SKY Core en Windows
esté conectado. Su seguridad se basa en comandos expresos, permisos y
confirmaciones; ninguna respuesta generada por IA ejecuta acciones solas.

## Comandos disponibles ahora

| Orden hablada o escrita | Ejecución | Evidencia honesta |
| --- | --- | --- |
| «SKY abre WhatsApp» | Solicita confirmación y abre la aplicación permitida | Android aceptó la apertura, no verifica que haya cargado |
| «SKY pon una alarma a las 5:30» | Abre el Reloj mediante `AlarmClock.ACTION_SET_ALARM` con hora y etiqueta | Debe verificarse la alarma en Reloj; no declarar creada antes |
| «SKY pon un temporizador de 10 minutos» | Abre temporizador nativo con duración | Revisar que Reloj lo inició |
| «SKY busca en internet recetas saludables» | Abre la búsqueda real en el navegador del teléfono | Android aceptó la apertura de la búsqueda |
| «SKY anota comprar leche» | Guarda una nota privada en SharedPreferences local | Se confirma el guardado con `commit()` |
| «SKY mostrame mis notas» | Muestra las últimas notas privadas del teléfono | Lee almacenamiento local |
| «SKY escribe en WhatsApp: hola» | Ofrece Compartir o Escritura asistida, tras confirmación | Nunca envía mensajes automáticamente |
| «SKY abre panel de conversación» | Abre el panel nativo solicitado | Ejecución local inmediata |

Las aplicaciones soportadas por apertura directa son YouTube, Chrome,
WhatsApp y Gmail; se habilitan individualmente en Ajustes.
La alarma usa el **Reloj del teléfono**. La API de Android no ofrece
confirmación universal de que el Reloj guardó una alarma, por lo que SKY
no informa falsamente `VERIFIED`. La creación de alarmas para fechas
concretas (por ejemplo, «mañana a las 5») requiere una interfaz de fecha
que el intent estándar no proporciona: SKY no finge garantizar esa fecha.

## Escritura asistida opcional (alcance restringido)

Es una función **manual y optativa** para WhatsApp y Gmail, no un agente
autónomo que navega por todas las aplicaciones. Antes de habilitar el
servicio de Accesibilidad, SKY presenta una divulgación de permisos y
requiere una aceptación explícita; el usuario debe activarlo además desde
Ajustes Android. Después, para **una solicitud aprobada**, SKY abre la
app correspondiente, y el usuario toca **un campo de texto vacío**. El
servicio puede poner ahí el texto solicitado dentro de 45 segundos.

- No lee historiales ni contactos; no accede a contraseñas.
- No envía mensajes, no presiona el botón Enviar y no opera por órdenes
  ocultas de modelos de IA.
- El permiso para cada aplicación sigue siendo necesario.
- El usuario puede retirar su consentimiento desde Ajustes de SKY y
  desactivar el servicio desde Ajustes Android > Accesibilidad.
- Google Play impone reglas de divulgación y limita la autonomía con
  AccessibilityService; la APK de desarrollo no equivale a una
  publicación aprobada en Play Store.

## Límites que todavía requieren desarrollo y pruebas

- No hay palabra clave escuchando las 24 horas con la pantalla bloqueada;
  la voz comienza al pulsar Hablar.
- No hay replicación completa de herramientas Windows en Android. El
  motor de chat móvil actual no recibe privilegios de ejecución remota.
- No hay sincronización permanente completa del historial ni de las
  notas del teléfono con Windows.
- La compilación de CI valida código y pruebas automatizadas, no sustituye
  pruebas físicas con Samsung, Clock, Gmail, WhatsApp, micrófono, batería,
  reinicio, accesibilidad o firma estable de APK.

Los APK siguen aislados en
[carpeta APK](apk/) y se generan mediante
[GitHub Actions](../../.github/workflows/sky-mobile-agent.yml).

---

# SKY IA Android 0.3 — ojos protagonistas y paneles bajo demanda

La pantalla inicial ya no muestra la conversación, tarjetas, accesos rápidos
o formularios técnicos: **solo SKY, sus ojos animados, el botón para hablar,
un acceso al chat y Ajustes**. La configuración HTTPS se muestra durante el
primer emparejamiento y luego queda guardada en Android Keystore.

## Órdenes reales de la interfaz
Con la aplicación abierta, tocá **Hablar** y decí:
- «SKY, abre panel de conversación» → abre el panel de chat.
- «SKY, cierra panel» → vuelve a los ojos animados.
- «SKY, abre módulo de documentos» → presenta el panel de documentos.
- «SKY, abre SKY Docente» → presenta el panel docente.
- «SKY, abre programación» → presenta el panel de programación.

También podés escribir esas órdenes en el panel de conversación. Los
paneles incluidos son Investigación, Documentos, Programación, Docente,
Creativa, Metaverso y Deportes. Se muestran **únicamente al solicitarlos**.
Los ojos, la voz y la vinculación existentes se conservan.

**Alcance verificado por código:** abrir o cerrar estos paneles ocurre en el
teléfono y no exige autorización del chat remoto. Sin embargo, **abrir un
panel no ejecuta automáticamente las herramientas del módulo en Windows**.
El chat móvil sigue conectado a la ruta segura de SKY Core para consultas
de texto, sin permiso genérico para ejecutar herramientas o controlar el PC.
Para activar herramientas reales desde Android hará falta ampliar la API con
autorización específica por módulo y dispositivo, pruebas y confirmaciones.

La voz se inicia tocando el micrófono: no hay micrófono siempre activo ni
activación de palabra clave con pantalla bloqueada. El ajuste para encender
o apagar las respuestas habladas se encuentra en **Ajustes**. El historial
visual del panel es temporal durante la sesión; no debe confundirse con la
memoria persistente compartida entre PC y teléfono.

Las pruebas del workflow Android incluyen compilación, pruebas de comandos
de voz/texto y pruebas del backend; la experiencia completa aún requiere
validación física de micrófono, audio, Android y conexión a SKY Core.

---

# SKY IA Android 0.2 — interfaz principal inmersiva

**Interfaz actual:** abre a pantalla completa, con SKY y sus ojos animados como
protagonistas, controles de voz, conversación, accesos rápidos para redactar
instrucciones de investigación/documentos/código y un acceso a Ajustes.

### Configuración inicial y sesiones
- El enlace con el SKY Core por HTTPS privado se solicita únicamente cuando
  el teléfono no tiene un token válido almacenado en Android Keystore.
- Una vez vinculado, las entradas de URL, nombre y código **no aparecen en el
  inicio**. La pantalla principal se abre directamente con SKY.
- El propietario puede consultar permisos, estado y revocación desde Ajustes.
- El chat tiene un permiso separado y temporal de 24 horas. Al caducar,
  se solicita **renovarlo**, sin repetir la vinculación del teléfono.
- Cada petición en la nube o que contenga datos privados requiere autorización
  nueva mediante el panel Privacidad; ninguna casilla queda marcada después
  de enviar una consulta.
- Los accesos de investigación, documentos y código **preparan solicitudes
  para el chat de SKY Core**; no convierten por sí solos al Android en
  controlador general de estas tareas ni habilitan ejecución arbitraria.
- El reconocimiento de voz sigue requiriendo un toque. No se incorpora
  escucha en segundo plano o con pantalla bloqueada.

### Actualización e instalación
GitHub Actions genera un APK de depuración en el artefacto
`sky-mobile-agent-debug` del workflow **SKY Mobile Android Agent**.
Es una compilación técnica; aún requiere pruebas físicas en Samsung/Android.

**Firma de desarrollo:** los APK debug compilados en distintas ejecuciones
de GitHub Actions pueden tener certificados diferentes. Si Android rechaza
una actualización por firma, no es un fallo de los ojos; no desinstalés
sin asegurar antes una vía de revinculación, porque al desinstalar se
perderán los tokens locales. Para actualizaciones que conserven datos se
necesita una misma clave de firma protegida en CI.

El chat depende de conectividad con el SKY Core o un backend remoto
configurado. Que la computadora esté apagada no garantiza conversación
activa con la arquitectura actual. El estado "vinculada" indica tokens
almacenados y no sustituye una comprobación de conexión real.

---

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
