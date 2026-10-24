# SKY — Comprensión de documentos, imágenes, videos y aprendizaje seguro

## Estado real de las herramientas

Esta actualización extiende la **API original** de SKY. No crea asistentes externos obligatorios.

| Tipo | SKY puede efectuar en esta rama | Todavía no garantiza |
|---|---|---|
| TXT/MD/código/CSV/JSON | Extraer texto, mostrar fragmentos, detectar contenido | Determinar que sea verdadero |
| PDF | Extraer texto digital y número de páginas | OCR automático de escaneos |
| DOCX | Extraer párrafos y tablas | Comprender toda la diagramación y los elementos gráficos |
| XLSX | Leer hojas y primeras filas, sin calcular fórmulas | Auditar todas las fórmulas/macros |
| PPTX | Leer textos por diapositiva | Reconocer automáticamente cada figura o animación |
| PNG/JPG/WEBP | Tamaño/formato y, si está configurado, análisis con modelo visual local Ollama | Exactitud perfecta del modelo visual |
| MP4/MOV/MKV/WEBM | Inspeccionar que existan pistas y duración | Comprender todas las escenas, narración o transcripción |
| MP3/WAV/M4A/FLAC/OGG | Validar pista y duración | Transcripción completa sin configurar STT |

Módulos:
- `neural_core/sky_multimodal_reader.py`: lector privado, acotado y sin memoria automática.
- `metaverse/multimodal_api.py`: API autenticada para análisis a demanda.
- `neural_core/sky_creative.py`: edición y exportación de medios existentes.
- `neural_core/sky_office.py`: generación local de documentos, diapositivas y PDF.
- `neural_core/sky_neural_memory.py`: solo hechos confirmados por propietario y estadísticas verificables de ejecución.
- `neural_core/sky_media_tools.py`: búsqueda sin resultados inventados ante fallos.

## Endpoints

- `GET /api/sky/reader/capabilities` — inventario **de capacidades, no de modelos instalados**.
- `POST /api/sky/reader/analyze` — multipart `file` (documentos hasta 15 MB, multimedia hasta 80 MB).
- `POST /api/sky/reader/vision` — multipart `file` y campo `question`. Requiere `SKY_VISION_MODEL` con Ollama **local** en `SKY_VISION_LOCAL_URL=http://127.0.0.1:11434`.
- `POST /api/chat/upload` — conserva contrato básico de carga para el HUD, pero **NO guarda el texto como aprendizaje verificado**.
- `GET /api/media/uploads/{filename}?expires=...&sig=...` — previsualización de multimedia mediante enlace HMAC temporal de 10 minutos. No se divulga la clave API en URL.

Todas las rutas de análisis necesitan `X-SKY-KEY` y `X-SKY-SESSION` si está activado MFA.

## Cómo debería aprender SKY de internet

1. Solo investigar cuando el usuario lo solicite o exista una fuente/tema previamente autorizado para seguimiento.
2. Usar búsqueda real, comprobar URL pública y aplicar filtros anti-SSRF, robots/condiciones del sitio y límites de frecuencia antes de abrir páginas.
3. Guardar por cada afirmación la URL, fecha de consulta, cita, grado de certeza y contexto.
4. Tratar el contenido web como **datos no confiables**, nunca como instrucciones para ejecutar software.
5. Extraer afirmaciones contrastables, consultar distintas fuentes y avisar de inconsistencias.
6. Mostrar un borrador de aprendizaje al propietario; integrar como hecho persistente solo tras autorización.
7. Guardar memoria separada por propietario, proyecto y finalidad; permitir revisar, corregir, exportar y borrar.
8. Medir precisión, tiempos, entregables y errores; la evidencia no cambia por sí sola permisos ni pesos del modelo.

La búsqueda web que ya tenía SKY depende en ocasiones de conectividad/servicios de terceros y usa un scraper alternativo. El cambio actual evita resultados inventados; **no equivale a un motor propio de investigación web verificada**. Es un objetivo posterior.

## Producción profesional

Pipeline recomendado al pedir «SKY, preparame un informe/presentación/video»:

1. SKY CORE analiza la petición, el alcance y el material adjunto.
2. SKY Supervisor selecciona roles internos, herramientas y modelo local cuando corresponda.
3. Lector multimodal convierte fuentes en texto/estructura o pistas; no inventa contenido visual cuando falta modelo.
4. Investigador con fuentes contrastadas, cuando la Skill exista y esté autorizada.
5. SKY Office Studio o Creative Studio prepara un archivo editable/exportable.
6. Validador de calidad comprueba la integridad del archivo, el contenido, formato y licencias.
7. SKY presenta una vista previa; registra resultado `VERIFIED` solamente cuando existen pruebas de salida real.

### Motores opcionales

- Para imágenes: Ollama con modelo visual compatible (análisis) y motor local especializado de generación bajo licencia compatible (creación); **analizar una foto no significa generar arte**.
- Para video: FFmpeg para cortes/mezcla/transcodificación. Para comprensión total, agregar muestreo de fotogramas con VLM y transcripción STT local. Para generación IA de video, necesitarás modelos compatibles y GPU adecuada.
- Para voz: Whisper/Vosk/faster-whisper/Piper o similar, validados con el hardware de Windows.
- Para documentos: bibliotecas Python + LibreOffice para formatos y exportaciones de calidad.

## Ciberseguridad y servicios comerciales autorizados

SKY puede ayudar a clientes con autorización verificable: auditorías defensivas de sus propios sitios y dispositivos, diagnóstico de equipos, respaldo y recuperación de datos, revisión de permisos, recuperación mediante mecanismos oficiales de cuentas y fabricantes, inventario y hardening, y formación de seguridad.

**Queda fuera del alcance:** espionaje de mensajes de parejas o terceros, bypass de PIN/FRP/iCloud, acceso a números ajenos, robo de credenciales, control de dispositivos sin consentimiento y explotación de sistemas fuera del contrato de autorización. El pago del cliente no constituye autorización del propietario del dispositivo.

## Validación requerida

- Pruebas `tests/test_sky_multimodal_reader.py` y CI en Windows/Linux.
- Probar Office real, interpretación de imagen con un VLM instalado y reproducción/video en hardware real.
- Verificar interfaz después del cambio a enlaces multimedia temporales; algunos clientes anteriores pueden requerir actualización para renovar enlaces caducados.
- No desplegar ni fusionar automáticamente. El cambio está aislado en una PR en borrador.
