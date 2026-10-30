## Respuestas Instagram supervisadas · servidor v18 (30/10/2026)

**Hecho:** Supabase Edge Function `sky-instagram` versión **18**, con lectura, comprobación de permisos y nuevas rutas `POST /mobile-reply-prepare`, `POST /mobile-reply-confirm`, `GET /mobile-reply-status`. También se creó `public.sky_instagram_outbound_approvals` con RLS habilitado, sin políticas públicas y permisos solo para `service_role`. La tabla conserva hashes de texto y referencias, **nunca el cuerpo de la respuesta ni tokens Meta**.

**Estado de producción:** el envío de mensajes está **DESACTIVADO por defecto** y la variable `SKY_INSTAGRAM_OUTGOING_ENABLED` no se habilita durante estas pruebas. El código de envío existe y se puede probar de forma controlada, pero **ningún mensaje se ha enviado desde SKY**; no debe presentarse como función de envío validada hasta la prueba real autorizada. En el primer despliegue, `sky_instagram_outbound_approvals` tenía **0 registros y 0 envíos**.

**Flujo de consentimiento en SKY Android (sin botones nuevos):**
1. «SKY, prepara respuesta al último mensaje de Instagram»: consulta un evento real y, para compartirlo con Groq/Gemini, pide permiso explícito; si el propietario no lo autoriza, genera borrador local.
2. SKY lee y muestra el borrador. «Cambia la respuesta por...» permite corrección; «copia la respuesta» conserva opción manual.
3. «Sí, envíala» autoriza **únicamente el texto vigente** y el evento original. La app envía una solicitud `prepare` usando su credencial revocable, cifrada en Android Keystore. No acepta un ID de destinatario escrito por el usuario.
4. El servidor verifica el evento Meta autenticado, identidad profesional y Page con tarea `MESSAGING`, token no vencido, ventana conservadora de 23 h y longitud máxima de 950 caracteres/1000 bytes; devuelve un `approval_id` de 2 minutos. Si la función sigue desactivada, **no consume aprobación ni envía nada**.
5. Solo la confirmación autorizada y coincidente con el SHA-256 del borrador provoca un intento de `POST https://graph.facebook.com/v26.0/{page-id}/messages` con Page token mantenido en Supabase. La transición atómica `prepared -> sending` impide repeticiones concurrentes. Meta debe devolver ID de mensaje y destinatario exactos para reconocer `sent`. Ante un error o timeout el estado es `failed`/`unknown`: **sin reintentos automáticos**.
6. `/mobile-reply-status` permite recuperar el último estado con la credencial del dispositivo y sin revelar mensajes. La integración de consulta de estado en la UI y el manejo de cierre inesperado deben probarse antes de activar producción.

**Corrección importante de fecha de webhook:** Meta puede enviar `timestamp` en **milisegundos**; el receptor ya convierte tanto segundos como milisegundos. Los dos primeros mensajes se almacenaron sin `event_at` y por seguridad **no autorizan un envío**; se necesitará una nueva prueba de DM desde la otra cuenta cuando la APK esté lista, sin modificar la conexión ni los webhooks existentes.

**Activación posterior, solo con aprobación del propietario y evidencia:**
- [ ] CI: pasar `deno check` y pruebas Node de seguridad para el gateway, unit tests Kotlin, build firmada y emuladores Android 15/16.
- [ ] Verificar Meta App Review/roles, ventana de 24 h, Page token y tarea `MESSAGING` sin revelar secretos.
- [ ] Probar en Samsung con un **mensaje de prueba nuevo**, borrador, corrección, aprobación y respuesta. No enviar test DM sin autorización concreta del usuario para el texto y cuenta.
- [ ] Revisar el comprobante de Meta y que un segundo «envíala» **no** provoque duplicado, además de denegación, expiración y corte de red.
- [ ] Solo después habilitar el secreto de producción `SKY_INSTAGRAM_OUTGOING_ENABLED=true` en el proyecto autorizado y validar nuevamente. Si algo falla, restablecerlo a `false`.
- [ ] Auditar límites por dispositivo, RLS, métricas sin contenido personal y controles de revocación.

