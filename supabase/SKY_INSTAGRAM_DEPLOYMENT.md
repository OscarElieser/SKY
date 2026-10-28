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
