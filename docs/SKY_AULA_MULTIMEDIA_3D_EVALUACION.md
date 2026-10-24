# SKY Docente — ampliación multimedia, 3D y evaluación auténtica

**Se amplió la SKY Aula existente**, `neural_core/sky_aula.py`, sus siete momentos pedagógicos, las sesiones temporales, la voz del HUD, la API FastAPI y la seguridad SENTINEL. No se reemplazó el sistema docente ni el núcleo SKY CORE.

## Experiencia del docente

Abrí el HUD principal y seleccioná el módulo **Docencia** (nuevo acceso a la SKY Aula existente). Indicá tema, nivel (inicial, primaria, secundaria, técnico, universitario, maestría o doctorado), objetivo y opcionalmente un texto o plan de estudios.

El panel permite:
- iniciar una clase original con etapas y explicaciones de SKY por voz;
- continuar momentos, escuchar al grupo y emitir retroalimentación formativa;
- solicitar **expresamente** búsqueda de videos educativos y bibliografía;
- abrir la demostración **real tridimensional esquemática** de una computadora;
- presentar un caso práctico ilustrativo relacionado con informática, porcentajes, electricidad, respiración o contabilidad;
- generar instrumentos de evaluación y descargarlos en Word sin almacenar identidades o respuestas de estudiantes.

Para otros temas, SKY conserva el motor de clases y evaluación, pero **solo muestra 3D si hay un modelo adecuado revisado**. No inventa automáticamente anatomía, maquinaria o modelos 3D incorrectos. Podremos añadir bibliotecas de modelos GLB/glTF autorizados por disciplina.

## Búsqueda de videos y red

API autenticada:
`POST /api/sky/academy/education/resources/videos` con `{"topic":"partes de una computadora","level":"tecnico","limit":4}`.

La búsqueda usa **YouTube Data API v3**, mediante `https://www.googleapis.com/youtube/v3/search`, `part=snippet`, `type=video`, `videoEmbeddable=true`, `safeSearch=strict`, `relevanceLanguage=es`; solo devuelve IDs válidos. No raspa YouTube ni descarga videos privados.

Configurar localmente, sin enviar claves a GitHub:

```dotenv
SKY_YOUTUBE_API_KEY=tu_clave_local
```

Sin clave, SKY entrega **enlace de búsqueda** y declara `searched_live=false`, no resultados inventados. `SKY_LOCAL_ONLY=1` bloquea la búsqueda remota. Un video encontrado no implica que SKY haya visto o analizado sus escenas; la selección de contenido requiere revisión del docente y notas/guiones autorizados. El video integrado usa el reproductor de YouTube sin cookies ampliadas y necesita una acción del usuario.

Para que SKY pueda **explicar un video por partes sin inventar su contenido**, agregamos `POST /api/sky/academy/education/resources/video-guide` con ID de video y transcripción o notas que aporta el docente. La API divide el material en fragmentos narrables con preguntas de comprensión, marcando siempre que el texto no fue contrastado automáticamente con el audiovisual. El HUD ofrece un campo de transcripción y la función «Explicar video por partes» usando la voz de SKY. No se descargan ni generan subtítulos de videos de terceros sin autorización.

También se agregó `POST /api/sky/academy/education/resources/research` que reutiliza `sky_scholarly.search_papers` para recuperar metadatos OpenAlex, sin atribuir evidencia del texto completo o revisión por pares.

## Computadora 3D

- Ruta fija `GET /aula/3d/computadora` dentro de la misma aplicación.
- Modelo educativo de ocho partes: gabinete, placa madre, CPU, RAM, SSD, fuente, GPU opcional y refrigeración.
- Modelo generado con geometría 3D real mediante Three.js v0.170.0, carga bajo demanda en el navegador y control OrbitControls. **No es un archivo CAD ni representación exacta de un fabricante.**
- La escena puede girarse, acercarse, explotar virtualmente mediante un control deslizante, seleccionar partes y reconstruirse.
- Cada pieza ofrece función, relación y consejo de seguridad, además de narración opcional TTS del navegador. El HUD continúa utilizando el motor de voz de SKY para sus explicaciones generales.
- El motor Three.js se obtiene en el navegador desde un CDN de versión fijada. Sin Internet o sin WebGL, las explicaciones textuales permanecen accesibles; la escena no se declara operativa en modo totalmente offline hasta incorporar dependencias estáticas locales autorizadas.
- **No abrir una fuente de alimentación ni desarmar un equipo energizado.** Demostración práctica física solo con supervisión adecuada.

La ruta autenticada `GET /api/sky/academy/education/visual/scenes/computer` entrega datos de los componentes y la secuencia didáctica; escenas sin material verificado se rechazan.

## Instrumentos y evaluaciones

Se añadieron al sistema existente:

- **Diagnóstica, formativa y sumativa**.
- Rúbrica analítica con cuatro niveles; lista de cotejo; guía de observación.
- Ticket de salida, estudio de caso, portafolio, autoevaluación, coevaluación, prueba práctica y cuestionario.
- **Tres saberes obligatorios**: conocer (conceptual), hacer (procedimental) y ser/convivir (actitudinal).
- Pesos de ejemplo `30/50/20` (propuesta adaptable, no norma curricular). El docente revisa objetivos y criterios. No se asignan calificaciones automáticas a estudiantes sin evidencia.
- Ruta `POST /api/sky/academy/education/assessments/review`: requiere `teacher_approved=true` y tres evidencias explícitas; devuelve puntuación orientativa, **no nota oficial**.
- Exportación `POST /api/sky/academy/education/assessments/document` en Word/PDF/PPTX/Markdown mediante el generador `sky_office` ya existente.

## Criterios para aceptar la instalación

1. CI de `tests/test_sky_aula_multimedia_assessment.py` y pruebas previas aprobado.
2. En Windows, iniciar SKY y verificar funcionamiento real del panel Docencia.
3. Ejecutar clase de informática por voz, seleccionar partes 3D, despiece/reconstrucción y comprobar el micrófono.
4. Con la API configurada, buscar video realmente embebible, comprobar el título y reproducirlo mediante acción del usuario. No inferir lo que dice el video.
5. Generar rúbrica, lista de cotejo, guía de observación y caso; descargar Word.
6. Validar los tres saberes con instrumentos del programa educativo correspondiente.
7. Repetir prueba en Android: HUD PWA y 3D dependen de WebGL y conexión; navegación y tamaño deberán verificarse.
8. Mantener datos de estudiantes privados: no insertar datos personales en herramientas externas sin permiso y medidas adecuadas.
9. No calificar a nadie únicamente por inferencia textual ni afirmar que se investigó un contenido no leído.

## Fuentes técnicas

- YouTube Data API search.list: https://developers.google.com/youtube/v3/docs/search/list
- YouTube IFrame Player API: https://developers.google.com/youtube/iframe_api_reference
- Three.js GLTFLoader: https://threejs.org/docs/pages/GLTFLoader.html

**Estado:** entrega de código; las pruebas de hardware, API externa y calidad docente son una etapa posterior. SKY conserva su esencia de asistente independiente.
