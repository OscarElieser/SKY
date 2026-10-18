# SKY IA v9.2 — Cambios verificados

- [Nuevo] `neural_core/sky_projects.py`: SQLite privado para proyectos, enlaces,
  notas, conversaciones, versiones y ZIP de resultados.
- [Nuevo] 14 rutas autenticadas de Project Hub (alta, listado, edición optimista,
  asociación de entregables, notas, mensajes, exportación).
- [Mejora] `POST /api/sky/assist`: contexto de proyecto y conversación persistente
  con controles opt-in independientes de memoria global.
- [Mejora] `metaverse/static/studio.html`, `studio.js`, `studio.css`: panel Project Hub,
  selector de proyecto, notas, historial, vinculación de elementos existentes,
  exportación ZIP, avisos de privacidad para proveedores externos.
- [Mejora] Exportación del mundo `.json` y `.glb`, HTML y especificación de diseño
  JSON, documentos Office en sus formatos originales.
- [Mejora] Diagnóstico incluye `sky_projects.sqlite3` y mantiene lectura de solo
  lectura al evaluar integridad; versión de API y preflight actualizada a 9.2.0.
- [Validado] 131 pruebas automatizadas y smoke test de Chromium con backend
  FastAPI de pruebas y sin errores JavaScript.
- [Conservado] Los 120 tests de v9.1, rutas existentes, metaverso, redes sociales,
  Office Studio, Neural Core, motores, dispositivos, BAQUEANO y exportador.
- [Sin cambios] No se modificó ningún sistema de producción, cuenta bancaria,
  proveedor de pago ni servicio externo.
