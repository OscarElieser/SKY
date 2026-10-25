# SKY Social Hub + evolución del cerebro

## Principio: una sola SKY, todas las herramientas bajo su control

La API principal sigue siendo `http://127.0.0.1:8765`.
La voz, HUD, seguridad SENTINEL, memoria, SKY Workflows, subagentes y la
integración opcional OpenJarvis **no se reemplazan**. Los proveedores de IA
(Gemini, Claude, OpenAI, Ollama, etc.) conservan sus propias licencias,
credenciales, costes y reglas: SKY los coordina, no fusiona sus modelos o
transfiere sus tokens de manera indiscriminada.

### Aprender y evolucionar de forma comprobable

- SKY registra acciones completadas/fallidas y latencia en `sky_metricas`.
- `sky_evolution` guarda feedback de su propietario y propuestas de mejora.
- `sky_experience_learning` conserva únicamente procedimientos verificados.
- Social Hub permite registrar métricas manuales **etiquetadas como NO
  verificadas** y feedback (1–5); la generación de borradores incorpora
  contexto de ese feedback para adaptar sugerencias y estilo.
- `POST /api/sky/social/strategy` consulta el motor de IA de SKY y genera
  una estrategia original, con pruebas y recomendaciones que no prometen
  seguidores ni viralidad. No publica ni modifica redes por sí sola.
- SKY no reentrena automáticamente los pesos del modelo ni actualiza el
  código en producción: los cambios requieren pruebas y autorización.

## Matriz real de plataformas

| Red | Disponibilidad en este cambio | Condiciones |
|---|---|---|
| X | Publicaciones de texto, respuestas, like/repost individual autorizado | Cuenta X Developer, OAuth de usuario con permisos específicos, límites/coste |
| Facebook | Publicaciones de texto en Páginas administradas | Meta App, token de Página, `pages_manage_posts`; no perfiles personales |
| Threads | Publicación texto y respuesta a un ID autorizado | Meta Threads App, OAuth, `threads_content_publish`; dos fases |
| Instagram | Borradores/estrategia; sin publicar desde este módulo | Cuenta profesional y permisos, contenedores de imagen/video y revisión |
| TikTok | Borradores/estrategia; sin publicar desde este módulo | Content Posting API, aprobación de scopes/auditoría; limita visibilidad de clientes no auditados |
| Snapchat | Borradores/estrategia; sin publicar desde este módulo | Public Profiles / acceso aprobado, cargas de medios y restricciones del producto |

**NO** se simulan APIs de funciones que no están implementadas, ni se
solicitan contraseñas en SKY. Un borrador no equivale a una publicación.
Las APIs que requieran medios, auditorías o acceso restringido deben
tener una implementación propia validada antes de activarse.

Referencias oficiales:
- X: https://docs.x.com/
- Meta Facebook Pages: https://developers.facebook.com/docs/pages-api/
- Meta Instagram: https://developers.facebook.com/docs/instagram-platform/
- Threads API: https://developers.facebook.com/docs/threads/
- TikTok Posting API: https://developers.tiktok.com/docs/en/content-posting-api-get-started
- Snapchat Public Profile: https://developers.snap.com/

## Cuentas y tokens seguros

Crear aplicaciones propias en los portales oficiales; autorizar mediante
OAuth los permisos mínimos. Para este primer adaptador, cargar tokens
**previamente obtenidos mediante OAuth oficial** en el `.env` privado
de SKY, nunca en GitHub ni dentro de las llamadas del HUD:

```dotenv
SKY_SOCIAL_X_ACCESS_TOKEN=
SKY_SOCIAL_X_USER_ID=
SKY_SOCIAL_THREADS_ACCESS_TOKEN=
SKY_SOCIAL_FACEBOOK_PAGE_ID=
SKY_SOCIAL_FACEBOOK_PAGE_TOKEN=
SKY_SOCIAL_WORKER_ENABLED=0
```

