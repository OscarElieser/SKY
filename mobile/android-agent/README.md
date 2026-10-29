# SKY Android — versión de código 0.8.18 · memoria, historial y adjuntos

**Novedades en la rama `main` (pendientes de validar en un teléfono real):**

- **Historial por consulta:** SQLite privado; fecha y hora local `dd/MM/yyyy · HH:mm`, título derivado de la pregunta, consulta y respuesta. El botón **Historial** permite expandir las últimas 150 consultas guardadas; el registro permanente no se borra al cerrar la app. Ajustes → **HISTORIAL · BORRAR CONSULTAS** borra el historial Android tras confirmación.
- **Voz opcional:** SKY continúa funcionando por **chat escrito**, voz tocando los ojos o activación **manos libres** opcional mediante el servicio de micrófono con notificación. No se exige activar manos libres para escribir o usar otras herramientas. Android puede detener la escucha en segundo plano; no se promete presencia garantizada mientras el teléfono esté bloqueado.
- **Adjuntar archivo:** botón **＋** en el cuadro de conversación, selector nativo y opción de quitar el adjunto. SKY extrae hasta 3.100 caracteres iniciales de texto/código y texto de **DOCX/XLSX/PPTX**; permite analizar imágenes, **PDF completo hasta 5 MB** y audio/video compatible de hasta 5 MB mediante Gemini, con autorización previa para cada envío. Para PDF mayores de 5 MB, solo intenta interpretar visualmente su primera página. Tamaño máximo de archivo leído: 8 MB. Otros formatos, archivos cifrados y multimedia mayor de 5 MB se reconocen sin inventar su contenido. Las capacidades remotas dependen del modelo, cuota y conexión. El archivo original no queda almacenado por SKY.
- **Perfil personal local:** en Ajustes → **MI PERFIL PERSONAL · EDITAR / IMPORTAR DE WINDOWS**, editar o importar el archivo `USER.md` desde `~/.neuralt/USER.md` en SKY Windows (cópialo voluntariamente al teléfono). Android también acepta JSON con campos `profile` y `facts[].text`. El perfil se conserva solo en preferencias privadas del teléfono; límite de 8.000 caracteres. No permite guardar PIN, contraseñas o API keys. Para incluirlo en un mensaje remoto, abrir **Privacidad** dentro del chat y autorizar **Enviar datos privados** para esa consulta concreta.
- **Memoria explícita:** la orden de texto **«recuerda que ...»** añade ese hecho al perfil local, sujeto a la validación de seguridad. No se asume entrenamiento de pesos del modelo ni aprendizaje fiable sin evaluación.
- **SKY Windows:** la importación voluntaria del perfil es el primer puente portable. No copia automáticamente bases SQLite cifradas, procesos, claves ni todos los módulos de Windows a Android. La sincronización continua requiere autenticación y autorización separadas.

