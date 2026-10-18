# Changelog v9.1 — SKY IA

- [Added] `neural_core/sky_integrations.py`: diagnóstico local de dependencias y SQLite con lectura segura.
- [Added] `GET /api/sky/integrations`: protegido por clave `X-SKY-KEY`.
- [Added] `sky_preflight.py`: verificador local con salida humana/JSON y código de salida.
- [Changed] `metaverse/static/studio.html`: nuevo Centro de Integración y versión visible.
- [Fixed] `metaverse/static/studio.js`: diseño anterior invalidado si los parámetros o dictado cambian; guardado de preview coherente con la acción específica.
- [Changed] Arrancadores Windows/Linux/macOS ejecutan el diagnóstico previo.
- [Added] `tests/test_sky_v9_1_integration.py`: 4 pruebas con flujos integrados y control de privacidad.
- [Verified] 120 pruebas de regresión, sintaxis, y petición HTTP a Uvicorn real.
- [Unchanged] BAQUEANO público, operaciones bancarias, autenticación de dispositivos y despliegues externos.
