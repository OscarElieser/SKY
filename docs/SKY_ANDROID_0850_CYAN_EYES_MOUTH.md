# SKY Android v0.8.50 · Ojos y boca cyan animados

**Tipo:** candidato beta Android | **Estado inicial:** pendiente de CI y pruebas en Samsung  
**Referencia visual:** solamente círculos luminosos cyan y sonrisa del ejemplo facilitado por el propietario; **no se incorpora imagen de terceros** ni recursos de Dreamstime.

## Qué cambió

- Se modificó el renderizado nativo `SkyFriendlyEyesView.kt`; usa exclusivamente `Canvas` con **dos ojos circulares cyan y una boca cyan**.
- Sin cabeza, borde robot, cejas humanas, nariz, mejillas, imágenes externas, marcas de agua ni descargas de imágenes.
- Ojos con parpadeo periódico, microbalanceo, mirada suave, halo luminoso y apertura dependiente de estado/emoción.
- Boca sonriente que cambia según la expresión; durante `SPEAKING` se abre y cierra con ritmo animado. Esto es **animación aproximada**, no sincronización fonética real.
- Se conservan y respetan `IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `SLEEPING`, `ERROR`; las expresiones existentes (11 estados) y los gestos de bailar, saltar, correr y girar siguen usando los mismos métodos públicos.
- Se conserva el control de voz mediante `SkyEyeVoicePanel` sin cambiar el micrófono ni los permisos, y la opción de tocar los ojos o mantenerlos en modo manos libres.
- El dibujo es local y se suspende cuando la vista no es visible; en `SLEEPING` su refresco es menos frecuente.

## Conservación funcional

- La rama parte de la fase de asistente #109 y, por tanto, incluye además los comandos del teléfono del #108, sin borrarlos.
- No se modifican rutas del servidor, SKY Windows, API propia, memoria, bases de datos, historial, conexiones privadas, reproducción, notas, chat, adjuntos, controles del teléfono ni opciones de accesibilidad.
- Se preservan el mismo `applicationId = ni.sky.mobileagent` y la firma de release prevista. `versionCode` sube a **63** y `versionName` a **0.8.50**, necesarios para actualizar desde la versión 0.8.47.
- Las mejoras de Android 0.8.48 (PR #105) y del motor IA (PR #107) **siguen en sus ramas separadas; no se eliminan ni se declaran integradas en esta beta**.

## Validación obligatoria

1. Construir `assembleStandardDebug`, ejecutar `testStandardDebugUnitTest` y el control del manifiesto de la APK estándar.
2. En emuladores API 35 y 36 ejecutar pruebas `connectedStandardDebugAndroidTest`, incluida `SkyCyanEyesMouthRuntimeTest`: fondo transparente fuera del rostro, ojos y boca visibles, y modos renderizados de forma diferente.
3. Hacer `assembleStandardRelease` con la **clave privada original** desde secretos GitHub (nunca generar una nueva clave para distribuir como actualización).
4. Comprobar firma y huella, SHA-256, Play Protect y actualización 0.8.47 → 0.8.50 sin pérdida de datos.
5. Samsung físico: pantalla en reposo, parpadeo, emociones, respuesta a voz y reproducción, ahorro de batería, manos libres, apertura de apps, llamadas/SMS/mapas, recordatorios y opciones de asistente.
6. No afirmar que todas las acciones de otras aplicaciones se completaron sin pruebas de campo y evidencia de estado.

## Flujo de publicación

La rama y su pull request sirven para pruebas de regresión; GitHub Actions de `sky-mobile-agent.yml` publican un archivo de prueba **debug** vinculado al commit. La release beta **firmada** solo debe publicarse con `sky-mobile-release.yml` sobre `main`, después de integrar cambios revisados y pasar validaciones. No instalar una APK debug encima de una instalación con firma release.
