# SKY Android 0.8.48 — diagnóstico legible y estados reales en Samsung

## Origen comprobado

Capturas de SKY 0.8.47 instalado en Samsung SM-S711U / Android 16 API 36 muestran:
- Mensaje de chat: «Para usar tu SKY API primero autorizá el chat del servidor HTTPS desde Ajustes. No se cambiará automáticamente a Gemini».
- Micrófono permitido, motor de reconocimiento local disponible, pero servicio manos libres **no** vivo y reconocedor **no** escuchando.
- Modo guardado `WAKE_ONLY` que por sí solo no prueba activación del servicio.
- TTS «Lista» que no certifica sonido audible.
- Ventana del diagnóstico extensa cuyos botones inferiores se cortan visualmente; multimedia 4/15 sin verificación acústica.

No hay evidencia de que el usuario tenga el consentimiento hands-free activado ni de que la API esté desplegada; ningún cambio debe fingir esas condiciones.

## Cambios en el código

1. **Pantalla legible**: el diagnóstico usa `ScrollView` con altura acotada y controles separados en vertical: autorizar/comprobar SKY API, iniciar/reiniciar manos libres explícitamente, control multimedia, copiar diagnóstico y cerrar. Sin descartar datos personales o el historial.
2. **Estados comprobables**: separa consentimiento voluntario, disponibilidad de SpeechRecognizer, estado vivo del servicio, reconocimiento realmente activo y configuración de chat HTTPS; `WAKE_ONLY` deja de parecer prueba de escucha.
3. **Servicio de voz**: el retorno de `startForegroundService` no significa inicio satisfactorio. Se muestra «iniciando», luego se consulta `SkyHandsFreeService.health()` y solo entonces se refleja un servicio activo. Al volver a la app, la UI consulta el servicio y no confunde `hands_free_opt_in` con ejecución real.
4. **Autorización privada**: el aviso HTTPS del chat incluye botón a Ajustes mediante el callback existente, sin instalar servidores, compartir claves o activar Gemini por sorpresa.
5. **Versión candidata**: `versionName=0.8.48`, `versionCode=61` preservando package, firma y datos actuales en actualizaciones Android válidas.
6. **Test unitario**: la política de mensaje distingue avisos de autorización de resultados normales.

## Verificación exigida antes de distribuir

- CI de Android standardDebug/standardRelease, pruebas Kotlin y Android 15/16; revisión del manifiesto y de la firma existente. **Sin CI verde, no distribuir.**
- En Samsung: abrir «Autodiagnóstico Android», desplazarse hasta el final, utilizar todos los botones y comprobar con tamaño de letra grande y teclado visible que nada queda cortado.
- Con manos libres previamente desactivadas: verificar que el diagnóstico muestre «consentimiento no concedido» y «servicio no vivo». Al pulsar «Activar / reiniciar manos libres», observar notificación persistente y dos estados reales (servicio, reconocedor). Probar diez turnos, pausa, pantalla bloqueada, parada desde notificación y reanudación. **No declarar siempre encendida o biometría de propietario sin pruebas.**
- Con el chat HTTPS sin token autorizado: pulsar «Abrir Ajustes · autorizar SKY API» desde el aviso del chat y comprobar que no se envía el borrador ni se usa Gemini silenciosamente.
- Con HTTPS y token realmente emparejados: consultar `/api/sky/mobile-chat/status` y demostrar al menos una respuesta real del modelo con `operation_id`, latencia y ausencia de proveedor externo inesperado.
- Multimedia: medir volumen y reproducir audio real; un nivel 4/15 no demuestra audibilidad.
- Comprobar permisos, Play Protect activo, archivos, respuestas académicas, historial, memoria, exportación y ausencia de regresiones en la misma APK firmada.

## Seguridad y límites

El servicio de micrófono solo se inicia por interacción visible/autorizada, respetando las restricciones Android 14–16 para foreground service y permisos while-in-use. No se eluden restricciones de Android, Play Protect, biometría, bloqueos ni autenticación. **No se modifica SKY Windows ni BAQUEANO.** La conexión a Ollama necesita un servidor realmente disponible, con HTTPS, token limitado y verificación de un modelo. El repositorio por sí mismo no prueba que ese servicio exista.

**Estado:** corrección en rama y PR de revisión; no equivale a APK compilada, instalada, probada ni a producto comercial validado.

## Independencia de Android frente a SKY Windows y HTTPS (10/11/2026)

