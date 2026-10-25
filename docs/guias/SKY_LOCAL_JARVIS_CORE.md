# SKY: núcleo cinematográfico, historial persistente y motores locales

## Una sola SKY; conservar lo existente

Esta propuesta extiende las ramas anteriores; ni las funciones actuales ni
la API original (`127.0.0.1:8765`) son reemplazadas. Todo está protegido
por SKY SENTINEL y la llave de propietario ya existente. **No se incorporan
modelos ni software en el equipo automáticamente al clonar el repositorio.**

## Pantalla principal, estilo Jarvis de Iron Man

`/hud` inicia en modo `sky-cinematic`: **únicamente el núcleo central
animado y su estado**. La cabecera, los botones y los paneles anteriores
permanecen en el DOM para compatibilidad, pero están ocultos. No se
muestran botones de diagnóstico, programación, agenda o sistemas.

El núcleo sigue aceptando clic para activar voz. Los controles avanzados
se abren en una **ventana pequeña, premium, flotante y arrastrable** mediante
órdenes por voz o texto; sus botones pertenecen a la ventana, no al núcleo.

Comandos:
- «SKY, abrí cuadro de texto» / «SKY, abrí el chat».
- «SKY, abrí historial» / «SKY, abrí historial de conversaciones».
- «SKY, abrí el Estudio Creativo en una ventana pequeña».
- «SKY, abrí diagnóstico» o «SKY, abrí programación».

Las ventanas admiten minimizar, ampliar, arrastrar y cerrar. Los módulos
de la interfaz antigua continúan en el código, pero no ocupan el inicio.
Los programas nativos como Word/Excel/Chrome siguen dependiendo del agente
Windows ya existente, que debe verificar que realmente se abrieron y que
la acción está autorizada; **un iframe no controla por sí mismo Windows**.

## Historial completo y recuperable

Las nuevas consultas/replies del HUD quedan en un archivo SQLite privado
(`local_data/sky_hud_history.sqlite3`), separado de la biblioteca de IA.
No se elimina automáticamente por número de mensajes y admite paginación,
búsqueda y recuperación del contexto al reiniciar navegador. Todas las
operaciones requieren la misma llave/seguridad del HUD.

- `POST /api/hud/historial` guarda un turno autorizado.
- `GET /api/hud/historial?limit=60&before=123` pagina, sin omitir filas.
- `GET /api/hud/historial?q=proyecto` busca una expresión.
- `GET /api/hud/historial/count` devuelve cantidad total.

**Límites:** esta primera versión guarda **nuevas consultas del HUD** y
no importa retroactivamente sesiones del navegador previas ni consultas
realizadas fuera de este HUD. Almacenamiento local no equivale a cifrado
de contenido en reposo; proteger el disco de Windows y sus copias.
Si una conexión falla, se marca como pendiente, sin anunciar guardado.

## Imagen y video propios sin Gemini

SKY ahora puede comunicarse con un servidor **ComfyUI ejecutándose en tu
propia computadora**, para utilizar modelos locales autorizados (según
licencia) de imagen o video, incluyendo SDXL/Flux o flujos de video
compatibles que el propietario instale. Las arquitecturas/modelos no
vienen preinstalados ni se descargan al arranque. Son necesarios GPU,
memoria, controladores y modelos adecuados a los flujos específicos.

API oficial ComfyUI: https://github.com/Comfy-Org/docs/blob/main/development/comfyui-server/comms_routes.mdx

1. Instalar ComfyUI por su procedimiento oficial en una carpeta separada
   de SKY y dejarlo escuchando únicamente en `127.0.0.1:8188`.
2. Descargar legalmente un modelo compatible para imágenes y, si se quiere
   movimiento, un modelo específico de video con sus nodos compatibles.
3. Exportar un **workflow en formato API JSON** desde ComfyUI y verificar
   su contenido. No ejecutar flujos descargados de procedencia desconocida.
4. Identificar el ID del nodo positivo `CLIPTextEncode` en el JSON; SKY
   reemplazará únicamente `inputs.text` en ese nodo.
5. Configurar el `.env` privado (nunca subir modelos, tokens o workflows
   con datos personales al repositorio):

```dotenv
SKY_COMFYUI_ENABLED=1
SKY_COMFYUI_PORT=8188
SKY_COMFYUI_WORKFLOW_IMAGE=C:/SKY-Workflows/imagen_api.json
SKY_COMFYUI_PROMPT_NODE_IMAGE=6
SKY_COMFYUI_WORKFLOW_VIDEO=C:/SKY-Workflows/video_api.json
SKY_COMFYUI_PROMPT_NODE_VIDEO=6
```

En `/creative` elegir «SKY local · ComfyUI» y solicitar imagen o
video. SKY envia el prompt a ComfyUI, recibe un trabajo en cola, y
**solo confirma la creación tras leer, validar e importar bytes
auténticos** en su biblioteca con `sky_creative.ingest`.
Rutas protegidas:

- `GET /api/creative/local/capabilities`: configuración, sin afirmar vivo.
- `GET /api/creative/local/check`: conexión a ComfyUI real.
- `POST /api/creative/local/submit`: pide imagen o video.
- `GET /api/creative/local/jobs/{id}`: estado o recurso importado.

