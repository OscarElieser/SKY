# Validación SKY v11.0

- **Regresión local:** 286 pruebas pasaron en tres grupos (109 + 87 + 90), incluyendo 17 nuevas (`tests/test_sky_v11_0_production.py`). La ejecución monolítica se cortó por tiempo; no se contó como aprobada.
- **HTTPS genuino en tests:** certificado de prueba válido para `sky.test` aceptado; certificado para `wrong.test` rechazado.
- **Docker:** checks estructurales de Compose pasan. Pila Docker real requiere confirmar el nuevo workflow de GitHub Actions.
- **Voz:** la CI medirá Whisper base. No asumir que cumple WER; `--report-only` publica evidencias y `--enforce` falla bajo WER superior al objetivo.
- **Integridad:** manifiesto SHA-256 del ZIP; no incluir secretos, medios privados ni SQLite.
- **Producción:** no certificada.

- GitHub Actions v11 inicial: Docker/Redis/HTTPS funcionales antes de una comprobación de puerto con falso positivo; regression GLB falló por SciPy no instalado; ASR auténtico ejecutado pero español WER=1.90. Incidencias corregidas en el código excepto precisión de voz, que permanece pendiente.