La app seguirá pudiendo **leer, avisar y preparar borradores** aun cuando el envío esté deshabilitado. No se modifica SKY Windows ni BAQUEANO.


## SKY Android 0.8.32 · bandeja real de Instagram (30/10/2026)

- **Prueba Meta → Supabase confirmada:** el webhook verificado registró **2 mensajes reales** para la cuenta profesional autorizada, con identificadores de evento válidos, estado `received` y recepción alrededor de las 07:58 (Nicaragua). Se comprobó en `sky_instagram_webhook_events`, sin guardar el contenido de conversaciones en este documento.
- **Implementación Android en `main`:** nueva opción «Bandeja de mensajes de Instagram» dentro de «Conexión segura»; lectura privada de `GET /mobile-profile` y `GET /mobile-events` con credencial revocable del dispositivo, guardada en Android Keystore. El teléfono **no recibe** secretos de Meta o de propietario. Se valida el ID numérico de la cuenta ante cada lectura.
- **Interfaz real:** diseño nocturno/cian con conversaciones agrupadas por identificador de remitente abreviado, contenido real de eventos, hora local de recepción y botón Actualizar. Refresco cada 30 segundos solo con la ventana abierta. No se fingen nombres, estado «no leído» ni un historial completo: el servidor entrega hasta 50 eventos recientes.
- **Política de seguridad:** bandeja de solo lectura. No responde automáticamente, no modifica publicaciones ni realiza acciones fuera de los permisos autorizados. Permisos y datos de BAQUEANO y SKY Windows permanecen intactos.
- **Pruebas Android:** `SkyInstagramInboxRulesTest` cubre aislamiento por cuenta, exclusión de eco propio y representación segura de mensajes sin texto. **Compilar y pasar CI no equivale a validación física en el Samsung**; antes de distribuir se requieren prueba de instalación firmada, conexión con la cuenta real, actualización de bandeja y revocación.
- **Siguiente fase (no implementada):** nombres reales de remitentes mediante API oficial cuando estén disponibles; lectura confirmada/no leídos, paginación, redacción supervisada y envío real de respuestas requieren endpoints, permisos y pruebas adicionales.



### Estado técnico Meta → SKY (29/10/2026)

- **Comprobado:** Meta verificó el webhook HTTPS y entregó una solicitud de prueba que Supabase registró con HTTP 200 (la prueba fue anterior al despliegue v16).
- **Desplegado:** Supabase Edge Function `sky-instagram` versión **16** y código en `main`. La función valida HMAC-SHA256 sobre el cuerpo original antes de guardar eventos.
- **Implementado:** tabla privada `sky_instagram_webhook_events` (RLS y sin permisos públicos); normalización mínima de mensajes, comentarios y menciones, identificación de duplicados por hash, lectura autenticada por `GET /events` (propietario) y `GET /mobile-events` (dispositivo previamente vinculado). No se almacenan solicitudes de prueba con envoltura `sample`.
- **Comprobado:** la tabla permite escritura y lectura por `service_role`, las cuentas `anon` y `authenticated` no tienen lectura, y el ensayo SQL en transacción se revirtió sin dejar mensajes ficticios.
- **Aún no verificado:** un mensaje auténtico entregado a v16, suscripción activa de campos en Meta, suscripción de la cuenta profesional cuando Meta la requiera, revisión de aplicación, interfaz de bandeja Android, publicación/respuestas automáticas y pruebas completas en teléfono.
- **Seguridad:** no modificar SKY Windows ni BAQUEANO; los tokens OAuth continúan cifrados en Supabase. Nadie debe copiar App Secret, verify token ni el token de propietario en repositorios, APK o capturas.
- **Próximo ensayo:** activar en Meta únicamente los campos `messages` y `comments` cuando se habilite la cuenta, enviar un DM desde otra cuenta autorizada y comprobar que la tabla tenga un registro real. La plantilla de Meta prueba transporte, no persistencia de un mensaje real.

# SKY Android — Supabase exclusivo para Instagram

## Proyecto objetivo

