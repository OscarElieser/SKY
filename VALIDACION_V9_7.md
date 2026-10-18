# VALIDACIÓN SKY IA v9.7 — Creative Studio & Reliability

## Resultados técnicos comprobados

- **176 pruebas automatizadas superadas** (`python -m pytest -q`). Se conservaron las 162 heredadas y se añadieron 14 pruebas de la nueva versión.
- Compilación Python de los módulos `neural_core`, `metaverse` y respaldo sin errores de sintaxis.
- JavaScript nuevo `metaverse/static/creative.js` pasó `node --check`.
- SKY Integration Center reconoce el módulo creativo, su base multimedia y detecta FFmpeg; diagnóstico local sin errores críticos.
- Pillow generó físicamente un PNG a partir de varias capas independientes y una versión WebP diferente sin sobrescribir el original.
- FFmpeg/FFprobe produjeron un **MP4 real desde videos originales** con dos clips y leyenda, otro **MP4 real generado a partir de fotos** y un ejemplo de montaje exportado en `ejemplos/sky_v9_7/`.
- El servidor WebSocket / FastAPI existente conserva tests previos; las rutas privadas del editor rechazaron peticiones sin `X-SKY-KEY` y tokens sociales.
- El worker del servidor completó un render en segundo plano **sin llamar manualmente al motor**, además de registrar progreso.
- La cola marca un trabajo en curso al reiniciar como `needs_review`; no reejecuta a escondidas. Un render pendiente usa una receta **congelada** aunque se edite el proyecto después.
- Se verificaron operaciones de biblioteca, validación de archivos, límites, control de versiones, instrucciones locales de edición y exportación/importación de paquetes `.skyzip`.
- El generador Gemini se probó **mediante un proveedor falso inyectado** en la prueba, para evitar uso de claves privadas. **No** se realizó ninguna llamada externa a la API real en esta validación.

## Interfaz

- El HTML y JS se integraron al servidor real de SKY (`/creative`) y no aparecen como nuevas tarjetas en la portada principal: el acceso está dentro de `Espacios`.
- La automatización visual del navegador Chromium quedó bloqueada en la navegación a `localhost` por una política del entorno de pruebas. No se afirma que ese recorrido end-to-end esté validado visualmente.
- Próxima prueba necesaria en dispositivo del propietario: acceso al estudio, carga de medios, previsualización y render con FFmpeg local.

## Alcance y limitaciones

Este estudio realiza edición **básica/intermedia** real de imágenes y videos. No equivale a todas las capacidades de Adobe Photoshop/Premiere o CapCut; no se certificó GPU, render 4K profesional, edición multicámara, animaciones avanzadas por keyframes, generación fotorrealista automática de películas ni servicio de producción público. Los modelos de IA externos requieren sus propias credenciales y pruebas.

La plataforma existente de BAQUEANO no se modificó ni se desplegó desde esta versión.