**Instalación:** no es suficiente con encontrar estos cambios en GitHub. Esperá a que finalicen las pruebas y exista una APK **firmada** de esta misma versión en [GitHub Releases](https://github.com/OscarElieser/SKY/releases); seguí la guía de instalación y no fuerces Play Protect.

---

## Documentación anterior (versiones 0.8.x)

**Beta Android independiente de Windows.** Diseño con **solo ojos y boca animados**, sin máscara ni rostro. Órdenes del teléfono por texto y voz, supervisadas por el usuario.

**Código en `main`: 0.8.6 (versionCode 19).** La APK se distribuye solo cuando aparece firmada en GitHub Releases. No desinstalés la versión anterior sin respaldo.

[**Ver las versiones APK efectivamente publicadas**](https://github.com/OscarElieser/SKY/releases) · [Versiones Android publicadas](https://github.com/OscarElieser/SKY/releases) · [Guía de instalación y seguridad](apk/README.md)

## Instagram @usuario — preparación real de autorización (0.8.6)

La API profesional de Meta **no autoriza cuentas personales**. Para
usar estadísticas y publicación directa en tu propia cuenta,
desde Instagram cambiá a **Creador** (gratis; conserva seguidores
y publicaciones, pero implica que el perfil sea público):

1. Instagram → Perfil → ☰ → **Tipo de cuenta y herramientas** →
   **Cambiar a cuenta profesional** → **Creador**.
2. Verificá el **Panel para profesionales** en Instagram.
3. En SKY → Ajustes → **MIS REDES · PERFIL Y ENLACES PÚBLICOS** →
   seleccioná Instagram → **Preparar acceso oficial de Instagram**.
4. Elegí **Ya cambié a Creador** solamente cuando lo hayas completado.
   SKY guarda el dato local como **declaración**, jamás como conexión
   verificable por API.
5. Para la autorización posterior, registrar una app en
   [Meta for Developers](https://developers.facebook.com/apps/) y
   configurar **Instagram API with Instagram Login**, un callback
   HTTPS y un backend seguro para conservar el secreto de Meta.
   Esta ruta no exige una Página de Facebook.
6. Permisos oficiales necesarios, separables por función:
   `instagram_business_basic` para el perfil,
   `instagram_business_manage_insights` para estadísticas,
   `instagram_business_content_publish` para publicaciones.

**Estado real:** todavía no hay aplicación Meta registrada y configurada
para SKY ni un backend OAuth activo; por tanto, no existe botón de
inicio de sesión funcional ni acceso autorizado a estadísticas.
El paso de Creador no concede automáticamente permisos a SKY.

[Leé la guía técnica completa y sus requisitos de seguridad](INSTAGRAM_OAUTH_SETUP.md).
No ingresés ni compartás contraseñas, tokens, códigos 2FA o secretos
de Meta. No se cambia ninguna configuración en SKY Windows.

---

## SKY Android 0.8.5 — mis cuentas y perfiles sociales

A partir de 0.8.5, SKY permite mantener en el **teléfono** un catálogo
de perfiles públicos de Instagram, Threads, TikTok, Facebook, YouTube,
X, Snapchat, Pinterest y LinkedIn.

### Importar los perfiles desde un archivo

1. En SKY, abrí **Ajustes → MIS REDES · PERFIL Y ENLACES PÚBLICOS**.
2. Seleccioná **Importar perfiles JSON** y buscá el archivo descargado
   en **Mis archivos / Descargas** de Android.
3. SKY valida el formato, guarda hasta 25 perfiles en preferencias
   privadas locales y muestra cada perfil con el estado
   **«Identificada, sin autorización OAuth»**.
4. Tocá un perfil para **abrir su enlace público**, **crear contenido
   para esa red** desde Estudio Creativo, **editarlo** o **retirarlo**.
5. Si Facebook solo tiene nombre visible, queda identificado pero SKY
   **no inventa su dirección de perfil**: añadí el identificador exacto
   cuando lo tengas.

Ejemplo genérico, sin perfiles personales ni claves:

```json
{
  "sky_profiles_version": 1,
  "profiles": [
    {"platform":"Instagram","handle":"miusuario","display_name":"Mi Instagram"},
    {"platform":"YouTube","handle":"micanal","display_name":"Mi canal"},
    {"platform":"Facebook","handle":"","display_name":"Mi perfil personal"}
  ]
}
```

**Nunca importes** teléfonos de WhatsApp, correos personales,
contraseñas, cookies, códigos 2FA, claves privadas ni tokens OAuth.
Los datos de identificación se guardan solo en el dispositivo
(`sky_public_social_profiles`); no se incluyen identificadores
personales en GitHub ni se transfieren a Gemini por este flujo.
Desinstalar SKY o borrar sus datos puede eliminar el catálogo.

### Identificar no equivale a conectar

Este módulo NO inicia sesión en tus cuentas, NO consulta estadísticas
privadas, NO programa ni publica posts y NO lee mensajes. El siguiente
paso es integrar los flujos **OAuth oficiales**, consentimiento por
cuenta, permisos mínimos, revocación y controles de publicación.
Google/Gemini no puede actuar como token universal para redes sociales.

**Verificación:** probar importación del JSON, acceso a enlaces
públicos, edición, retirada y acceso al Estudio Creativo en el Samsung.
La compilación automatizada no confirma funcionamiento en hardware.

---

## SKY Android 0.8.4 — música a tu voz y activación segura

**Novedades del código (aún necesitan validación en el Samsung):**

- Reconoce órdenes directas **sin repetir «SKY»** mientras está escuchando:
  `siguiente`, `atrás`, `repite`, `subí el volumen`,
  `bajá el volumen`, `pará`, `reanudar` y `cambiá de música`.
- Desde **Ajustes → CONTROL MUSICAL · SIGUIENTE / ATRÁS / VOLUMEN**
  también se pueden probar los controles táctiles sin micrófono.
- Usa `AudioManager.dispatchMediaKeyEvent` para solicitar a la sesión
  multimedia activa pasar de pista, retroceder, pausar y reanudar.
  El ajuste de volumen modifica **STREAM_MUSIC** y confirma el nivel
  cuando Android permite cambiarlo. Spotify/YouTube Music/YouTube
  determinan si atienden los comandos; SKY no debe declarar éxito
  musical sin comprobarlo.
- **Repetir:** la primera implementación envía «anterior», que en
  algunos reproductores reinicia el tema actual y en otros cambia al
  anterior. **No activa todavía el bucle de repetición**. La integración
  posterior con un reproductor autorizado o servicio de sesión
  permitirá un control más preciso.
- Voz para **«activá el teléfono»** o «desbloqueá el teléfono»
  disponible **solo si SKY ya está abierta y escuchando**. Solicita
  al sistema mostrar el desbloqueo. Si Samsung exige PIN o biometría,
  el usuario debe autenticarse. Nunca desactiva el bloqueo.
- **No hay escucha permanente con la pantalla apagada:** requiere
  un servicio específico con notificación, permiso de micrófono,
  controles de batería y validación según la versión de Android.
  Esta versión no lo declara ni finge funcionar en segundo plano.

### Vincular tus redes sociales

Podés compartir los **@usuarios o enlaces públicos** de TikTok,
Instagram, Facebook, YouTube, X, Threads y otras cuentas para preparar
las integraciones. **No compartas contraseñas, códigos 2FA, cookies,
tokens, archivos de sesión ni claves API.** Solo el identificador público
no otorga permiso de lectura o publicación. Las conexiones privadas
requieren un flujo de autorización OAuth de cada plataforma, sus
permisos aprobados y revocación.

Esta beta ofrece Studio Creativo, importación voluntaria de métricas,
preparación de contenidos y compartir videos; **no está conectada
automáticamente a las estadísticas privadas ni publica en secreto**.

### Prueba cuando la APK esté firmada

1. Abrí una canción en Spotify o YouTube Music y dejá SKY visible.
2. Habilitá el micrófono y tocá **HABLAR**. Decí «siguiente», «atrás»,
   «subí el volumen» y «pará». Observá **si el reproductor realmente
   obedece**, no solo si SKY muestra un mensaje.
3. En Ajustes, probá los controles táctiles para aislar problemas del
   reconocimiento de voz.
4. Con la app visible, probá «activá el teléfono» si se muestra el
   bloqueo: Samsung debe pedir PIN/huella si corresponde.
5. **No esperés que SKY escuche mientras la pantalla esté apagada
   en esta versión**; esa capacidad sigue en desarrollo.

---

## Historial de diseño y comandos 0.8.1 (referencia)

- SKY ya no dibuja un rostro gigante. Los **dos ojos ovalados** flotan, parpadean y se mueven; **la boca** sonríe y se anima al hablar. Conserva estados escuchar, pensar, hablar y error.
- El fondo mantiene una iluminación violeta/turquesa discreta. Los controles de voz, chat y detener permanecen accesibles y se ajusta el panel a la barra de navegación Android.
- Los comandos explícitos de WhatsApp se procesan en el teléfono ANTES de preguntar a Gemini. Ejemplo: **«SKY, abrí WhatsApp y mandá un mensaje a Ana: hola, ¿cómo estás?»**.
- SKY prepara el texto, puede reformularlo de forma local y enseña una vista previa. **Después de confirmar, abre el compositor de WhatsApp. Vos elegís el contacto correcto y pulsás Enviar**. No envía mensajes sin tu aprobación, no lee conversaciones ni finge haber enviado algo.
- Conserva acciones existentes: abrir aplicaciones visibles en Android, alarmas, temporizadores, notas, búsqueda web, modo acompañante y conversaciones Gemini con clave privada.
- No activa servicios de accesibilidad ni toma control ilimitado de otras aplicaciones. Las capacidades dependen de permisos y APIs oficiales.
- Windows no es necesario para conversar en el teléfono y **no se modifica** en este lanzamiento.

## Prueba en el Samsung

1. Descargá una APK **solo cuando figure publicada y firmada** en GitHub Releases. Instalá encima de la anterior sin desinstalar ni borrar la clave local. Si Play Protect muestra un riesgo, no fuerces la instalación.
2. Comprobá que solo se vean dos ojos y la boca. Tocá los ojos y observá sus gestos.
3. Presioná **HABLAR** y decí «SKY, abrí YouTube»; confirmá el permiso cuando Android lo solicite.
4. Decí «SKY, mandá un mensaje a Ana: hola, ¿cómo estás?». Verificá la vista previa. Pulsá **ABRIR WHATSAPP**, elegí la conversación y decidí si lo enviás.
5. Si no reconoce la orden, compará el texto interpretado por el dictado con el mensaje esperado. El reconocimiento de Android puede equivocarse con nombres.
6. Preguntale algo a Gemini y comprobá la voz natural. **Conversación fluida** es opcional y solo funciona en primer plano, con límite de turnos.

**Seguridad:** las claves Gemini no se publican en GitHub; se guardan cifradas en Android Keystore para esta beta personal. Para distribución pública es necesario un backend autenticado. No compartir credenciales en capturas ni mensajes.

---

## SKY Android 0.8.3 — datos reales, MP4 y publicación supervisada

### 1. Consultar y analizar métricas reales en el propio teléfono

En **Ajustes → MÉTRICAS REALES · IMPORTAR ESTADÍSTICAS** ahora podés
importar registros de estadísticas de tus perfiles, **sin enviar las cifras
a Gemini ni a terceros**. El archivo CSV debe incluir como mínimo las
columnas `Plataforma,Publicacion,Vistas` y puede incluir
`Likes,Comentarios,Compartidos,Seguidores,Fecha`. También reconoce
varios encabezados equivalentes en inglés.

Ejemplo **ficticio de formato**, NO estadísticas reales:
```csv
Plataforma,Publicacion,Vistas,Likes,Comentarios,Compartidos,Seguidores,Fecha
TikTok,Mi primer video,120,10,2,1,0,2026-10-28
Instagram,Mi segundo video,240,25,3,4,2,2026-10-28
```

Usá números que **vos hayas obtenido realmente** de TikTok Studio,
Instagram Insights, YouTube Studio u otras fuentes oficiales. Algunos
exportes vienen con columnas o formatos distintos: adaptalos antes de
importar. SKY calcula vistas, interacción por vista y publicaciones
destacadas. El análisis es local y se puede borrar en Ajustes.

**Estado:** importación CSV voluntaria e interpretación local.
**No hay sincronización automática OAuth**: requiere autorización de
cada perfil, registro de la app y permisos aprobados por la red.
No afirma que sean métricas consultadas directamente de las APIs.

### 2. Crear un video MP4 sin salir de SKY

En **Ajustes → ESTUDIO CREATIVO · MIS REDES SOCIALES**, elegí una red,
escribí el tema y elegí **Crear publicación**. Después de revisar el
guion generado, tocá **Crear video MP4**. SKY construye en el propio
teléfono un video **vertical H.264 de 720×1280, 10 segundos, 15 fps**
con cinco escenas de **texto animado** y fondos de colores. No emplea
imagen generativa remota ni requiere salir ante cámara.

**Límite actual:** MP4 sin sonido, sin videos de stock, sin voz en off
ni fotos; completá la edición con música propia o licenciada y material
original dentro del editor de Instagram/TikTok/YouTube. La generación
usa el codificador de hardware **MediaCodec/OpenGL ES** disponible en
Android. Puede fallar si el dispositivo no lo admite o no tiene espacio.
**Se necesita una prueba real en el Samsung**: superar CI no garantiza
que el codificador concreto funcione en todos los dispositivos.

SKY ofrece **Compartir video** mediante una URI temporal de solo
lectura, sin publicar por sí misma. La app que elijas y el propietario
confirman dónde y cuándo se publica.

### 3. Publicación automatizada y cuentas conectadas

La app ya permite compartir texto y video desde Android para completar
la publicación en la red elegida. **No está conectada por OAuth
a tus perfiles y no puede publicar silenciosamente.** Publicación
directa con programación, estadísticas remotas y confirmación de
publicación requieren:
- TikTok: app registrada y permisos `video.publish`, autorización del
  creador y auditoría para publicaciones públicas.
- Instagram/Facebook: integración Meta y acceso autorizado a las
  cuentas compatibles (Instagram profesional para la API relevante).
- YouTube: OAuth para Analytics y permisos de subida para publicar;
  la clave API de Gemini **no sustituye** el acceso de YouTube.

### 4. Teléfono como núcleo independiente

El reconocimiento de órdenes, gestión de permisos, interfaz, notas,
estadísticas importadas, generación del MP4 y reproducción local se
ejecutan **en Android**. Gemini sigue siendo opcionalmente el motor
remoto de lenguaje para tareas inteligentes; el teléfono orquesta
las herramientas y protege los datos que el usuario no autorizó
compartir. Android no ofrece acceso irrestricto a credenciales,
datos de todas las apps, cámara, micrófono ni permisos de publicación;
la autonomía se construye con permisos verificables y límites por tarea.

**Versión de código:** `0.8.3`, `versionCode=16`.
**Distribución:** solo instalar después de que la compilación, pruebas,
firma y Release sean aprobadas en GitHub. Los APK anteriores permanecen
como respaldo. SKY Windows no fue modificado.

---

## SKY Android 0.8.2 — conversación cotidiana, música y cámara voluntaria

**Solo Android**. SKY Windows no fue modificado. La app puede entender órdenes
durante una sesión de voz sin repetir «SKY» en cada frase.

### Música con el servicio que elijas

- En **Ajustes → MÚSICA** elegí Spotify, YouTube Music o YouTube como servicio
  favorito. SKY recuerda esa preferencia.
- Pedí **«Reproducí la canción [título] en Spotify»**, **«Pon la canción
  [título] en YouTube Music»** o **«Pon la canción [título]»** sin prefijo.
- El ejecutor usa `MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH`,
  según la API oficial de Android. **Solo la aplicación receptora puede
  confirmar si empezó a reproducir**; algunos servicios muestran resultados
  de búsqueda en su lugar, y quizá debas tocar la canción. No utiliza APIs
  privadas de Spotify/YouTube ni elude licencias.
- En **Ajustes → Conversar sin decir SKY**, la escucha fluida es voluntaria,
  únicamente mientras SKY está visible y por un máximo de ocho turnos.
  La opción se conserva entre aperturas, pero el micrófono no se inicia
  automáticamente: tocá **HABLAR** para comenzar.

### Respuestas naturales para contactos elegidos

- **Ajustes → RESPUESTAS NATURALES · CONTACTOS → Autorizar contacto**.
  Escribí manualmente el nombre del contacto; se admite un máximo de
  veinte nombres y podés retirarlos desde Ajustes.
- Pegá un fragmento del mensaje recibido y aceptá su envío **solo esa vez**
  a Gemini. SKY genera un **borrador editable**, pensado para el contexto
  y sin fórmulas robóticas. Vos elegís el chat correcto y pulsás **Enviar**
  en WhatsApp. También funciona con una orden explícita como:
  **«Respondé a Ana: ¿Por qué no me escribís?»** si Ana fue autorizada.
- **Esta beta NO lee conversaciones, no accede a contactos del sistema y NO
  responde automáticamente en segundo plano.** El acceso a notificaciones,
  a conversaciones de otras apps y el envío automatizado requieren permisos
  adicionales, validación de identidad del remitente, pruebas, controles
  de privacidad y cumplimiento de las reglas de la aplicación receptora.
  La lista de nombres autoriza únicamente la creación de borradores.

### Cámara y acompañamiento respetuoso

- En **Ajustes → CÁMARA OPCIONAL · ¿CÓMO ME VEO?** o con la orden
  «Mírame», SKY puede abrir la **cámara de Android** para una única foto.
- Al regresar de la cámara, una **segunda confirmación** permite o impide
  enviar una miniatura JPEG a Gemini. La app no guarda el archivo, no usa
  cámara continua ni identifica a la persona. Según la cámara instalada,
  la aplicación de cámara del dispositivo puede tener sus propias reglas
  de almacenamiento.
- SKY comenta solo rasgos **visibles**, no adivina emociones, diagnóstico
  psicológico ni estados de ánimo a partir del rostro. Te preguntará
  cómo te sentís y responderá de manera conversacional.
- El uso de Gemini requiere internet y consentimiento; la clave personal
  permanece en Android Keystore en esta beta privada. No subir claves a
  GitHub, README ni chats.

### Límites y verificación

- SKY no posee «acceso total» e indiscriminado al celular: ejecuta acciones
  disponibles con permisos de Android y confirmación cuando corresponde.
  No puede afirmar que una canción, mensaje o publicación se completó
  si la aplicación receptora no lo confirmó.
- `versionCode=15`, `versionName=0.8.2`. Esta versión de código
  necesita aprobar CI, compilación firmada y pruebas reales en el Samsung.
  Consultá [GitHub Releases](https://github.com/OscarElieser/SKY/releases)
  y no descargues un APK 0.8.2 antes de que aparezca allí con su SHA-256.
- La instalación existente sigue siendo el respaldo hasta aprobar 0.8.2.

---

## SKY Estudio Creativo — redes sociales (0.8.1)

**Objetivo:** ayudarte a crecer de forma orgánica en TikTok, Instagram, Facebook,
YouTube, X, Threads, Snapchat, Pinterest y LinkedIn; no necesitás aparecer
frente a la cámara. SKY no puede garantizar contenido viral ni seguidores.

**Cómo usarlo:**
1. Abrí **Ajustes → ESTUDIO CREATIVO · MIS REDES SOCIALES**, elegí plataforma,
   escribí el tema y mantené marcada «Sin mostrar mi rostro» si lo preferís.
2. Elegí **Crear publicación** o **Plan de 7 días**. Con Gemini configurado,
   SKY prepara un gancho, guion breve, idea de tomas propias o pantalla,
   subtítulos, descripción, cinco hashtags y llamado a la acción; el plan
   incluye ideas diarias y métricas para revisar manualmente.
3. También podés decir **«SKY, preparame un video para TikTok sobre
   curiosidades de Nicaragua sin mostrar mi cara»** o **«SKY dame un calendario
   de siete días para Instagram sobre diseño gráfico»**.
4. SKY muestra un **borrador editable**. Tocá **Copiar texto** o
   **Compartir texto** para abrir el selector oficial de Android. Algunas redes
   no aceptan publicación de video desde texto plano; en ese caso copiá el
   guion y añadí fotos, clips y audio dentro de su app.
5. Revisá y publicá desde tu cuenta personal. **No se publican contenidos ni
   se envían mensajes sin tu autorización.** No se solicitan contraseñas
   sociales ni permisos de lectura de cuentas.

**Crecimiento medible:** revisá semanalmente en las estadísticas oficiales
vistas por publicación, retención/tiempo de visualización, comentarios,
guardados, compartidos y nuevos seguidores. Usá esas cifras para mejorar
ganchos, duraciones, temas y formatos. SKY 0.8.1 **no obtiene esos datos
automáticamente**, no consulta tendencias en tiempo real y no ejecuta
seguimientos, likes o comentarios masivos. Una conexión futura de datos y
publicación directa requerirá permisos OAuth y APIs aprobadas por cada red.

**Privacidad y derechos:** usá material original o con licencia, protegé tu
imagen y la de terceros y evitá música protegida sin autorización. La
generación envía a Gemini el tema que indicás y la plataforma seleccionada;
no transfiere contraseñas de redes sociales ni un inventario de contactos.
La clave Gemini personal sigue protegida en Android Keystore para esta beta
privada; para lanzamiento público se requiere backend autenticado.

---

## Historial técnico (versiones anteriores)

**Estado actual:** beta personal independiente para Android 8.0+ (API 26). Código Kotlin en `mobile/android-agent/app/`, publicado en la rama [`main`](https://github.com/OscarElieser/SKY/tree/main/mobile/android-agent). **SKY Windows permanece sin cambios y su conexión es opcional.**

[**⬇ Descargar APK firmada 0.7.1**](https://github.com/OscarElieser/SKY/releases/download/sky-android-v0.7.1/SKY-IA-Android-v0.7.1-firmada.apk) · [Release y suma SHA-256](https://github.com/OscarElieser/SKY/releases/tag/sky-android-v0.7.1) · [Cómo instalar/verificar APK](apk/README.md) · [Compilación Android](https://github.com/OscarElieser/SKY/actions/workflows/sky-mobile-release.yml)

## Inicio rápido solo con el teléfono

1. Abrí el enlace de descarga desde **Chrome en tu Android**, sin usar el navegador interno si bloquea descargas. Buscá el archivo `SKY-IA-Android-v0.7.1-firmada.apk` en GitHub Releases.
2. Instalá **sobre SKY existente**, conservando la firma; no desinstalés tu app ni borres datos para actualizar. Si Play Protect emite una advertencia de riesgo, no la ignores ni fuerces la instalación.
3. En **Ajustes** ya no necesitás Windows ni Tailscale: el modo independiente inicia con una clave Gemini privada configurada desde el propio teléfono. Tocá **Copiar clave** en [Google AI Studio](https://aistudio.google.com/apikey) y luego **PEGAR CLAVE COPIADA** en SKY. No pegues el nombre del proyecto ni compartas la clave.
4. Marcá la autorización de envío de mensajes a Gemini y elegí **VERIFICAR CLAVE Y ACTIVAR SKY**. Google debe confirmar la clave y el modelo antes de que SKY la guarde cifrada con Android Keystore.
5. Tocá **HABLAR** para iniciar una consulta de voz; el rostro debe permanecer visible. Usá el icono de teclado para abrir el historial de chat.
6. Opcional: **Ajustes → Conversación fluida**, para hasta ocho turnos seguidos mientras la app esté abierta. Tocá **Detener** para parar la escucha/voz. Los permisos de micrófono se solicitan explícitamente.

**Prueba manual recomendada:** «Hola SKY, contame un chiste»; «Abrí YouTube»; «Poné una alarma»; una pregunta libre a Gemini. Confirmá el resultado de cada acción. Si una app, alarma o llamada no se abre realmente, no se considera completada.

## Experiencia premium y capacidades

- **Aura Face:** avatar vertical vectorial 360×590 que se escala a la pantalla; ojos grandes, iris y pupilas móviles, expresiones, parpadeo, boca animada durante TTS y luces que reflejan estados de voz.
- **Pantalla limpia:** cabecera compacta, estado de conversación y barra inferior de hablar/escribir/detener que respeta los márgenes de navegación de Android.
- **Voz natural disponible:** SpeechRecognizer del sistema (puede requerir conectividad según proveedor) y TextToSpeech en español; busca la voz instalada con mejor calidad, pero **no instala voces neuronales ni promete voz humana perfecta**.
- **Conversación por voz con rostro presente:** la pregunta hablada puede obtener respuesta de Gemini sin abrir el panel sobre la cara. El chat escrito mantiene historial accesible.
- **Acciones implementadas:** comandos locales de apps permitidas, notas, alarmas, temporizadores, acompañante y respuestas divertidas. El control irrestricto de redes sociales, mensajes, Word/Excel o videojuegos **no está implementado ni autorizado universalmente**.
- **Seguridad:** clave cifrada en reposo y borrable desde Ajustes; el uso de API directamente en APK es **solo beta personal**. Para una aplicación pública, migrar a un backend autenticado, límites por usuario y protecciones contra abuso.

La comprobación de **GitHub Actions valida compilación, pruebas unitarias, firma y archivo generado**, pero no sustituye pruebas de micrófono, TTS, interacción, batería, conectividad y notificaciones en un Samsung real. La conversación de Gemini necesita acceso a internet; SKY Windows es independiente y opcional.

## Desarrollo, verificación y distribución

- Versión: `0.7.1` · `versionCode=12` · paquete Android `ni.sky.mobileagent`.
- Build Android: `SKY Mobile Android Agent`, para pruebas y compilación de desarrollo.
- Release: `SKY Android Signed Release Candidate`, con firma estable provista por secretos de GitHub, prueba y publicación **automática** de beta como APK descargable en [Releases](https://github.com/OscarElieser/SKY/releases).
- APK `standard`: no declara servicios de Accesibilidad. Variante `assistive`: código separado para revisión de permisos; no se distribuye como APK estándar.
- No guardar claves Gemini, keystores, `.env` ni otros secretos en el repositorio. Consultá [distribución y SHA-256](apk/README.md).

---

## Registro histórico de versiones (para referencia, no instrucciones vigentes)

Las siguientes notas documentan la evolución y pruebas pasadas. Donde aparezca una versión anterior (0.6.x, 0.5.x o inferior), **usá las instrucciones anteriores de esta guía para instalar 0.7.1**.
## SKY Android 0.7.1 — versión premium corregida

La versión 0.7.1 sustituye la beta inicial 0.7.0. Corrige la prioridad
del rostro durante conversaciones por voz (el chat no oculta SKY),
y selecciona preferentemente una voz española de alta calidad si
Android la tiene instalada. Si no hay voces mejores, conserva el motor
TTS estándar. El usuario controla el micrófono y el modo fluido;
el modo fluido nunca permanece activo en segundo plano.

## SKY Android 0.7.0 · Aura Premium (solo teléfono)

- Rostro de SKY rediseñado en Canvas vectorial vertical 360×590:
  ocupa casi toda la altura útil, con fondo aurora, facciones grandes,
  iris expresivos, animaciones de parpadeo, rubor, boca al hablar,
  luces según el estado de voz y gestos táctiles amistosos.
- Se conserva el personaje dibujado (no hay imagen estática ni carcasa
  robótica) y se respetan las capacidades de Android sin tocar Windows.
- Cabecera compacta, estado visible de escuchar/pensar/hablar y
  controles de chat, voz y detener con estilo premium.
- La respuesta a comandos hablados no abre automáticamente el chat
  encima del rostro. Por texto sí se mantiene el historial completo.
- Ajustes: **Conversación fluida** voluntaria, primer plano, hasta
  8 turnos consecutivos. Después se pausa. Se detiene al salir de la
  aplicación o al presionar Detener. Sin micrófono encubierto.
- Se compensa la barra de navegación real con WindowInsets en Android
  15/16 para que los botones inferiores no queden tapados.
- La voz utiliza los motores SpeechRecognizer/TextToSpeech disponibles
  en el teléfono y Gemini si está activado. No es una voz neuronal
  personalizada ni una escucha permanente en segundo plano.
- Se conservan acciones locales, permisos, perfil personal,
  firmas de APK y el backend opcional sin cambiar SKY Windows.

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


## Manos libres Android (0.8.9)

Desde **Ajustes**, habilitá **Manos libres: decir SKY para despertar**. Se solicita
RECORD_AUDIO; un servicio visible de tipo microphone mantiene el reconocimiento
*en el dispositivo* y una notificación permite **Apagar micrófono**. Con la app
abierta, SKY acepta «SKY, abrí YouTube» y preguntas siguientes sin tocar el botón.
«SKY, despertá» inicia conversación; tras 45 segundos sin órdenes, vuelve al
reposo de voz; «SKY, dormí» la deja en reposo, pero **no** apaga el micrófono.
Para apagar el micrófono, usá el botón de detener o la notificación.

Cuando SKY pasa a segundo plano, el servicio escucha la activación y puede
recibir instrucciones, pero **no ejecuta las acciones de Activity en segundo plano**:
muestra una notificación para que el dueño abra la app y continúe la orden.
Se preservan todas las confirmaciones de acciones sensibles.

**Compatibilidad:** requiere Android 12+ (API 31) y un servicio de reconocimiento
de voz local instalado. Si no hay un modelo local compatible, la app conserva
el modo HABLAR manual y no transfiere la activación a un servidor remoto.
El reconocimiento de Android no es un detector DSP de palabra clave de bajo
consumo, por lo que puede gastar batería y ser limitado o detenido por el
fabricante o el sistema; no se promete funcionamiento tras forzar la detención,
reiniciar el equipo ni en todos los dispositivos. En Android 14+, el servicio de
micrófono solo puede arrancar mientras la app está visible. No se permite activar
el micrófono sin consentimiento ni reiniciarlo silenciosamente tras el arranque.
