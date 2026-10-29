# SKY IA Android — seguridad por capas y ruta verificable a 100 000 usuarios

Estado: **medidas Android implementadas parcialmente; no existe certificación ni prueba de 100 000 concurrentes**. Esta guía no sustituye pruebas en el Samsung del propietario ni auditoría independiente.

## 1. Distribución segura y Play Protect

- La APK estándar no declara un servicio AccessibilityService, no permite HTTP plano ni copias automáticas y restringe la confianza TLS a las autoridades del sistema.
- La firma de release usa secretos del workflow y jamás una clave escrita en el código. Se publica SHA-256 y huella del certificado; **comparar la huella de firma dentro de SKY (Configuración → Seguridad)** con `signer-fingerprint.txt` del release.
- `scripts/release-security-audit.sh` verifica la APK **compilada** y aborta si encuentra depuración, permisos de alto riesgo, acceso a red en claro o servicios de accesibilidad. El workflow publica solo tras superar pruebas de compilación y emulación.
- **No** se solicita apagar, eludir, neutralizar ni falsear Play Protect. Si hay advertencia: identificar texto exacto y categoría, aceptar el escaneo oficial y corregir problemas verificables. Si Google clasifica la app erróneamente, presentar apelación por canal de desarrolladores: <https://developers.google.com/android/play-protect/warning-dev-guidance?hl=es-419>.
- La distribución por GitHub Releases no equivale a publicación en Play Store ni a certificación. Para distribución masiva: Play Console, firma con Play App Signing, pruebas internas/cerradas, revisión de permisos, política de privacidad y, si corresponde, Play Integrity validada en **backend**. No incrustar secretos de la API en una APK pública.

## 2. Capas de seguridad existentes o añadidas

| Capa | Presente / pendiente | Evidencia |
| --- | --- | --- |
| Android y distribución | Presente para variante estándar, sujeto a CI | APK firmada, sin AccessiblityService, sin permisos invasivos declarados; auditoría en Actions |
| Credenciales locales | Presente | AES-256-GCM y Android Keystore en `PrivateTokenStore.kt`; cifrado en reposo de token y claves |
| Red | Presente | HTTPS sin redirección automática; `sky_network_security.xml` bloquea texto claro y CA de usuario |
| Permisos | Presente, limitado | Un consentimiento revocable para abrir apps bajo orden local. **No** autoriza lectura de contraseñas, envíos o eliminación |
| Antibucle local | Presente | `SkyLocalActionLimiter` evita órdenes duplicadas en 1,5 s y limita a 30 aperturas por minuto |
| Aislamiento IA/herramientas | Presente, limitado | El modelo no obtiene permiso directo para ejecutar comandos Android; solo el analizador de órdenes locales del usuario |
| Auditoría | Presente, limitada | `SkyActionEvidence` distingue solicitud enviada de éxito verificado |
| Acciones destructivas | No completas | Requieren integración por app, autorización separada y capacidad de deshacer/confirmar |
| Antimalware / seguridad ofensiva | No auditada externamente | Sin garantía de ausencia de vulnerabilidades; requiere pentest, SAST/DAST/SCA, monitoreo |
| Control de cuentas a escala | Pendiente | Identidad de usuarios, RBAC por organización, cuotas, servicio de sesiones e infraestructura dedicada |

Los permisos generales nunca deben aceptar instrucciones de páginas web, documentos, correos, chats recibidos, resultados de IA o parámetros remotos como si fueran órdenes nuevas del propietario. Un texto externo puede ser contenido **a analizar**, pero no una autorización.

## 3. Capacidad: 100 000 usuarios simultáneos NO verificados

La cola actual `neural_core/sky_mobile_agent.py` usa **SQLite + RLock local**. Sirve para un despliegue personal limitado, pero no comparte correctamente el estado de la cola entre múltiples réplicas ni prueba alta disponibilidad. No cambiar este componente de SKY Windows dentro del trabajo Android sin plan de migración y autorización.

