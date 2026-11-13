# SKY Android — selección explícita de IA directa (13/11/2026)

## Qué se implementó
SKY Android permite elegir en **Ajustes → Motor de IA en Android**:
- **Automático inicial**: Groq, si existe clave configurada; si no, Gemini.
- **Solo Groq**: no cambia a Gemini si Groq falla, no hay red o se agota la cuota.
- **Solo Gemini**: no cambia a Groq si Gemini falla, no hay red o se agota la cuota.

La elección se guarda en `sky_mobile_provider/preference` y se consulta una sola vez por turno. La respuesta conserva la procedencia del proveedor. No hay reintentos cruzados entre proveedores para chat ordinario: una excepción devuelve error veraz y `home.failSending` conserva el texto. Configurar ambas claves **no equivale** a autorizar una doble solicitud.

Los modos de Gemini pedidos explícitamente y las consultas que necesitan búsqueda con fuentes verificables conservan sus protecciones; **Groq no suplanta la verificación web**. El modo privado `sky_auto` de SKY API mantiene de forma independiente sus permisos y enrutamiento de respaldo aprobados, sin modificación.

## Alcance y límites de gratuidad
La política evita gastar cuota de **otro proveedor** en un reintento automático. **No puede certificar que una clave Groq/Gemini concreta tenga coste cero**, ni ampliar límites o garantizar conexión. El propietario debe comprobar los planes y activar presupuestos y alertas en sus cuentas. El algoritmo no compra créditos, no elude HTTP 429 ni reemplaza la selección tras un fallo.

Sin un modelo generativo local validado en el teléfono, el chat abierto sin red necesita servidor autorizado o servicios externos: SKY debe explicarlo, no fingir generación IA offline. Los comandos locales y respuestas locales existentes permanecen independientes.

## Cambios limitados
- `SkyMobileProviderPolicy.kt`: selección determinista y fallo cerrado.
- `MainActivity.kt`: selector visible y uso real de la elección en chat.
- `SkyMobileProviderPolicyTest.kt`: prioridad, preferencia explícita, límites de investigación y ausencia de cambio tras fallo.

No modificar SKY Windows, BAQUEANO, contraseñas, versiones, firma, historial ni permisos existentes. Esta rama depende del candidato Android 0.8.48 (PR #105); no equivale a una release 0.8.49.

## Verificación
1. Configurar ambas claves válidas y elegir «Solo Groq». Una pregunta ordinaria debe usar Groq. Con fallo de Groq, observar que la consulta se conserva y no se llama a Gemini.
2. Elegir «Solo Gemini». Una pregunta ordinaria debe usar Gemini. Con cuota agotada o red fallida, no se llama a Groq.
3. Elegir automático. Con ambas claves, la elección inicial es Groq. Si no está configurado, se elige Gemini; **no cambia a otra clave después de empezar el turno**.
4. Elegir un proveedor **sin clave configurada**: presentar error de configuración antes de enviar y conservar el mensaje.
5. Pedir investigación con fuentes reales: no derivar a Groq por falta de Gemini y no inventar citas.
6. Comprobar consentimiento privado de SKY API, manos libres, reconocimiento, TTS, archivos, historial, sin red y recuperación de sesión.
7. Ejecutar `gradle -p mobile/android-agent :app:testStandardDebugUnitTest :app:assembleStandardDebug --no-daemon` y validaciones de seguridad. **No distribuir APK hasta validar el Samsung Android 16, Play Protect, audio real y firma de distribución.**

## Puertas de salida
- Código revisado + CI del commit final en verde.
- Prueba física Android 16 en Samsung con evidencias de uso y ausencia de redirección de datos.
- APK de release con la firma real y verificación de hash.
- Solo después de esas puertas: plantear siguiente versión. No publicar como funcional al 100 % por pruebas unitarias aisladas.

Relacionados: #105 (correcciones P0 0.8.48), #106 (hoja de ruta de herramientas).
