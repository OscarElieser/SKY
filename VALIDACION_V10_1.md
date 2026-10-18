# Evidencias de validación SKY IA v10.1

- Base comprobada: SKY v10.0 del proyecto, 185 tests existentes.
- `PYTHONPATH=. pytest -q`: **191 passed** (185 heredadas y 6 nuevas), en el entorno de desarrollo 18 de octubre de 2026.
- `node --check` de los tres scripts principales: sin errores de sintaxis.
- Se levantó un servidor Uvicorn auténtico para comprobar la API HTTP y se completó la suite con FastAPI TestClient.
- Un `sky_render_worker.py` ejecutado como subproceso distinto completó una cola de render, generó un MP4, un fotograma PNG y un proyecto `.skyzip` editables.
- Se verificó con fotogramas reales que una máscara alfa pasa de un fotograma oscuro a otro visible.
- Pruebas de host desconocido, cabeceras, caché privada, entrada de JSON grande, acceso sin clave, traducción no consentida y preferencia de idioma.
- No hay credencial `GEMINI_API_KEY` configurada aquí. Se mantiene el endpoint de prueba voluntaria, pero **Gemini real no está validado**.
- El navegador Chromium de este entorno bloqueó acceso HTTP y RPC a servidores locales, por lo que la validación integral visual quedó pendiente. No debe interpretarse como prueba satisfactoria de interfaz.
- No se ha realizado prueba de penetración, auditoría de dependencias de terceros ni ensayo de carga distribuida.
- No se ha modificado BAQUEANO en producción.
