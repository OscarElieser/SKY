# SKY Skillpack · integración ejecutable en rama de revisión

**Rama:** `feat/skillpack-integraciones-reales-20261023`. Se preservan `main`,
SKY CORE, API FastAPI, HUD, motor de voz, 4 skills originales, MCP Hub,
Office Studio y Sentinel. Sin migraciones de base de datos ni auto-despliegue.

## Resultado implementado en código

De los **29 nombres** aportados en la solicitud actual:

- **22** tienen una vía de ejecución implementada o reutilizada en la API SKY
  (ver adaptadores en `neural_core/sky_skillpack.py`). El código presente
  **NO prueba** conexión a cuentas externas ni instalación local de Docker.
- **2** instrucciones `SKILL.md` de código abierto están copiadas físicamente:
  `seo-audit` y `copywriting-pro`, procedentes de
  [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills),
  con sus licencias MIT. La redacción AI carga la guía de copywriting si existe.
- **7** nombres no tienen aún adaptador ejecutable:
  `aws-workflow-deploy`, `loki-mode`, `supermemory`,
  `google-workspace-connector`, `slack-communicator`, `remotion`,
  `claude-d3js-skill`. No se simula que estén activos.
- El catálogo anterior de **78** skills funcionales de SKY no está
  enumerado íntegramente en la solicitud actual. Este cambio no declara que
  esas 78 integraciones estén instaladas ni que sustituya el catálogo previo.

## Qué operaciones ejecuta hoy el adaptador

| Adaptador | Operación real y límites |
| --- | --- |
| `pdf-pro`, `xlsx-advanced`, `docx-coauthoring`, `pptx-generator` | Reutiliza `/api/office/generate` (archivos reales). No implementa macros, edición avanzada de formularios ni garantiza equivalencia funcional con paquetes terceros. |
| `scientific-researcher` | Busca metadatos reales en OpenAlex por `sky_scholarly`; no inventa texto completo. |
| `github-connector` | Consulta commits públicos mediante el lector GitHub existente; solo lectura. |
| `supabase-mcp` | Reutiliza cliente Supabase actual para lectura de tablas explícitamente autorizadas. **No es el servidor MCP remoto oficial**; aquel requiere OAuth y configuración independiente. |
| `docker-manager` | Consulta `docker ps` local si Docker está instalado. No altera contenedores. |
| `vercel-plugin` | Consulta el estado/listado de despliegues mediante API REST de Vercel. No crea despliegues. |
| `notion-workspace` | Busca páginas autorizadas con token y API oficial. |
| `linear-sync` | Lee issues y datos de usuario de Linear vía GraphQL. |
| `hubspot-crm` | Lee hasta 10 contactos por API REST. |
| `typefully` | Lee borradores del social set configurado mediante API v2. |
| `firecrawl` | Extrae markdown mediante API v2 solamente para dominios permitidos por el propietario. |
| `seo-audit` | Calcula comprobaciones deterministas de title, meta description, h1, alt y canonical a partir del HTML proporcionado. |
| `open-carousel` | Devuelve HTML autónomo de carrusel horizontal con texto escapado. |
| `algorithmic-art` | Devuelve SVG original, determinista y editable. |
| `humanizer`, `copywriting-pro`, `marketing-skills`, `ad-angle-research`, `internal-comms` | Usa el motor IA ya existente; produce texto, **no envía mensajes** ni finge investigar anuncios no suministrados. |

## Interfaces operativas

La API SKY existente añade:

- `GET /api/skillpack/catalogue`
- `POST /api/skillpack/execute/{skill_id}`

Ambas conservan autenticación `X-SKY-KEY` y segundo factor si SKY lo tiene activo.
Cada resultado reporta explícitamente el estado o error; jamás etiqueta credenciales
configuradas como cuenta validada.

Ejemplos de cuerpo JSON para POST:

```json
{"html":"<title>Mi web</title><h1>Destino</h1>"}
```

para `seo-audit`,

```json
{"query":"interactive learning"}
```

para `scientific-researcher`, y

```json
{"text":"Mejora este comunicado conservando todos los hechos","provider":"auto"}
```

para `humanizer`.

También se integró en el asistente de voz y texto mediante órdenes **explícitas**
como «SKY, ejecuta skill scientific-researcher: educación inclusiva» o
«SKY, ejecuta skill humanizer: [texto]». Solo admite ocho rutas de lectura o
redacción sin acciones de terceros por voz. Las demás necesitan la API privada.

## Credenciales locales (NUNCA en GitHub)

Configurar, según necesidad, en el equipo donde se ejecuta SKY:
`VERCEL_TOKEN`, `NOTION_TOKEN`, `LINEAR_API_KEY`,
`HUBSPOT_ACCESS_TOKEN`, `TYPEFULLY_API_KEY`,
`TYPEFULLY_SOCIAL_SET_ID`, `FIRECRAWL_API_KEY` y,
para Supabase, `SUPABASE_URL` más `SUPABASE_ANON_KEY` (o
`BAQUEANO_SUPABASE_PUBLISHABLE_KEY`).

Para Firecrawl definir `SKY_FIRECRAWL_ALLOWED_HOSTS=ejemplo.com`.
Para Supabase definir `SKY_SKILL_SUPABASE_ALLOWED_TABLES=lugares,negocios`,
utilizar credenciales con Row Level Security y **no** exponer service-role keys.

Un token puede requerir plan de pago, OAuth, permisos, aceptación de condiciones
o límites de cuota. No se han verificado cuentas del usuario en este cambio.

## Fuentes y licencias verificadas

- [Marketing Skills (MIT)](https://github.com/coreyhaines31/marketingskills),
  fuente copiada de los dos `SKILL.md` con licencia retenida.
- [Anthropic Skills](https://github.com/anthropics/skills) — referencia, no
  copiar habilidades source-available cuya licencia no autoriza redistribución.
- [Remotion Skills](https://github.com/remotion-dev/skills) — referencia;
  requiere un entorno Node/React.
- [D3.js Skill](https://github.com/chrisvoncsefalvay/claude-d3js-skill) — referencia.
- [Loki Mode](https://github.com/asklokesh/loki-mode) — referencia;
  no se habilita ejecución autónoma de alto riesgo.
- [Supabase MCP](https://supabase.com/docs/guides/ai-tools/mcp) — necesita
  alcance de proyecto y modo read-only.
- [Typefully API](https://typefully.com/docs/api),
  [Linear GraphQL](https://linear.app/developers/graphql),
  [Slack chat API](https://docs.slack.dev/reference/methods/chat.postmessage).

## Pruebas reproducibles

```powershell
python -m pip install "pytest>=8,<10" "httpx>=0.27,<1"
python -m pytest -q tests/test_sky_skillpack.py
```

El workflow `sky-skillpack-tests.yml` evalúa sintaxis, operaciones locales,
fail-closed, escape HTML y control de autorización, sin exigir credenciales.
Las integraciones cloud requieren posteriormente pruebas en una cuenta de
pruebas autorizada, no en producción.

**Importante:** La presencia del código en GitHub no instala servicios,
dependencias externas, cuentas o CLI en la PC/Android del propietario.
No se alteró `main` ni se activaron despliegues productivos.
