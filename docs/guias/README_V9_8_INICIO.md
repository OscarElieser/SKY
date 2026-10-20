# SKY IA v9.8 — Advanced Creative Intelligence

**Visión conceptual del proyecto:** Oscar Elieser Chamorro Guzmán.

## Cambios reales de esta versión

- Capas con `mask_asset_id`, `mask_mode`, `mask_invert` y `mask_feather`. Las máscaras son PNG independientes y reutilizables.
- Selección asistida de primer plano usando OpenCV GrabCut (rectángulo de interés); no es segmentación semántica universal.
- Animación de títulos en MP4 con dos posiciones clave (`caption_motion`), movimiento lineal en X/Y y fundidos; overlays de imagen (`sticker_asset_id`).
- Portabilidad de proyecto `.skyzip` conserva las referencias a máscara y sticker.
- Interfaz integrada en `Espacios → Estudio creativo`, con paneles avanzados plegables.
- API autenticada: `POST /api/creative/assets/{asset_id}/selection` recibe `{ "rectangle": [x,y,ancho,alto], "iterations":4 }`.

## Puesta en marcha

1. Python 3.11+ y ffmpeg/ffprobe instalados y accesibles desde PATH.
2. En la carpeta del proyecto: `pip install -r requirements.txt -r requirements_studio.txt`.
3. Ejecutá `INICIAR_SKY_V9_WINDOWS.bat` (Windows), o `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765`.
4. Abrí `http://127.0.0.1:8765/creative`, autenticá con la clave privada que genera SKY y utilizá tu biblioteca.
5. Para crear máscaras, importá una imagen, seleccionala en la biblioteca, abrí «Máscaras y selección de objetos» y asigná la máscara creada a la última capa de imagen.
6. Para animar títulos, creá un proyecto de video, definí el texto del clip, abrí «Animación avanzada» y ajustá posiciones de inicio/final.

## Verificación

`PYTHONPATH=. python -m pytest -q tests`

La validación local de esta entrega registró 180 pruebas superadas, incluidas las anteriores; no se ha certificado producción pública ni uso intensivo. Las llamadas de generación de Gemini siguen necesitando una API real configurada y NO han sido verificadas con credenciales de producción.

## Importante: repositorio GitHub

Destino oficial: https://github.com/OscarElieser/SKY

Si el repositorio remoto solamente contiene el manifiesto inicial o los cambios v9.8 parciales, es necesario **importar este árbol completo** desde el ZIP para tener una copia funcional en GitHub. Desde una carpeta con Git instalado, partiendo de este proyecto extraído:

```bash
git init
git branch -M main
git remote add origin https://github.com/OscarElieser/SKY.git
git fetch origin main
git add .
git commit -m "feat: import SKY IA v9.8 complete platform"
git pull --rebase origin main
git push -u origin main
```

Si algún archivo remoto ya existe con cambios posteriores, revisá las diferencias y resolvé conflictos antes del push. Nunca subas `.env`, claves, tokens, historiales personales ni bases de datos privadas.

## Alcance y seguridad

- Las mejoras de máscaras, fotogramas clave y composición usan herramientas locales, no prometen equivalencia a Adobe Photoshop/Premiere ni generación de largometrajes.
- Los contenidos protegidos por clave administrativa permanecen privados.
- No se modifica BAQUEANO en producción.
