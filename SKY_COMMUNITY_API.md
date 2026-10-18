# SKY IA · Social Universe API v7.0

**Autor de la visión y promotor del concepto: Oscar Elieser Chamorro Guzmán.**

API real HTTP + WebSocket del **piloto social**. Sirve conexiones concurrentes a través de un servidor FastAPI y guarda mensajes, usuarios, preferencias y publicaciones en SQLite. Por defecto escucha solo en `127.0.0.1:8765`; no es un servicio público desplegado.

## Identidad y seguridad

- SKY maestro usa `X-SKY-KEY: ...` para publicar mundos existentes y crear invitaciones; nunca enviar esta clave a participantes.
- El usuario recibe una invitación de un solo uso, se registra con usuario y contraseña (PBKDF2-HMAC-SHA256 + sal) y abre una sesión opaca que expira a los 7 días.
- Las rutas de usuario aceptan `Authorization: Bearer <token>` y comprueban el usuario en base de datos.
- WebSockets de cada mundo exigen ticket de un uso y 30 segundos de validez; no compartir tokens de sesión en URLs.
- Mundos son privados hasta que el propietario los publique explícitamente.
- Memorias quedan aisladas por usuario; solo se envían al proveedor de IA si el dueño de esa memoria lo autoriza explícitamente.
- Los mensajes del mundo compartido y las publicaciones sociales no son privados frente a sus otros participantes.

## Rutas principales

| Método | Ruta | Autorización y resultado |
| --- | --- | --- |
| `POST` | `/api/community/admin/invites` | Maestro: genera código de invitación de uso único |
| `PUT` | `/api/community/admin/worlds/{id}` | Maestro: publicar/despublicar mundo |
| `GET` | `/api/community/admin/reports` | Maestro: revisar denuncias |
| `POST` | `/api/community/register` | Invitación: crear identidad |
| `POST` | `/api/community/login` | Público: autenticar y obtener sesión temporal |
| `POST` | `/api/community/logout` | Usuario: revocar su sesión |
| `GET/PUT` | `/api/community/me` | Usuario: consultar/editar perfil y avatar |
| `GET` | `/api/community/worlds` | Usuario: listar mundos publicados |
| `GET` | `/api/community/worlds/{id}` | Usuario: obtener escena 3D publicada |
| `GET` | `/api/community/worlds/{id}/messages` | Usuario: recuperar historial del chat del mundo |
| `POST` | `/api/community/ws-ticket?wid={id}` | Usuario: ticket 30 s para entrar a sala |
| `WS` | `/api/community/ws/{id}?ticket={code}` | Presencia, posiciones, mensajes y señalización WebRTC |
| `GET/POST` | `/api/community/me/memory` | Usuario: listar o crear memorias individuales |
| `DELETE` | `/api/community/me/memory/{id}` | Usuario: olvidar un recuerdo propio |
| `POST` | `/api/community/me/feedback` | Usuario: evaluar preferencias |
| `GET` | `/api/community/me/learning` | Usuario: ver resúmenes de evaluaciones |
| `POST` | `/api/community/me/ask` | Usuario: preguntarle a SKY local o a un modelo configurado |
| `GET/POST` | `/api/community/posts` | Usuario: muro social y publicaciones |
| `PUT` | `/api/community/posts/{id}/like` | Usuario: reacción |
| `PUT` | `/api/community/users/{id}/follow` | Usuario: seguir a otro usuario |
| `POST` | `/api/community/reports` | Usuario: reportar contenido |

## Multijugador verdadero

En la conexión `WS`, el servidor envía `welcome` con tu identidad y los avatares existentes. Los demás reciben `join` y `leave` en tiempo real. El cliente envía `move` con `position:[x,y,z]` y mensajes `say` con `text`. Las posiciones se validan y se retransmiten; los mensajes se guardan en el archivo SQLite y se pueden consultar después de reiniciar el servidor. La presencia **no se guarda permanentemente** (es estado de sesión).

## Voz, multimedia e inmersión

Los participantes pueden solicitar una **llamada de voz punto a punto WebRTC** desde el visor: `webrtc-offer`, `webrtc-answer` y `webrtc-ice` se retransmiten solo al otro participante solicitado. El audio viaja de navegador a navegador y no se graba en SKY. Requiere HTTPS o localhost, permiso de micrófono y conectividad ICE. Hay STUN público predeterminado, pero redes con NAT restrictiva exigirán TURN propio; aquí **no se implementa servidor TURN**. Se probó la mensajería de señalización a nivel servidor, no llamada con micrófonos físicos.

El visor principal es **WebGL local**, con cubos, casas, árboles y avatares de geometría básica. No es un motor AAA, fotorealista o MMO, no contiene generación automática de cualquier video/película/avatar humano hiperrealista y no garantiza compatibilidad con visores VR.

## Aprendizaje y memoria

El usuario elige qué recuerdos almacenar, puede consultarlos y borrarlos y registrar evaluaciones. Esto es **memoria personal recuperable y adaptación por preferencias**, no autoentrenamiento de pesos neuronales ni consciencia. SKY puede usar OpenAI, Gemini, Anthropic u Ollama con credenciales configuradas y permiso de envío de memorias; consultas locales de memoria y herramientas no requieren esos proveedores.

## Límites operativos y publicación

- Esta versión se prueba en **un solo proceso Uvicorn** (`--workers 1`). Multiproceso fragmentaría la presencia en memoria.
- SQLite con modo WAL no es suficiente como arquitectura de red social a gran escala. Antes de abrir acceso general migrar usuarios, chat y publicaciones a PostgreSQL, y presencia, chat y eventos a Redis/pubsub.
- Para una versión pública, implementar HTTPS/WSS, límites de peticiones perimetrales, prevención de abuso, roles y moderación, recuperación de contraseña, política de privacidad, copias de seguridad verificadas, métricas, procesos de despliegue y pruebas de carga.
- No poner la clave maestra de SKY en el frontend de los usuarios ni compartir el archivo de tokens.
- La documentación automática en `/docs` incluye los esquemas completos de las rutas.

## Activar y probar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements_social.txt
.venv/bin/python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765 --workers 1
```

Abrí primero `http://127.0.0.1:8765` y obtené la clave en `local_data/sky_api_token.txt` (solo dueño). Abre después `http://127.0.0.1:8765/community`, expandí «Propietario», pegá la clave, creá/publicá mundo y generá dos invitaciones. En dos navegadores/perfiles independientes registrá dos usuarios e ingresá en el mismo mundo. Para que un segundo equipo llegue al servidor se requiere red privada HTTPS o despliegue remoto administrado.

## Reglas de publicación en VPS

Hostinger VPS u otro Linux pueden alojarlo. Se recomienda sistema operativo actualizado, usuario Linux sin privilegios, `systemd`, proxy Caddy/Nginx, DNS (Cloudflare si se utiliza), HTTPS/WSS, bases de datos con respaldo y telemetría. **No abrir directamente el puerto 8765 ni exponer `/` del panel maestro a usuarios públicos sin control adicional de acceso.** Para escalar a decenas/cientos de usuarios se debe rediseñar el broker de mensajes y medir latencia, saturación de CPU/RAM, pérdida de conexiones y consultas SQLite.

**Respaldos consistentes:** `python sky_backup.py` genera copias privadas `.sqlite3` de ambas bases y comprueba su integridad. Para recuperación en producción verificar la restauración en un entorno aislado.