SKY no usa una URL externa suministrada por el usuario, no hace
redirecciones HTTP, no lanza comandos en Windows y no modifica el
workflow original. El video de difusión local está condicionado a un
workflow que produzca un archivo `.mp4` o `.webm` en la salida
`gifs`/`videos`; no todos los flujos de ComfyUI usan ese formato.
Si la salida no es compatible, el trabajo permanece sin importarse.

La ruta Gemini anterior **permanece disponible como opción explícita**
para comparación o equipos sin modelos locales.

## Motor alternativo Diffusers ejecutado directamente por SKY

Para que SKY pueda crear imágenes **sin Gemini y sin ComfyUI**, también se
añadió `sky_diffusers_local.py`. Llama directamente desde Python a los
pesos de un modelo Diffusers existente y devuelve un PNG válido a
`sky_creative.ingest`.

Documentación base: https://huggingface.co/docs/diffusers/main/index

Instalación opt-in, después de analizar capacidad GPU, licencia del
modelo y compatibilidad PyTorch/CUDA:

```powershell
# Ejemplo ilustrativo, no ejecutado en tu PC:
.venv\Scripts\python.exe -m pip install diffusers transformers accelerate safetensors
```

```dotenv
SKY_DIFFUSERS_ENABLED=1
SKY_DIFFUSERS_IMAGE_MODEL_DIR=C:/SKY-Models/imagen-local
```

El directorio contiene `model_index.json` y los pesos/pipelines
compatibles instalados previamente. SKY usa
`DiffusionPipeline.from_pretrained(..., local_files_only=True,
use_safetensors=True)` y no descarga nada. Seleccionar en el estudio
**«SKY local · Modelo Diffusers directo (imágenes)»**.

El motor local admite imágenes de **512×512** o **768×768** en este
contrato y 10–35 pasos. Algunos modelos requieren formatos de entrada,
resoluciones o GPU distintas; un error significa que se necesita ajustar
el modelo y sus requisitos. La ejecución puede ser lenta en CPU.
**No se han entrenado pesos fundacionales nuevos**: la creación propia
consiste en la orquestación, el render, los flujos y el resultado generado
sobre modelos open-weight instalados y licenciados por el propietario.

Para **video generativo local**, la ruta implementada es ComfyUI con
un workflow y un modelo realmente especializados en video.

## LM Studio y LLM locales

LM Studio puede servir modelos mediante su API OpenAI-compatible
`/v1/chat/completions` en puerto 1234: https://lmstudio.ai/docs/developer/openai-compat

```dotenv
SKY_LMSTUDIO_ENABLED=1
SKY_LMSTUDIO_PORT=1234
SKY_LMSTUDIO_MODEL=NOMBRE_EXACTO_DEL_MODELO_CARGADO
```

Se añade `lmstudio` al registro de `neural_core.providers`.
SKY conserva Ollama, OpenJarvis, Gemini, Claude, OpenAI y los otros
proveedores. En `SKY_LOCAL_ONLY=1` puede usar expresamente LM Studio,
o seleccionarlo en automático si está configurado; nunca enviará
prompts a un servidor LM Studio externo. El catálogo configurado
**no comprueba automáticamente** si el modelo está cargado: la lectura
de `sky_lmstudio.status()` sí consulta `GET /v1/models`.

## Auditoría de las demás librerías y plataformas

| Componente | Estado confirmado en repositorio |
|---|---|
| LLM locales y Ollama | Adaptador existente; el modelo real depende de PC |
| LM Studio | Nuevo adaptador; instalación/modelo del PC aún sin comprobar |
| ComfyUI | Nuevo adaptador para imagen/video local; workflow/modelo pendiente |
| Hugging Face Diffusers | No hay nueva inferencia directa ni pesos instalados por este PR |
| CrewAI | No se encontró adaptador nativo; integración no completada |
| Microsoft AutoGen | No se encontró adaptador nativo; integración no completada |
| LangChain | No se encontró adaptador directo; SKY ya tiene su propia orquestación |
| keyboard | No es dependencia esencial declarada; el estado real se detecta en runtime |
| pyautogui | No se ha activado como controlador; funciones Windows nativas ya existen |
| subprocess | Biblioteca estándar de Python; usada en el controlador Windows y render |
| requests | Solo se detecta paquete al iniciar SKY; no confundir con httpx/urllib |
| n8n | Bridge existente, exige allowlist y aprobación |
| Make.com | No hay adaptador validado ni autorización configurada |
| Home Assistant | Bridge REST existente con permisos específicos y confirmaciones |
| No-code/low-code | n8n disponible; Make pendiente; no equivale a dominio universal |

El inventario real del proceso estará disponible en
`GET /api/sky/intelligence/integrations-audit`. El informe lee si los
módulos de Python están instalados **en el equipo donde corre SKY**;
no puede saber si un programa está en otro PC sin agente instalado.
No se habilitan CrewAI/AutoGen/LangChain solo por descubrir un paquete:
seguirán subordinados a permisos y al supervisor SKY, nunca reemplazarán
su cerebro.

## Validación / límites pendientes

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_sky_local_media_hud_history.py
.venv\Scripts\python.exe sky_diagnostico.py
```

Las pruebas CI usan respuestas simuladas para ComfyUI y LM Studio;
la infraestructura de SKY necesita validación Windows y una
generación **real** con los modelos propios, además de pruebas de
compatibilidad con el agente, permisos de audio y GPU.
No afirmar «todo operativo» basándose solamente en importaciones Python.
