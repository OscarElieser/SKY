# SKY Global API v10.2 — Idiomas, voz, medios y seguridad

Todas las rutas expuestas son parte del mismo servidor FastAPI, no microservicios ficticios.

## Traducción de interfaz (sin enviar contenido a terceros)

- `GET /api/i18n/languages` — idiomas del catálogo, detección negociada de `Accept-Language` y estado real de etiquetas offline.
- `GET /api/i18n/ui?locale=ar` — glosario público **estático**, orientación `rtl`/`ltr` y recuento de cadenas revisadas. No incluye datos del usuario.
- `GET /api/i18n/phrases?locale=ko` — compatibilidad con v10.1.
- `PUT /api/community/me/language` — guarda preferencia lingüística de la cuenta, requiere bearer de usuario comunitario. Ejemplo `{ "language":"ja-JP" }`.
- `GET /api/community/me/language` — devuelve la preferencia de esa cuenta y si la configuró explícitamente.
- `GET/PUT /api/i18n/preference` — preferencia local del propietario, exige cabecera `X-SKY-KEY` y `X-SKY-SESSION` si MFA está activado.
- `POST /api/i18n/translate` — traducción de texto con Gemini u Ollama **solamente** tras indicar `provider` y `consent:true`. La calidad depende del modelo; no adjunta contexto privado.

## Medios (solo creador)

Todas requieren `X-SKY-KEY` y, si corresponde, `X-SKY-SESSION`:

- `POST /api/global-media/subtitles/vtt` — recibe `{ "srt":"1\n00:00:00,000 --> 00:00:02,000\nHola", "language":"es" }`; devuelve un `.vtt` descargable sin llamadas externas.
- `POST /api/global-media/subtitles/render` — el mismo SRT más `video_asset_id` de la biblioteca privada; genera un `.mp4` subtitulado localmente, sin modificar el original. **No disponible en modo público hasta instalar worker aislado.**
- `POST /api/global-media/narration/mp3` — recibe `{ "text":"Hola", "language":"es", "provider":"gtts", "external_consent":true }`. El texto se manda a gTTS **solo por petición expresa**; no almacena credenciales ni clona voces.

Los archivos multimedia son procesados por FFmpeg con rutas privadas, sin pasar entrada textual del usuario a un shell. Los archivos temporales se limpian después de servir la descarga. El render tiene límites de contenido, tiempo y tamaño.

## MFA del creador

- `GET /api/security/owner-mfa/status` — declara si está configurado TOTP, sin revelar la semilla.
- `POST /api/security/owner-mfa/session` — requiere clave `X-SKY-KEY` y `{ "code":"123456" }`; crea sesión de hasta veinte minutos. Respuesta `{ "session": "...", "expires_in": 1200 }`.
- `GET /api/security/owner-mfa/verify` — requiere clave y `X-SKY-SESSION` cuando MFA está activado.
- `POST /api/security/owner-mfa/logout` — revoca la sesión.

La semilla TOTP debe generarse **fuera de la API** con `python scripts/setup_owner_mfa.py`. La sesión se guarda solo como hash SHA-256 en memoria del servidor; el cliente mantiene el token temporal en memoria de pestaña `sessionStorage`, no la semilla.

**Limitación:** TOTP y sesiones en memoria no sustituyen un proveedor de identidad con FIDO2, recuperación, almacenamiento compartido de sesiones y registros de auditoría. En modo `public` el arranque exige Redis, MFA y proxy TLS externo.