- Proyecto indicado por el propietario: `jojzuaeqmjgnqikpnfxk`.
- Dashboard: https://supabase.com/dashboard/project/jojzuaeqmjgnqikpnfxk
- **No usar BAQUEANO**: la base de datos y las claves de esa aplicación quedan intactas.
- Estado de entrega verificado el 28/10/2026: **función `sky-instagram` activa (versión 7), URL `/health` con `ready:true`, OAuth autorizado y token cifrado almacenado**.
- La cuenta profesional seleccionada fue autorizada en Meta y el backend verificó el token; **aún falta verificar programáticamente el perfil de Instagram y conectar SKY Android**.
- La cuenta Meta del usuario tiene el caso de uso *Instagram API (Unified Login)*.

## Direcciones del backend desplegado

- Retorno OAuth: `https://jojzuaeqmjgnqikpnfxk.supabase.co/functions/v1/sky-instagram/callback`
- Verificación de webhook: `https://jojzuaeqmjgnqikpnfxk.supabase.co/functions/v1/sky-instagram/webhook`
- Salud: `https://jojzuaeqmjgnqikpnfxk.supabase.co/functions/v1/sky-instagram/health`

**Comprobado el 28/10/2026:** la URL HTTPS de retorno está registrada en Meta, `/health` respondió `ready:true` y un ciclo OAuth finalizó exitosamente. La respuesta de salud por sí sola **no** acredita la identidad del perfil ni capacidades reales de Android.

## Despliegue seguro

1. Autorizar el proyecto nuevo en el conector Supabase o vincularlo con la CLI oficial (no cambiar la conexión de BAQUEANO).
2. Aplicar `supabase/sky_instagram_schema.sql` **solo** en el proyecto `jojzuaeqmjgnqikpnfxk`; confirmar RLS activo y privilegios de `anon`/`authenticated` revocados. Ningún cliente público puede leer tokens.
3. Desplegar `supabase/functions/sky-instagram/index.ts` como la función `sky-instagram`, con `verify_jwt=false` **solo porque** los webhooks y callbacks requieren acceso externo y los endpoints de propietario tienen autenticación fuerte propia. No habilitar otros endpoints públicos.
4. Probar `/health`: debe responder JSON con el nombre del servicio y `ready:false` si no hay configuración secreta.
5. Copiar **solo** el retorno OAuth HTTPS desplegado en Meta → Instagram API → Unified Login → URI de redirección; guardar. Meta generará la URL de inicio de sesión oficial.
6. Añadir **secrets privados en Supabase → Edge Functions → Secrets**, **nunca** en GitHub, capturas, APK ni chat:
   - `SKY_META_APP_ID`: App ID de Meta (es público).
   - `SKY_META_APP_SECRET`: secreto Meta, confidencial.
   - `SKY_META_LOGIN_URL`: URL de inicio de sesión generada por Meta después de guardar la URL de redirección; debe incluir `config_id` y la URI exacta.
   - `SKY_INSTAGRAM_OWNER_KEY`: clave aleatoria fuerte de al menos 32 caracteres para peticiones autenticadas del propietario.
   - `SKY_INSTAGRAM_ENCRYPTION_KEY_B64`: **32 bytes aleatorios**, codificados como base64, exclusivamente en Supabase.
   - `SKY_INSTAGRAM_WEBHOOK_VERIFY_TOKEN`: cadena aleatoria de 24 caracteres o más para el futuro webhook.
   - `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` son variables inyectadas por la plataforma, no hay que compartirlas.
7. Confirmar `/health` con `ready:true` y después realizar un inicio OAuth desde un cliente propio autorizado: `POST /start` con `Authorization: Bearer <owner key>` devuelve `authorization_url`. **Esa URL es sensible durante su vigencia**; abrirla solo desde el teléfono del propietario.
8. Después del consentimiento, el callback canjea el código y verifica la firma lógica del token con Meta antes de almacenarlo cifrado. `GET /status`, con autenticación del propietario, **nunca devuelve el token**.
9. No activar mensajes, publicación ni webhook hasta validar ID de cuenta, permisos concedidos, expiración y pruebas reales. El receptor de webhook actual **solo verifica y confirma la entrega; no almacena ni procesa eventos**.
10. Para desconectar: `POST /disconnect` autenticado elimina el registro local cifrado; además hay que revocar la autorización dentro de Instagram, ya que borrar el registro local **no revoca automáticamente el token en Meta**.