El HTTPS **no es requisito de la app Android** para ejecutar herramientas locales; solo protege la conexión cuando se selecciona voluntariamente una API remota. SKY Windows permanece independiente y no se modifica.

Hallazgo verificado en el flujo `MainActivity.sendChatText`: un dispositivo podía tener token histórico de SKY Core y llegar a la rama genérica `SkyNetwork.requestChat(...)` aunque se hubiese desactivado `prefer_self_hosted_ollama`. Esto producía una dependencia remota oculta.

Corrección de enrutamiento:
- `prefer_self_hosted_ollama` tiene valor por defecto **false** en Ajustes y envío. Los consentimientos guardados previamente no se eliminan ni cambian.
- Si se selecciona expresamente SKY API, sigue requiriendo emparejamiento y autorización HTTPS (sin fallback a nube oculta).
- Si no se selecciona SKY API, los tokens previamente emparejados **no autorizan** conexiones al servidor. Se aceptan como motores independientes solo Gemini/Groq que el propietario haya configurado.
- Si no hay motor generativo autorizado, SKY informa lo que falta y conserva la consulta en el editor; no inventa un LLM local ni remite la consulta a Windows.
- Se elimina la rama genérica de chat que intentaba un `requestChat` al servidor sin una ruta verificada.
- La UI ofrece una prueba de respuesta local (hora del teléfono), que **no** equivale a LLM ni demuestra comprensión generativa offline.
- El diagnóstico distingue el modo Android independiente de la API privada opcional.
- Tests de `SkyOwnApiRoutingPolicyTest` cubren tokens históricos, elección voluntaria de API privada, Gemini/Groq configurados y ausencia total de motor generativo.

**Límite vigente:** la APK actual no lleva un modelo generativo nativo en Android. Operaciones locales como el reconocimiento de voz y los comandos locales pueden funcionar independientemente; cualquier función dependiente de nube, búsqueda actualizada, servidor o API necesita las condiciones reales respectivas. Para investigación/tesis y respuestas abiertas sin internet, se necesita una implementación y prueba separadas de modelo local compatible con el hardware. No degradar esto a respuestas enlatadas presentadas como IA.

Aceptación: pruebas de Android y backend verdes, ausencia de conexiones privadas en modo independiente (prueba con servidor inalcanzable), consulta no local con ningún proveedor debe conservar el borrador, prueba con clave configurada y consentimiento, prueba de aviso de SKY API seleccionada sin autorización, Play Protect y prueba física de Samsung. No afirmar «funciona al 100 %» por pasar tests estáticos.


## Refuerzo de diagnósticos e indicadores (10/11/2026)

Se verificó un problema adicional de representación: `SkyMobileHome.setConnection` pintaba un punto verde y mostraba «Android lista»/«SKY vinculada» basándose en credenciales guardadas, **no en un resultado HTTP real**. Por otra parte, el caption mostraba «SKY durmiendo» siempre que el servicio manos libres estuviese activo, incluso cuando `sky_presence_mode=ATTENTIVE`.

Correcciones en esta rama:
- Nueva `SkyAndroidStatusPolicy` con pruebas unitarias: separa funciones locales disponibles, API privada seleccionada pero sin autorizar, API privada configurada sin verificación en vivo y motor externo configurado sin prueba de conexión.
- El indicador deja de utilizar el punto verde como prueba de conectividad: usa señal neutra hasta que exista una comprobación en vivo. Un emparejamiento histórico de Windows no implica conexión.
- Los captions de voz usan el modo solicitado `SLEEP_LOCKED`, `ATTENTIVE` o `WAKE_ONLY`, y estado real de servicio. «Activo» no equivale a «captó una frase».
- `SkyHandsFreeService.health().recognizing` solo es verdadero tras `RecognitionListener.onReadyForSpeech`, y se anula al detener el reconocedor o al suspender voz para TTS. La mera solicitud `startListening()` ya no se interpreta como éxito. El callback significa que el motor está preparado, no que exista una transcripción reconocida.
- El diagnóstico Android etiqueta esta distinción para que no aparezca «escuchando» sin la confirmación del motor.
- La UI actualiza el estado del motor cuando el propietario activa o desactiva la API privada; no modifica las credenciales ni elimina los ajustes anteriores.

**Aceptación:** CI completo Android en el commit final y prueba física Samsung Android 16. Comparar prueba con modo atenta/dormida, cambio de opciones sin red, arranque/suspensión de micrófono, reconocimiento que entrega respuesta real y notificación persistente. Probar que la UI nunca afirma servidor «en línea» sin efectuar un health check autenticado. No declarar lista una APK de depuración.
