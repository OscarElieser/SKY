# SKY IA Universal v9.7 · Creative Studio & Reliability

**Visión y promoción de SKY IA: Oscar Elieser Chamorro Guzmán.**

## Qué cambia

Se incorpora un **estudio creativo real** dentro de `Espacios → Estudio creativo`, conservando la pantalla de conversación minimalista y el control privado BAQUEANO. Usa las herramientas existentes de SKY y añade:

- **Biblioteca personal persistente:** importar PNG/JPG/WEBP, MP4/MOV/WEBM/MKV y formatos habituales de audio; archivos almacenados por SHA-256 y protegidos con la clave privada `X-SKY-KEY`.
- **Editor de imágenes no destructivo:** capas de fotografías, textos y rectángulos; posición, opacidad, tamaño, recorte/rotación y ajustes de brillo, contraste, saturación, nitidez y desenfoque desde el motor/API. Exportación PNG, JPEG o WEBP.
- **Editor de video local:** secuencias de clips de video o fotos, recorte por intervalo, cambio de velocidad, textos por clip, pista musical opcional y exportación MP4 con FFmpeg y AAC. Video máximo **10 minutos** por proyecto; máximo 20 clips.
- **Edición por instrucciones escritas:** comandos comprobables como «Agregá texto Innovación con SKY», «contraste 1.5», «fondo #112233», «Pon texto Bienvenidos en clip 1». No se acepta una orden arbitraria fingiendo que SKY la interpretó.
- **Generación opcional de imágenes con Gemini:** la persona activa la operación expresamente y necesita `GEMINI_API_KEY`. Las pruebas no consumieron API de Gemini real.
- **Proyectos versionados**, cola persistente de renders, recuperación conservadora después de cortes, biblioteca de resultados y formatos portables `.skyzip` para conservar archivos y receta de edición al trasladarse a otra instalación.
- **Integración con Project Hub:** los proyectos creativos pueden vincularse al proyecto maestro de SKY y exportar la receta editable más sus medios (hasta 45 MB en el ZIP de Project Hub). Para medios mayores, descargarlos directamente desde Creative Studio.

## Instalación

1. Descomprimí el **ZIP completo** en una carpeta distinta de SKY v9.6. Necesitás Python compatible con el proyecto; los tests de este entorno se ejecutaron con Python 3.13, pero para instalación personal se recomiendan Python 3.11 o 3.12 y las versiones de dependencias de `requirements.txt`.
2. Instalá **FFmpeg y FFprobe** en el sistema operativo. Probá `ffmpeg -version` y `ffprobe -version` en una terminal. Son indispensables para exportar MP4; la edición de imágenes sigue funcionando sin FFmpeg.
3. Ejecutá `python -m pip install -r requirements.txt` y configurá opcionalmente `.env` a partir de `.env.example`. Nunca compartas las claves reales.
4. Ejecutá `INICIAR_SKY_V9_WINDOWS.bat` o `bash iniciar_sky_v9_linux_mac.sh` según corresponda.
5. Abrí `http://127.0.0.1:8765/sky`, iniciá sesión con **Acceso privado** y entrá en **Espacios → Estudio creativo**, o abrí `http://127.0.0.1:8765/creative`.
6. Seleccioná imágenes/videos desde la biblioteca, creá tu proyecto y probá cambios. Guardá cada revisión, exportá los medios finales y, si querés trasladar el editor, **Exportar proyecto editable** (`.skyzip`).

### Ejemplos completos y reutilizables

En `ejemplos/sky_v9_7/`:
- `SKY_fondo_antes.png` y `SKY_portada_editada.png`: imagen original y versión con varias capas.
- `SKY_video_montaje_real.mp4`: video de tres segundos producido realmente con el motor local.
- `SKY_portada_editable.skyzip` y `SKY_video_editable.skyzip`: proyectos portables con sus medios, importables desde la interfaz de SKY.
- Los archivos `.json` son **recetas orientativas** que utilizan identificadores originales; para restaurar y editar en otra instalación usá los `.skyzip`.

## Seguridad y límites

- Las operaciones privadas requieren `X-SKY-KEY`; las cuentas sociales **no tienen acceso** a los archivos, ediciones ni trabajos del creador.
- FFmpeg se invoca como proceso local con argumentos explícitos; **no** se ejecuta texto del usuario como comandos shell. Los archivos importados se validan por contenido.
- Máximo **80 MB por archivo**, **30 minutos por video fuente**, 35 capas, 20 clips, **10 minutos de video final**. Trabajos interrumpidos pasan a `needs_review` y solo se reintentan si se solicita.
- Las imágenes generadas por Gemini usan el modelo que admita tu cuenta; pueden aplicar precios/límites. No son generación local y se realiza una llamada externa solamente después de elegirla.
- **No es una copia completa de Photoshop, Premiere o CapCut.** No hay aún edición multicámara, keyframes complejos, motion tracking, máscaras avanzadas dibujadas, color grading profesional LUT, modelado fotorrealista ni generación autónoma de películas enteras. Es un estudio útil de edición básica/intermedia y producción real de archivos.
- La pantalla principal conserva un solo acceso **Espacios**, y BAQUEANO continúa reservado a la clave del creador. No se modificó baqueanonicaragua.com.

## Migración desde v9.6

1. Apagá SKY y hacé respaldo de `local_data/`, archivos generados y `.env`.
2. Extraé la versión nueva aparte. Copiá tus datos únicamente con SKY apagado.
3. Las nuevas tablas `assets`, `projects`, `project_versions`, `jobs`, `job_specs` y `exports` se crean **en una base propia** (`local_data/sky_creative.sqlite3`). La biblioteca reside en `local_data/sky_creative/media/`.
4. Ejecutá `python sky_preflight.py --json` y `python sky_backup.py` para un respaldo. El respaldo extendido (`backup(include_extended=True)`) ahora incluye la nueva base y sus medios.
5. **No incluyas archivos `.env` ni `local_data` en ZIP que compartás.**

## Validación

Los tests verifican preservación de suites antiguas, imágenes compuestas de verdad, clips reales FFmpeg, control de acceso, versionado, trabajos interrumpidos, edición textual limitada, ZIP portables, API y coherencia de planes de render. Consultá `VALIDACION_V9_7.md` para cifras finales y pasos de reproducción.
