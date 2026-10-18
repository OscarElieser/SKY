# SKY IA v10.0 — Validación técnica

- Pruebas automatizadas: **185 de 185** (`PYTHONPATH=. pytest -q`).
- Pruebas anteriores conservadas: **183 de 183**.
- Pruebas nuevas: seguimiento real con OpenCV y un MP4 generado, composición de capa gráfica, render FFmpeg, extracción de fotograma exacto, exportación/importación `.skyzip`, autenticación y rechazo de parámetros inválidos.
- JavaScript del estudio: `node --check metaverse/static/creative.js`.
- Archivo multimedia de demostración: `ejemplos/sky_v10/SKY_v10_video_seguimiento.mp4`, con muestra de trayectoria JSON y fotograma obtenido del render real.
- Validación con Gemini real: **pendiente** de clave privada y acceso a Internet; el endpoint de prueba requiere intervención explícita y no revela credenciales.
- Validación de público mundial / carga pesada: **pendiente**.
- No se alteró BAQUEANO.
