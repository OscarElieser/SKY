# Validación de SKY IA v9.5

- **154 pruebas pytest aprobadas**, incluyendo las 146 de v9.4 y ocho nuevas para Intelligent Workspace.
- `node --check metaverse/static/sky-home.js`: sin errores de sintaxis.
- `python -m compileall -q`: sin errores de sintaxis en los módulos añadidos.
- `python sky_preflight.py --json`: diagnóstico local sin error crítico; incluye base de datos de Intelligent Workspace.
- **Servidor Uvicorn HTTP real:** solicitud -> propuesta -> aprobación -> programación -> finalización; 4 resultados registrados y ZIP de proyecto con `.docx`, `.html`, `.glb` y metadatos JSON. Archivo de prueba en `ejemplos/sky_v9_5/VALIDACION_HTTP_REAL.json`.
- **Interfaz Chromium:** inició sesión como propietario, generó propuesta de cuatro pasos y aprobó el flujo mediante llamadas a la API real reenviadas por un transporte local de pruebas. No se registraron errores de JS. Imagen `sky95_workspace_preview.png`.

**Límites:** Chromium bloqueó navegación directa a localhost en este entorno; la prueba de interfaz utiliza un proxy de peticiones del harness de pruebas, no una captura del despliegue productivo. No se ejecutaron pruebas de llamadas reales a Gemini, OpenAI o Anthropic, cámaras o micrófonos físicos, operaciones financieras ni carga masiva. No se modificó BAQUEANO en producción.
