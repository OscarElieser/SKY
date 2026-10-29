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