Cálculos de capacidad preliminares, **no mediciones**:
- 100 000 teléfonos realizando polling cada 30 s ≈ **3 333 solicitudes/segundo**, incluso sin conversaciones. Sustituir polling frecuente por notificaciones push, cola asíncrona y consultas con backoff.
- 100 000 personas realizando una petición de IA por minuto ≈ **1 667 peticiones/segundo** de inferencia. Las cuotas y costos de Gemini/Groq/otros proveedores requieren dimensionamiento y acuerdos reales; sin ellos no se promete respuesta inmediata.
- No todos los usuarios conectados estarán activos; medir *conectados, usuarios activos, RPS, tokens/s y trabajo pendiente* por separado.

### Arquitectura futura necesaria (no desplegada)

1. Android → CDN/WAF/rate limits por IP, dispositivo y cuenta → API Gateway TLS; autenticación de sesión y de dispositivo, tokens revocables, MFA para acciones sensibles y attestation sólo si la distribución lo soporta.
2. API stateless en al menos 2 zonas, réplicas independientes, balanceo y HPA/autoescalado basado en latencia, CPU y profundidad de cola.
3. PostgreSQL administrado en alta disponibilidad para estados durables con índices e idempotency keys; Redis administrado para límites de tasa y estados efímeros; cola durable (Cloud Tasks / Pub/Sub / SQS / RabbitMQ con persistencia) para trabajos de IA y multimedia.
4. Trabajadores con límites de concurrencia por modelo/proveedor, circuit breakers, timeout, presupuesto, reintentos con jitter y colas de errores; cancelar tareas al revocar la cuenta.
5. Datos privados cifrados en reposo, segregación por usuario/tenant, controles de acceso por fila, rotación de secretos y borrado conforme a política; backups probados y restauración medible.
6. Observabilidad sin registrar secretos ni prompts privados: métricas p50/p95/p99, disponibilidad, errores, saturación, colas, costos y alertas. Procedimiento de incidentes, recuperación y pruebas de caos.

### Puertas de aceptación antes de decir «100 000»

- Ejecutar `ops/staging-load.k6.js` **sólo** en HTTPS staging aislado, con token de prueba, primero con 10–100 usuarios virtuales. Mide resultados reales (HTTP 200, p95 menor de 1,5 s y error menor de 1 %) de `home-status` únicamente: no infiere capacidad de chat ni voz.
- Crear una prueba completa por pasos con **1 000 → 10 000 → 100 000 conexiones** y mezcla real de chat, voz, archivos, acciones Android y cargas multimedia; aumentar sólo tras aprobar la etapa anterior y contar con presupuesto y protección del entorno.
- Verificar explícitamente p95/p99 por operación, errores menores del 1 %, fallos por zona, desconexiones, reintentos, recuperación de base de datos, pruebas de restauración y estabilidad prolongada. Definir SLOs con el propietario y proveedor.
- Validar permisos y flujos en el **Samsung físico**; el emulador no sustituye pruebas de micrófono, bloqueo de pantalla, OEM y Play Protect.

## 4. Matriz de pruebas de ataques

- Inyección de prompt desde archivo/página/mensaje intentando abrir apps, exfiltrar claves o aceptar permisos → **no se ejecuta**; se trata como dato.
- Órdenes duplicadas/micrófono retransmitido → limitador y evidencia de rechazo.
- APK manipulada o firmada con otra clave → huella distinta; el usuario no debe instalarla ni ignorar advertencias.
- HTTP, certificado CA local agregado, redirección de endpoint → conexión rechazada.
- Token de dispositivo revocado, caducado o equivocado → 401; no hereda privilegios del propietario.
- Publicar/eliminar/modificar datos fuera de SKY → no permitido sin capacidad y confirmación explícita.
- Saturación y fallo de un proveedor de IA → degradación controlada, no fallo global (pendiente de infraestructura).

## 5. Qué NO se promete

No se ha eliminado Play Protect. No se ha certificado la APK en Google Play. No se ha demostrado control universal de otras apps. No se han probado 100 000 usuarios simultáneos ni se ha desplegado la arquitectura anterior. Cualquier informe de pruebas debe incluir SHA del commit, APK, dispositivo/emulador, parámetros de carga, resultados y errores.
