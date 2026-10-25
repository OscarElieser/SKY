# SKY Creative Evolution · Imagen, video, música y narrativa en nueve idiomas

## Arquitectura sin reemplazos

La única asistente y API principal continúa siendo SKY. Esta ampliación añade
`neural_core/sky_creative_evolution.py` y rutas de su Estudio Creativo en
`/api/creative/evolution/`. Reutiliza `providers.py`, `sky_languages.py`,
el SDK Gemini ya configurado y la biblioteca, editor, historial, render y cola
FFmpeg existentes en `sky_creative.py`.

Ningún módulo preexistente se elimina. Las novedades están sobre una rama de
integración; no equivalen a una instalación en el equipo del propietario.

## Idiomas de creación

| Código | Idioma |
|---|---|
| es | Español |
| en | Inglés |
| fr | Francés |
| pt | Portugués |
| it | Italiano |
| ko | Coreano |
| zh | Chino |
| ja | Japonés |
| de | Alemán |

Todos admiten instrucciones de texto creativo dirigidas al proveedor de IA
configurado. Un idioma seleccionado no garantiza pronunciación, tipografía
instalada, voces, traducción perfecta ni modelo local multilingüe. La interfaz
global de SKY ya incluye esos códigos, y este módulo los usa para sus obras.
Variantes como `es-NI`, `pt-BR` y `zh-CN` se normalizan al idioma principal.

## Escritura y evolución del cerebro

- Cuentos completos breves; historias originales; guiones con escenas.
- Novela: sinopsis, protagonistas, estructura y **primer capítulo**, con
  continuación y revisiones editables en versiones posteriores.
- Película escrita: tratamiento y guion; distinta de un archivo MP4.
- Canciones: letra original; no afirmamos haber cantado el tema.
- Cada solicitud de IA pasa por `neural_core.providers` (Ollama, Gemini,
  OpenAI, Claude, etc. según configuración y elección), conservando los
  permisos y la política `SKY_LOCAL_ONLY`. La generación es contextual,
  no un texto fijo; el resultado depende del modelo real.
- Las obras quedan guardadas en SQLite privado
  `local_data/sky_creative_evolution.sqlite3`, con versión verificable.
  Cada revisión o continuación exige `expected_version`. La continuación
  respeta partes previas; ningún modelo garantiza coherencia perfecta.

## Imagen IA

La ruta de generación mejora opcionalmente el prompt mediante un modelo de
texto elegido por SKY; después invoca el generador Gemini ya existente,
valida imagen PNG/JPEG/WebP y la incorpora a la biblioteca privada.

**No genera imágenes de manera ficticia.** Si el modelo no produce bytes
válidos, el servidor informa el error. El modo local estricto bloquea la
solicitud de Gemini. Generar imágenes en Gemini requiere autorización
`cloud_authorized=true`; pueden existir límites y costes de uso.

## Cine y video

`POST /api/creative/evolution/movies/generate` genera un storyboard JSON
acotado (2–4 planos), solicita una imagen real por plano a Gemini, las guarda,
crea un proyecto de video válido con subtítulos y opcionalmente añade una
pista instrumental. Finalmente envía un trabajo a la cola FFmpeg de SKY.

- El resultado final es un **MP4 de montaje de imágenes** con narrativa,
  no un video fotorrealista de movimiento neuronal.
- La API devuelve el ID del proyecto y del trabajo en cola: **no debe
  anunciar un MP4 descargable** antes de que finalice el render real.
- Consultar `GET /api/creative/jobs/{id}`; descargar desde la biblioteca
  luego de `status=completed`.
- Se requieren FFmpeg/FFprobe y GPU/recursos según los modelos utilizados.
- 2–4 imágenes de Gemini pueden consumir cuota; el usuario debe confirmar
  cada generación. Si falla un plano, el montaje no se pone en cola.
- Para películas más largas, SKY mantiene su editor multipista y proyectos
  de video por clips; el generador simplificado no hace largometrajes completos.

## Música

SKY compone WAV instrumental reproducible mediante síntesis armónica
original y una progresión/motivo dependientes del género, la emoción,
la duración y la semilla. Duración por clip: **8–30 segundos**; BPM 60–160.
Se valida mediante `ffprobe` al añadir a la biblioteca existente.
La pista sirve como música original de los montajes.

Esta función **no es todavía un modelo generativo neuronal de música**:
no genera voz cantada, instrumentos virtuales profesionales ni una canción
completa de horas. Las letras se generan aparte en el tipo `cancion`.
No imitar artistas o grabaciones existentes sin autorización.

## Rutas autenticadas de SKY

| Método | Ruta |
|---|---|
| GET | `/api/creative/evolution/capabilities` |
| GET | `/api/creative/evolution/languages` |
| POST | `/api/creative/evolution/writing` |
| GET | `/api/creative/evolution/writing` |
| GET | `/api/creative/evolution/writing/{id}` |
| GET | `/api/creative/evolution/writing/{id}/versions` |
| POST | `/api/creative/evolution/writing/{id}/revise` |
| POST | `/api/creative/evolution/writing/{id}/continue` |
| POST | `/api/creative/evolution/images/improve-prompt` |
| POST | `/api/creative/evolution/images/generate` |
| POST | `/api/creative/evolution/music/generate` |
| POST | `/api/creative/evolution/movies/generate` |

Todas las rutas heredan `require_key` y la protección global de SKY.
Los controles nuevos están en el mismo `/creative`, usando la sesión
autorizada del estudio que ya existía. No existe una segunda app SKY.

Ejemplo para libro en francés:

```json
{"kind":"novela","title":"Le secret de la vallée",
"premise":"Une communauté découvre une histoire ancienne dans sa vallée.",
"genre":"misterio","locale":"fr","provider":"auto"}
```

Ejemplo de música instrumental (no hay uso externo de IA):

```json
{"genre":"cinematic","mood":"hopeful","seconds":12,"bpm":96,
"seed_text":"amanecer en las montañas"}
```

## Solicitudes naturales a SKY

Los comandos específicos de narración y música instrumental se reconocen
en la API personal existente tanto en `/api/asistente/mensaje` como en
`/api/asistente/stream`. Ejemplos:

- «SKY, redacta una novela en francés sobre una ciudad con recuerdos».
- «SKY, escribe un cuento en japonés sobre viajeros y nuevas amistades».
- «SKY, crea una canción en coreano sobre la esperanza y el futuro»:
  produce **letra**, no voz cantada.
- «SKY, crea música instrumental inspirada en el paisaje nicaragüense»:
  compone y guarda WAV en la biblioteca.

Para crear fotogramas con Gemini o un montaje cinematográfico, el usuario
debe iniciar la generación desde el Estudio Creativo y autorizar el envío
a la API externa. No se autoriza consumo automático de nube por un comando
ambiguo. Las capacidades del estudio también aparecen en
`GET /api/sky/intelligence/overview`.

## Validación y siguientes requisitos reales

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_sky_creative_evolution.py
.venv\Scripts\python.exe sky_diagnostico.py
```

Las pruebas de GitHub usan simulaciones para las llamadas pagadas de IA;
la música WAV se analiza como bytes y fotogramas del storyboard se
validan como datos estructurados. **Faltan pruebas en Windows del modelo
Gemini, FFmpeg, biblioteca y fuentes para chino, japonés y coreano** antes de
decir que todas las producciones funcionan en el dispositivo.
