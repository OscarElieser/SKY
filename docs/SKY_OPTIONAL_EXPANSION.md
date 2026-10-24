# SKY IA — Expansión opcional y segura de investigación, modelos y n8n

## Principio de integración

Esta fase **no sustituye SKY CORE**, los agentes de Windows/Android,
la API FastAPI, SKY Aula, los 29 adaptadores, la memoria o el HUD holográfico.
Se desarrolla primero en una rama para poder revertirla sin afectar `main`.

Se descartó instalar indiscriminadamente los 12 repositorios y decenas de
aplicaciones de las imágenes: Open WebUI, Dify y Langflow son plataformas
alternativas con servicios persistentes. Instalarlas sin necesidad duplicaría
partes de SKY y aumentaría consumo y superficie de ataque.

### Reutilizado sin duplicar

- Ollama local: `neural_core/providers.py` y `sky_cerebro`.
- OpenAlex y Crossref: `neural_core/sky_scholarly.py`.
- Firecrawl: adaptador preexistente `sky_skillpack.py`.
- GitHub, Supabase, Office, voz y aprendizaje: permanecen en sus módulos.

### Nuevas integraciones reales por API, opt-in

| Función | Conector | Configuración | Alcance |
| --- | --- | --- | --- |
| Investigación | Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` opcional | Artículos, año, DOI, autores, resumen |
| Referencias | Zotero v3 | `SKY_ZOTERO_USER_ID`, `SKY_ZOTERO_API_KEY` | Consultar biblioteca privada propia |
| Cálculos | Wolfram Alpha Short Answers | `SKY_WOLFRAM_APP_ID` | Respuesta computacional breve |
| Modelos | OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Chat solo al seleccionar el proveedor |
| Modelos | Hugging Face Inference | `HF_TOKEN`, `HF_MODEL` | Chat solo al seleccionar el proveedor |
| Automatización | n8n | `SKY_N8N_URL`, `SKY_N8N_API_KEY` | Consultar workflows y ejecuciones |

Todos necesitan Internet salvo un n8n expresamente autohospedado en
`http://127.0.0.1:5678`. La infraestructura local de Ollama permanece
seleccionable. Una cuenta en la web no equivale a tener API habilitada.

**Las credenciales se configuran localmente, no se agregan a GitHub**.
El registro del catálogo refleja configuración, NO resultados live verified.
No se automatizan pagos, escritura en Zotero ni publicaciones de investigación.

## Cómo utilizar desde voz y texto

Se admiten peticiones explícitas como:

- «SKY, investiga en Semantic Scholar sobre aprendizaje interactivo».
- «SKY, busca mis referencias en Zotero sobre educación técnica».
- «SKY, consulta Wolfram 2+2».

Se consulta directamente la API del proveedor elegido, se indican
limitaciones de las fuentes y se devuelve la respuesta al motor conversacional
preexistente. No se realiza investigación externa silenciosa ante otras frases.
Los resultados de Semantic Scholar se consideran **metadatos/resúmenes**, no
texto integral leído ni evidencia que certifique las conclusiones.

Los dos proveedores de modelos nuevos se eligen **explícitamente** como
`openrouter` o `huggingface` a través de la pasarela SKY; no se añaden
a `AUTO_ORDER`. `SKY_LOCAL_ONLY=1` bloquea ambos. El nombre del modelo
se obtiene de la variable del propietario; no se inventan modelos ni precios.

`SKY_LOCAL_ONLY=1` también bloquea las nuevas consultas externas a Semantic
Scholar, Zotero y Wolfram, así como n8n remoto. Solo permanece permitido el
n8n localhost activado expresamente por el propietario.

## n8n — sin control paralelo de SKY

Por defecto, solo lectura:

```dotenv
SKY_N8N_URL=https://tu-n8n.example.org
SKY_N8N_ALLOWED_HOSTS=tu-n8n.example.org
SKY_N8N_API_KEY=<clave almacenada localmente, no aquí>
```

También permite, de forma separada y explícita, n8n local en
`http://127.0.0.1:5678` únicamente si
`SKY_N8N_ALLOW_LOCAL=1`. Nunca usar `0.0.0.0` o publicar
el agente de Windows a Internet.

Para **disparar un webhook ya creado y expresamente autorizado**:

```dotenv
SKY_N8N_ALLOW_DISPATCH=1
SKY_N8N_ALLOWED_WEBHOOKS=teacher_reminder
SKY_N8N_WEBHOOK_SECRET=<secreto seguro de 24+ caracteres>
```

El workflow n8n debe verificar el header `X-SKY-WEBHOOK-SECRET`
antes de continuar. SKY exige autorización explícita en el request y
**PIN SENTINEL** en el endpoint protegido. Una respuesta HTTP correcta
significa `DISPATCHED_UNVERIFIED`, nunca tarea finalizada.
No se aceptan URLs proporcionadas por el usuario ni se ejecutan
workflows por texto libre. Usar únicamente flujos creados y probados
por el propietario.

## Rutas añadidas a la API SKY existente

Todas están protegidas por `X-SKY-KEY` y MFA ya existente:

- `GET /api/sky/expansion/readiness`
- `POST /api/sky/expansion/research/semantic-scholar`
- `POST /api/sky/expansion/research/zotero`
- `POST /api/sky/expansion/research/wolfram`
- `GET /api/sky/expansion/n8n/workflows`
- `GET /api/sky/expansion/n8n/executions`
- `POST /api/sky/expansion/n8n/dispatch` (aprobación + PIN)

## Aceptación antes de fusionar

1. Ejecutar CI de Python, análisis de seguridad y regresiones preexistentes.
2. Confirmar que las integraciones existentes sigan intactas.
3. Probar fuentes públicas en el equipo, sin credenciales privadas.
4. Probar Zotero, Wolfram y modelos con claves reales del propietario,
   medir latencia y cuota; ninguna prueba CI simula autenticación real.
5. Configurar y probar n8n en una instancia local/privada, aprobar
   el webhook de pruebas y comprobar el resultado desde n8n.
6. Finalmente validar Windows/Android, micrófono, TTS, interrupciones
   y secuencias usando los módulos anteriores.

### Comprobación local sin conectores pagos

```powershell
python -m pytest -q tests/test_sky_optional_expansion.py
```

## Referencias para la implementación

- Semantic Scholar API: https://api.semanticscholar.org/api-docs/
- Zotero Web API v3: https://www.zotero.org/support/dev/web_api/v3/basics
- Wolfram Alpha Short Answers: https://products.wolframalpha.com/short-answers-api/documentation
- OpenRouter: https://openrouter.ai/docs/api_reference/overview
- Hugging Face Inference: https://huggingface.co/docs/inference-providers/en/tasks/chat-completion
- n8n API: https://docs.n8n.io/api/

**No es una certificación de funcionamiento universal ni una nueva versión
instalada en tu PC o teléfono.** Es una integración incremental verificable,
conservando la versión estable mientras se revisa.
