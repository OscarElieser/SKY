# SKY Android 0.8.43 — corregir riesgo de permisos y validar instalación

**Estado (30/10/2026, Nicaragua):** cambio de manifiesto y pruebas en código. No se declara instalación aprobada por Google Play Protect hasta comprobarla realmente en el Samsung. Este trabajo no desactiva, engaña ni elude Play Protect.

## Diagnóstico confirmado en 0.8.42

El binario estándar incluye desde `app/src/main/AndroidManifest.xml` el servicio `SkyPlaybackProofListener` registrado como `android.service.notification.NotificationListenerService`, protegido por `android.permission.BIND_NOTIFICATION_LISTENER_SERVICE`. Google explica oficialmente que las aplicaciones descargadas desde Internet con acceso a notificaciones, SMS o accesibilidad pueden quedar bloqueadas en instalación lateral. Su texto coincide con la captura del usuario: «Esta app puede solicitar acceso a datos sensibles...». Este hallazgo es un **factor verificable y corregible**, no prueba de que Google no detecte otros riesgos. Fuente: https://developers.google.com/android/play-protect/warning-dev-guidance?hl=es-419

## Corrección de seguridad

1. **Standard release**: elimina completamente la declaración del listener sensible del manifiesto común. Se mantienen Internet, reconocimiento de voz con notificación de micrófono, archivos mediante el selector del sistema, chat, controles Android permitidos y APK con el mismo `applicationId`.
2. **Assistive experimental**: conserva el servicio de comprobación musical y sus servicios de accesibilidad en un manifiesto de *flavor* separado. **No se distribuye** como APK estándar ni se activa desde esta publicación. No implica autorización comercial para controles de accesibilidad.
3. UI: explica la limitación de verificación de reproducción en el producto estándar. Envío de órdenes y apertura de reproductor **no equivalen** a reproducir sonido comprobado.
4. La auditoría de APK firmada ahora falla si encuentra `SkyPlaybackProofListener`, `BIND_NOTIFICATION_LISTENER_SERVICE`, `NotificationListenerService`, servicios de accesibilidad, SMS o permisos amplios innecesarios. El test instrumentado inspecciona servicios **del APK instalado**, no solo código fuente.
5. Actualización `versionName=0.8.43`, `versionCode=56` con el mismo paquete y firma de release que el CI resguarda. **No cambiar la clave de firma**: verificar digest del certificado antes de instalar sobre 0.8.41/0.8.42.

## Checklist para publicar

- [ ] Pruebas unitarias Kotlin y backend Python aprobadas **en el mismo commit**.
- [ ] APK estándar RELEASE realmente firmada; comprobar `apksigner verify --print-certs`, `aapt dump permissions` y `aapt dump xmltree`.
- [ ] Emulator API 35 y 36 ejecuta `SkyPlaybackProofRuntimeTest` y pruebas de regresión (no equivale a Samsung real).
- [ ] SHA256 APK, fingerprint, versionCode/versionName y commit identificados en Actions y Release.
- [ ] Instalar desde el canal previsto en Samsung Android 16 **sin desactivar Play Protect** y registrar resultado exacto.
- [ ] Probar actualización sin pérdida de historial/base de datos, voz manos libres, abrir YouTube/Spotify, archivos, modelo SKY API privada y consentimientos.
- [ ] Si persiste el bloqueo tras auditoría, **no forzar instalación**: documentar resultado y presentar apelación oficial de Play Protect. No recomendar instalar APK con alertas ignoradas.

## Próximo trabajo P0

Consolidar real `Ollama` (respuesta académica extensa, trazas de tokens y modelo real); voz/audio y archivos Samsung; seguridad multiusuario y rendimiento medidos, sin tocar SKY Windows ni BAQUEANO. Referencia: `docs/SKY_P0_ACADEMIC_32K_2026-10-30.md`. Una nueva APK no certifica ninguno de esos aspectos hasta obtener evidencia física.

**Política de lanzamiento**: la versión 0.8.43 es una candidata de beta personal, no una autorización de comercialización, ni garantía de superar Play Protect; respetar la evaluación independiente de Google.