La disponibilidad del catálogo se basa en presencia de configuración, NO
garantiza que el token esté vigente, aprobado o tenga cuota. La plataforma
verifica permisos, costes y expiración durante la llamada real. No agregar
claves de servicio con privilegios innecesarios ni compartir contraseñas.

## API SKY protegida

Todas las rutas requieren la autorización de propietario `X-SKY-KEY`
preexistente. Publicar o aprobar exige también SENTINEL/PIN si el dueño
lo configuró.

- `GET /api/sky/social/capabilities`: lo realmente implementado/configurado
- `GET /api/sky/social/queue`: borradores y estado real
- `POST /api/sky/social/drafts`: borrador literal, no se publica
- `POST /api/sky/social/ai-draft`: SKY genera un borrador original con su IA
- `POST /api/sky/social/drafts/{id}/approve`: aprobación expresa y fecha opcional
- `POST /api/sky/social/drafts/{id}/publish`: ejecuta una publicación previamente aprobada
- `POST /api/sky/social/drafts/{id}/cancel`: cancela un borrador o tarea pendiente
- `POST /api/sky/social/x/engagement`: crea acción individual como borrador (like/repost)
- `POST /api/sky/social/drafts/{id}/metrics`: medición manual, marcada no verificada
- `GET /api/sky/social/insights`: reporte de observaciones y limitaciones
- `POST /api/sky/social/drafts/{id}/feedback`: experiencia evaluada por propietario
- `POST /api/sky/social/strategy`: estrategia de IA específica con KPIs disponibles

Ejemplo de solicitud JSON para crear un borrador con IA:

```json
{"platform":"threads","topic":"consejos prácticos para educación técnica",
 "audience":"estudiantes y docentes","style":"cercano y claro","provider":"auto"}
```

O por voz/texto en el chat existente: **«SKY, redacta una publicación para
Threads sobre innovación educativa»**. SKY redacta y almacena el borrador,
pero no lo envía hasta que el propietario lo apruebe.

Para programar: aprobar con `{"approved":true,
"scheduled_at":"2026-10-26T15:00:00-06:00"}`.
Ese horario es un ejemplo, no una cita o tarea creada.

## Servicio de publicaciones aprobadas

Desde `SKY_INICIAR.bat` -> opción 0, si
`SKY_SOCIAL_WORKER_ENABLED=1`, el lanzador inicia `sky_social_worker.py`
y lo supervisa. Lee la cola cada ~60 segundos, enviando COMO MÁXIMO
una publicación previamente aprobada por pasada. Sin aprobación previa no
publica nada. No se ejecutan likes ni reposts por el worker: requieren
selección individual y aprobación humana.

SKY limita las publicaciones confirmadas por red al día y no repite
automáticamente los errores ambiguos. Si la red responde de forma incompleta
se registra `needs_review`; no se marca como publicada ni se reintenta
hasta aclarar si se envió, para evitar duplicados.

**Actividad continua no significa interacción falsa, spam ni garantía de
vistas o seguidores.** El programa no crea seguidores ficticios, no compra
engagement ni simula presencia humana.

## Pruebas

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_sky_social_hub.py
.venv\Scripts\python.exe sky_diagnostico.py
```

GitHub Actions ejecuta pruebas offline con clientes HTTP simulados. Eso
confirma los contratos y seguridad básicos, no que las cuentas estén
conectadas ni que se haya publicado una vez en el entorno real. Antes de
fusionar a `main`, comprobar los permisos de cada cuenta, métricas,
restricciones regionales, vencimiento de tokens y límites reales.

## Recuperación

`SKY_SOCIAL_WORKER_ENABLED=0` y reiniciar SKY desactiva el programador.
Los borradores permanecen en SQLite y los demás módulos de SKY siguen
intactos. Revocar los tokens directamente en el panel oficial detiene
acceso a la plataforma sin desinstalar SKY.