## Seguridad

- La tabla `sky_instagram_connections` usa AES-GCM con IV único; no almacena tokens sin cifrar.
- Estado OAuth aleatorio de un solo uso y caducidad a 10 minutos para reducir ataques de repetición.
- Los endpoints de estado y desconexión requieren clave del propietario. Los webhooks deben venir firmados con el secreto de Meta.
- Nunca imprimir URL completas que contengan `code` o `state` OAuth ni registrar cuerpos de webhooks de terceros.
- Mantener siempre acceso mínimo y evitar permisos publicitarios si SKY no los utiliza.
- No reusar el token de prueba compartiéndolo por chat o dentro de la APK.
- `Instagram OAuth` no implementa autenticación de Windows y **no modifica SKY Windows**.

## Evidencia confirmada y pendiente (28/10/2026)

- **Confirmado:** proyecto SKY-IA `jojzuaeqmjgnqikpnfxk` accesible por el conector, independiente de BAQUEANO.
- **Confirmado:** tablas privadas creadas; ambas con RLS habilitado y sin políticas públicas.
- **Confirmado:** función `sky-instagram` activa, `verify_jwt=false`, `/health` con `ready:true`.
- **Confirmado:** URL de retorno registrada en Meta y secretos configurados exclusivamente en Supabase.
- **Confirmado:** OAuth completado; registro `owner` con `verified_at=2026-10-28T22:57:02.453Z`, token cifrado y vector AES-GCM presentes; estado OAuth consumido una sola vez.
- **Permisos de token observados:** `instagram_basic`, `instagram_manage_comments`, `instagram_content_publish`, `instagram_manage_messages`, `public_profile`.
- **Pendiente:** identificar y validar programáticamente el perfil exacto de Instagram, verificar acceso API real, ciclo de vida y expiración/renovación del token (`token_expires_at` no informado).
- **Pendiente:** implementar en Android autenticación de usuario/dispositivo y consulta de estado sin incrustar `SKY_INSTAGRAM_OWNER_KEY` en APK, más pruebas reales en teléfono.
- **Seguridad a revisar:** el linter reporta `public.rls_auto_enable()` SECURITY DEFINER con permisos de ejecución públicos; evaluar revocación sin afectar el event trigger.

Los tokens, claves privadas y URLs temporales con `code`/`state` no deben copiarse al repositorio ni a incidencias.

## Renovación desde Android (SKY 0.8.31)

La configuración de Meta se actualizó el 29/10/2026 para añadir la selección de Páginas y los permisos `pages_show_list` y `pages_read_engagement`. **Guardar el ajuste no cambia el token anterior.** El propietario debe autorizar de nuevo en Meta.

La versión 0.8.31 incorpora una acción para iniciar la renovación directamente desde el dispositivo ya vinculado:

1. SKY Android → Ajustes → Mis redes → Instagram → Conexión segura → **Renovar autorización oficial con Meta**.
2. Confirmar la apertura de Meta. Android solicita `POST /mobile-start` con su credencial móvil de Android Keystore; la función verifica la credencial revocable y genera un estado CSRF de un solo uso y una URL oficial de consentimiento con caducidad de diez minutos.
3. El usuario autoriza los permisos necesarios en el navegador oficial. El callback del servidor recibe el código, verifica el token de Meta y actualiza su copia cifrada. La credencial del teléfono no se cambia.
4. Volver a SKY Android → **Verificar identidad real con Meta**. Confirmar que Meta proporciona el ID y usuario esperados. Si faltan los permisos de página o no hay una cuenta de Instagram profesional vinculada, mostrar el resultado real sin afirmar que la cuenta está verificada.

El dispositivo **nunca** recibe claves maestras ni tokens de Meta. La ruta `/mobile-start` no es pública: requiere el mismo token de dispositivo que `/mobile-profile`. La URL de autorización solo se abre si usa HTTPS y el host oficial esperado. No se habilitan publicaciones ni respuestas automáticas con este cambio. Mantener intacto SKY Windows y BAQUEANO.

La disponibilidad real de 0.8.31 requiere verificar compilación, pruebas, firma y una GitHub Release publicada. No recomendar instalar un artefacto de Actions sin esa evidencia.
