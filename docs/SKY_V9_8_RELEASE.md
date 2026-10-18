# SKY IA v9.8 — Advanced Creative Intelligence

**Visión y promoción del proyecto:** Oscar Elieser Chamorro Guzmán.

## Cambios comprobados en el paquete maestro

- Capas de imagen con máscaras PNG independientes, inversión y suavizado.
- Segmentación asistida con OpenCV GrabCut a partir de un rectángulo señalado por el creador.
- Títulos animados en videos MP4 mediante dos posiciones clave, fundidos alfa y superposición de imágenes.
- Conservación de máscaras y stickers en exportaciones editables `.skyzip`.
- UI avanzada plegable dentro del estudio; portada de SKY minimalista, BAQUEANO solo para el creador.
- 180 pruebas automatizadas locales pasadas (176 heredadas + 4 nuevas). No son una certificación de producción.

## Estado del repositorio

El repositorio se inicializó vacío. Este commit incorpora documentación y fuentes iniciales de v9.8, **no equivale todavía a publicar los 209 archivos del paquete local completo**. El paquete íntegro debe importarse mediante Git desde la carpeta extraída, conservando este historial.

## Instalación

Python 3.11+; `pip install -r requirements.txt -r requirements_studio.txt`; FFmpeg y FFprobe en PATH. Iniciar mediante `INICIAR_SKY_V9_WINDOWS.bat` o `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765`. Panel privado `/creative`.

## Riesgos y límites

No se dispone aquí de credenciales Gemini reales ni se certificó uso público de alta carga. GrabCut no equivale a segmentación semántica avanzada; dos fotogramas clave no equivalen a la línea de tiempo completa de Premiere. Las pruebas de API y render fueron locales. No se ha modificado BAQUEANO en producción.
