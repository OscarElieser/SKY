# SKY IA v9.9 — Instalación y uso del Estudio Creativo

**Proyecto impulsado por Oscar Elieser Chamorro Guzmán.**

## Instalación

1. Python 3.11 o 3.12, FFmpeg y FFprobe instalados.
2. Instalar dependencias: `python -m pip install -r requirements.txt -r requirements_studio.txt`.
3. Ejecutar `INICIAR_SKY_V9_WINDOWS.bat` en Windows o el servidor `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765`.
4. Visitar `http://127.0.0.1:8765/creative` y autenticarse con la clave de SKY en el equipo propio.
5. La portada pública sigue minimalista. BAQUEANO y las herramientas de propietario permanecen detrás del acceso administrativo.

## Máscaras guiadas

Importá una imagen. En **Máscaras y selección de objetos** elegí un rectángulo, agregá coordenadas de puntos a conservar como `[[50,50],[65,45]]` y puntos de fondo como `[[0,0]]`. Pulsá **Crear máscara asistida** y aplicala a una capa de imagen. Las coordenadas deben estar dentro de la imagen; GrabCut realiza una segmentación estadística, no garantiza recortes perfectos.

## Fotogramas de títulos

Elegí un proyecto de video con texto en uno de sus clips. Abrí **Fotogramas clave múltiples** e indicá el clip, el JSON de posiciones (segundos `t`, coordenadas `x`, `y`) y la interpolación.

Ejemplo:

```json
[
  {"t":0,"x":-20,"y":40},
  {"t":0.5,"x":40,"y":40},
  {"t":1.0,"x":80,"y":60}
]
```

La duración del último fotograma debe ser menor o igual a la duración efectiva del clip. Pulsá **Aplicar fotogramas**, guardá una versión y renderizá MP4. Los títulos se mueven en la línea de tiempo según el proyecto guardado. El `.skyzip` conserva los puntos.

## API privada

- `POST /api/creative/assets/{id}/selection`: `rectangle`, `iterations`, `foreground`, `background`, `brush_radius`.
- `POST /api/creative/projects`: acepta `caption_keyframes` (2–16) y `caption_easing` en los clips de tipo video.
- `POST /api/creative/projects/{id}/video/render`: encola el render aprobado y conserva la versión de entrada.

## Seguridad y continuidad

- No publicar `.env`, claves, bases `local_data` ni credenciales privadas.
- Hacer respaldo antes de trasladar datos de v9.8.
- Las peticiones administrativas deben incluir la clave configurada en el servidor.
- No compartir los mundos, proyectos o medios privados sin autorización.

## Validación

`python -m pytest -q tests` — 183 pruebas en la versión de entrega.
`node --check metaverse/static/creative.js`

No afirmar producción hasta pasar pruebas externas de carga, hardware y APIs con credenciales reales.
