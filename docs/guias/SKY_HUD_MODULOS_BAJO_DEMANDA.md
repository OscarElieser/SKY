# SKY — un solo HUD con módulos bajo demanda

El acceso principal sigue siendo http://127.0.0.1:8765/ y conserva la API SKY. El catálogo Streamlit está en neural_core/sky_module_registry.py. El archivo anterior anunciaba 26 módulos, pero tiene **27 entradas** (incluye SKY Sports).

## Activación
- Orden escrita, voz del HUD o voz Vosk: «SKY, activá el módulo Educación e investigación».
- Las páginas nativas SKY, Studio 3D, Office y Metaverso conservan rutas actuales.
- Las demás conservan temporalmente su funcionalidad en app.py (Streamlit). El puerto 8501 se inicia **sólo cuando se pide por primera vez uno de estos módulos** y se muestra dentro de una ventana del HUD. Esto es un **puente compatible**, no una migración completa a FastAPI.
- app.py selecciona la sección por el identificador conocido en sky_mod. Ninguna orden ejecuta automáticamente tareas peligrosas; sólo abre una interfaz.
- La voz Vosk añade un evento SQLite y el HUD autenticado recoge órdenes de módulos sin crear otro capturador de audio.
- Las herramientas previas del HUD siguen disponibles en el catálogo avanzado.

## Archivos adjuntos
- El botón 📎 aparece dentro del chat. Permite cualquier extensión, hasta 50 MiB por archivo.
- Los contenidos de texto extraíbles se ofrecen como datos no confiables al análisis con Ollama **local**; las instrucciones de los archivos no son órdenes autorizadas.
- Se pueden recibir fotos, videos y binarios pero no se garantiza reconocerlos ni interpretarlos sin un módulo especializado.
- No se ejecuta código adjunto.

## Pruebas recomendadas
1. Antes de actualizar Windows, resguardar los cambios sin commit y no destruir stash@{0}.
2. En la rama de pruebas, ejecutar: python -m unittest discover -s tests -p test_sky_module_registry.py -v.
3. Iniciar SKY una vez. 8501 permanece apagado hasta activar un módulo heredado.
4. En el HUD pedir: «activá el módulo Finanzas personales». Debe abrirse una ventana integrada.
5. Con HUD abierto y Vosk funcionando: «SKY, abrí el módulo Biblioteca y memoria».
6. Adjuntar archivo .txt y pedir: «resumí el archivo». Comprobar respuesta local y errores explícitos.

## Limitaciones reales
- Los módulos opcionales sólo funcionan si ya tienen dependencias, credenciales y servicios configurados.
- Streamlit continúa siendo un servicio interno separado, aunque se navegue sólo en 8765. No se descarga automáticamente al cerrar la ventana para no interrumpir tareas.
- El comportamiento de iframe, cookies, cargas de archivos Streamlit y Vosk debe validarse en el Windows real.
- Un Ollama lento puede seguir alcanzando el límite de 90 segundos en el HUD. Esta mejora no resuelve todavía ese límite.
- No se elimina código ni se recupera automáticamente el respaldo local de Git.
