# SKY Video Studio — primera fase

Motor de renderizado real para medios aportados por el usuario. Requiere Python 3.11+, `ffmpeg` y `ffprobe` instalados. No modifica SKY Windows ni Android.

## Uso

Crear `video.json` junto a los archivos:

```json
{
  "format": "vertical",
  "fps": 30,
  "scenes": [
    {"file": "foto1.jpg", "duration": 4},
    {"file": "clip2.mp4", "duration": 6}
  ],
  "audio": "musica_autorizada.mp3"
}
```

Ejecutar:

```bash
python scripts/sky_video_studio.py video.json salida.mp4
```

Formatos: vertical 1080x1920, horizontal 1920x1080, cuadrado 1080x1080. Exportación H.264 MP4, 24–60 fps. Se recorta el centro para llenar el formato; revisar encuadres. Audio opcional, siempre con derechos de uso.

## Estado y límites

- Implementado: montaje secuencial de imágenes y videos, escalado, recorte, exportación MP4 y audio opcional.
- Pendiente de validación: prueba de renderizado extremo a extremo en GitHub y dispositivos.
- No implementado: generación de escenas con IA, animación de objetos, transiciones complejas, voz sintética, subtítulos, orquestación desde SKY Android y Windows.
- Seguridad: el manifiesto no ejecuta comandos; las rutas se pasan como argumentos a FFmpeg. Los archivos multimedia siguen siendo entrada no confiable: procesarlos en un entorno aislado y con límites de recursos antes de exponer el servicio a usuarios.

Este componente no reemplaza la experiencia existente de SKY; es un motor independiente para integrar tras superar pruebas.

## Transiciones

El manifiesto acepta `"transition": "cut"` (por defecto) o `"transition": "fade"`, con `"transition_duration": 0.4` en segundos. Las escenas deben durar más que la transición. El fundido se renderiza mediante el filtro `xfade` de FFmpeg; no se simula en la interfaz. El tiempo final disminuye por el solapamiento de cada transición. El nuevo modo requiere superar la prueba de CI antes de considerarse verificado.

## Subtítulos incrustados (fase de validación)

Añadir al manifiesto `"captions": [{"start": 0.1, "end": 2.0, "text": "Descubrí Nicaragua"}]`. Los tiempos están en segundos y deben ser crecientes, sin solaparse y dentro de la duración total. El texto se incrusta en el MP4 usando el filtro `subtitles` de FFmpeg (requiere una compilación con libass). Este bloque todavía no transcribe audio ni genera subtítulos automáticamente; acepta textos proporcionados. La prueba de CI determina si el renderizado es compatible con el entorno.

## Narración y música mezcladas

El manifiesto admite `"voiceover": "narracion.wav"` y `"audio": "musica.mp3"` simultáneamente. La música se repite hasta la duración del video y, si hay narración, su volumen predeterminado es 0.18. `"music_volume"` permite ajustar el nivel entre 0 y 1. Se mezclan con FFmpeg y se exportan como audio AAC. Es necesario aportar la narración y la música con autorización de uso; **este motor aún no sintetiza voces**. Las pruebas de CI incluyen la presencia de pistas de video y audio en el MP4 final.

## Título de apertura

Añadir `"title": "Descubrí Nicaragua"` y opcionalmente `"title_duration": 2.5` (0.3–10 segundos). FFmpeg incrusta un título centrado en blanco, con fondo semitransparente, durante los primeros segundos del video. Requiere soporte `drawtext` y una fuente instalada en el sistema de renderizado. La tipografía y las animaciones premium todavía no están implementadas.

## Narración local automática (eSpeak NG)

Instalar `espeak-ng` en el entorno de renderizado. Crear `guion.txt` (UTF-8) y ejecutar:

```bash
python scripts/sky_video_narration.py guion.txt narracion.wav --voice es --speed 155
```

Después indicar `"voiceover": "narracion.wav"` en el manifiesto del video. El sintetizador es local, determinista y no usa servicios externos. Su timbre es robótico: **no representa una voz neuronal premium**. Para voces naturales será necesaria una integración TTS adicional, con autorización, gestión de credenciales y pruebas de calidad. La ejecución automática de ambos pasos desde Android aún no está integrada.

## Producción en un único comando

El orquestador `scripts/sky_video_production.py` recibe un proyecto JSON con escenas reales, texto de narración y las opciones existentes de título, subtítulos y música:

```json
{
  "format": "vertical",
  "fps": 30,
  "title": "Descubrí Nicaragua",
  "scenes": [{"file": "destino.mp4", "duration": 6}],
  "narration": "Descubrí lugares inolvidables con BAQUEANO.",
  "captions": [{"start": 0.2, "end": 4.5, "text": "Descubrí Nicaragua"}]
}
```

Ejecutar `python scripts/sky_video_production.py proyecto.json resultado.mp4`. La narración local se sintetiza en un WAV temporal, y el renderizador compone el MP4 final. No requiere duplicar comandos manuales. Sigue necesitando medios reales y dependencias FFmpeg/eSpeak NG. No genera escenas con IA, no hace montaje semántico ni ofrece aún una interfaz Android; tampoco asegura calidad de voz premium.

## Voz neuronal local opcional (Piper)

Para usar una voz neuronal con licencia y modelo propios, instalar el ejecutable `piper` en el servidor de renderizado y disponer de un modelo ONNX compatible. Añadir al proyecto:

```json
{
  "narration": "Descubrí Nicaragua con SKY.",
  "narration_engine": "piper",
  "narration_model": "voces/es.onnx",
  "narration_config": "voces/es.onnx.json"
}
```

El orquestador invoca Piper, genera WAV y lo mezcla con el video. Si no hay Piper o modelo, devuelve un error explícito: **no afirma haber sintetizado una voz que no existe**. El modo `espeak` permanece disponible. La prueba de integración real con una voz neuronal requiere instalar un modelo autorizado y comprobar el audio resultante. No se distribuyen modelos ni voces de terceros con SKY.
