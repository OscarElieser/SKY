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
