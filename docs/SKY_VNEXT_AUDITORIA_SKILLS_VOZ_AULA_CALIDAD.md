# SKY IA · Integraciones ejecutables, voz, docencia, investigación y calidad

**Implementación en la rama:** `feat/sky-integraciones-voz-aula-calidad-20261023`.
Se basa en `feat/sky-operational-cycle-mobile-20261023` (PR #25), que a su
vez incorpora el Skillpack (PR #24). **No modificar directamente `main`.**

**Autor del proyecto:** Oscar Elieser Chamorro Guzmán. **Asistencia
técnica en la elaboración y revisión:** ChatGPT, desarrollado por OpenAI.
SKY es un proyecto independiente, no un producto de OpenAI.

## Lo que está realmente agregado

- `neural_core/sky_skillpack_extended.py`: adaptadores de siete habilidades
  nuevas que faltaban del catálogo de 29. El total de 29 ahora tiene
  ruta de código, NO 29 servicios conectados y probados.
- AWS CloudFormation: consulta identidad, valida plantillas allowlist y puede
  desplegar un stack autorizado solo con `approved:true`, MFA del propietario,
  `SKY_SKILL_ALLOW_AWS_DEPLOY=1` y `SKY_AWS_ALLOWED_STACKS`. AWS puede cobrar.
- Loki Mode: dos workers acotados y un máximo de 24 trabajos; únicamente
  `seo-audit` y `algorithmic-art` en segundo plano. **No es el framework Loki
  Mode completo de terceros ni permite agentes autónomos sin revisión.**
- Supermemory: CRUD privado a través del SmartMemory existente; solo con
  aprobación para escribir/eliminar; secretos rechazados.
- Google Workspace: lectura real de 10 archivos Drive, mensajes Gmail o eventos
  Calendar mediante OAuth token del propietario. Todavía no implementa un flujo
  OAuth interactivo ni actualización automática del token; no envía correo.
- Slack: `auth.test`, historial de canales permitidos, y `chat.postMessage`
  solo con `approved:true` más PIN SENTINEL para envío. Configuración mínima:
  `SKY_SLACK_BOT_TOKEN`, `SKY_SLACK_ALLOWED_CHANNELS`.
- Remotion: proyecto React/Remotion compilable; render real `SkyIntro` cuando
  se instalan dependencias en `sky_remotion`, se aprueba y existe Chromium
  compatible. No afirma haber renderizado un video en el equipo del propietario.
- D3.js: renderizador `sky_d3/render.mjs` usando `d3` real (npm), capaz de
  producir SVG desde listas de valores válidas. Se valida en CI mediante npm.
- Nuevas operaciones protegidas de auditoría y calidad:
  `GET /api/sky/skills/audit`,
  `GET /api/sky/skills/live-results`,
  `POST /api/sky/skills/probe/{skill_id}` y
  `GET /api/sky/quality/operational`.
  No se exponen claves ni datos privados.
- `metaverse/academy_api.py`: `POST /api/sky/academy/research/live-papers`
  (OpenAlex/Crossref, metadatos con DOI, año y fuente; no asegura revisión por
  pares) y `POST /api/sky/academy/education/formative-rubric` (sin calificación
  numérica). Se conservan las sesiones de SKY Aula y la exportación Office.
- `metaverse/static/hud.js`: aceptación de intervenciones sin repetir «SKY»
  con conversación natural activada y órdenes explícitas para interrumpir la
  voz del navegador. El micrófono manual, VAD, TTS y la historia común se
  conservan; no declara que se haya comprobado barge-in físico en Android.
- Los indicadores de calidad muestran verificadas, fallidas, enviadas sin
  evidencia, latencia, audio y coste cuando existe una observación registrada.
  **Nunca se inventa un 100/100.**

## Catálogo de 78: auditoría y hechos

El número `78` aparece como objetivo histórico por grupos, pero **no hay
un manifiesto de 78 nombres individuales con repositorios y evidencias**.
`sky_skills_audit.audit()` reporta, por separado, los grupos realmente
presentes: 29 adaptadores externos, guías profesionales, habilidades nativas,
skills de pasos y habilidades del builder. No se suman como 78 skills únicas
porque pueden representar conceptos de naturaleza distinta o solaparse.
Los archivos `SKILL.md` se enumeran como recursos, NO como herramientas
ejecutadas. El campo `manifest_of_78_distinct_ids_present` es falso hasta
que haya datos reales.

## Pruebas con servicios reales

Los unit tests simulan de forma explícita HTTP y políticas (no las presentan
como cuenta conectada). Hay probes voluntarios:
`POST /api/sky/skills/probe/{skill_id}` para proveedores de lectura permitidos,
almacenados en `~/.neuralt/sky_skill_live_checks.json`. Las pruebas **no
se ejecutan en arranque** ni publican, despliegan ni borran. Solo devuelven
`verified` ante respuesta real en ese dispositivo; errores se registran como
`failed`. Historial consultable en `GET /api/sky/skills/live-results`.

Para pruebas que requieren recursos elegidos por el propietario (por ejemplo
scraping Firecrawl o Supabase tables), invocar la skill directamente con
los parámetros permitidos. No usar probes automáticos que consuman cuotas,
accedan a información privada no autorizada o generen cargos.

### Dependencias voluntarias en el equipo

```powershell
npm install --prefix sky_d3
npm install --prefix sky_remotion
python -m pytest -q tests/test_sky_skillpack.py tests/test_sky_final_integration.py tests/test_sky_execution_cycle.py
```

Configurar credenciales en el entorno privado del dispositivo. Nunca
subir tokens, llaves, accesos OAuth ni `.env` a GitHub.
Para Google, generar OAuth con ámbitos de lectura y gestionar caducidad;
`SKY_GOOGLE_OAUTH_ACCESS_TOKEN` no es una solución duradera sin refresco.

Documentación API utilizada:
- AWS: https://docs.aws.amazon.com/cli/latest/reference/cloudformation/validate-template.html
- Slack: https://docs.slack.dev/reference/methods/conversations.history/
- Remotion: https://www.remotion.dev/docs/render
- D3.js: https://d3js.org/
- Google: https://developers.google.com/workspace

## Criterio de aceptación antes de producción

1. CI tests Python, JS y D3 deben pasar en la misma commit SHA.
2. Se prueban Windows y Android en sesiones reales con micrófono, TTS,
   interrupción y conversación de seguimiento.
3. Se prueba el agente en Word, Excel, archivos y multimedia con permisos
   explícitos y registro `VERIFIED`; nunca sumar `DISPATCHED` como éxito.
4. Validar conexión HTTPS privada entre teléfono y PC y revocación de
   dispositivos. La PWA Android no es todavía una APK nativa.
5. Ejecutar probes de proveedores con las credenciales correspondientes y
   documentar HTTP, permisos, latencia, cuotas y coste observado.
6. Cada skill del supuesto grupo 78 debe tener identificador único, fuente,
   licencia, permisos, función real y prueba. Hasta entonces no certificar 78/78.
7. `/api/sky/quality/operational` informa muestra y cobertura, no promete
   funcionamiento universal perfecto.

**No fusionar a producción sin validar las condiciones anteriores.**


## Prueba física futura en Windows (solo al ejecutar manualmente)

El script `scripts/sky_e2e_pc_real.py` no se ejecuta en GitHub Actions
ni automáticamente al iniciar SKY. En una PC Windows, con el agente SKY ya
corriendo en localhost y sus permisos configurados, permite comprobar el
ciclo real con una aplicación y un documento nuevo:

```powershell
python scripts/sky_e2e_pc_real.py --help
python scripts/sky_e2e_pc_real.py --confirm --app calculator
python scripts/sky_e2e_pc_real.py --confirm --app word --open-document
```

Si Word no está instalado o no tiene permiso, la prueba falla sin fingir
que abrió. Cada ejecución conserva un reporte sin tokens en
`Documentos/SKY_E2E` (incluye posible redirección OneDrive). El comando
`--media-test` modifica el estado Play/Pausa y solo debe usarse
cuando el propietario lo solicite expresamente. Estas comprobaciones NO
prueban por sí solas el micrófono o la reproducción acústica del equipo.
