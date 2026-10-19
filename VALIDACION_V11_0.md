# Validación SKY v11.0

- **Suite completa local:** 282 pruebas pasan, incluyendo 13 nuevas (`tests/test_sky_v11_0_production.py`). Se ejecutó `pytest -vv tests` con dependencias locales y bandera de workers desactivada.
- **HTTPS genuino en tests:** certificado de prueba válido para `sky.test` aceptado; certificado para `wrong.test` rechazado.
- **Docker:** checks estructurales de Compose pasan. Pila Docker real requiere confirmar el nuevo workflow de GitHub Actions.
- **Voz:** la CI medirá Whisper base. No asumir que cumple WER; `--report-only` publica evidencias y `--enforce` falla bajo WER superior al objetivo.
- **Integridad:** manifiesto SHA-256 del ZIP; no incluir secretos, medios privados ni SQLite.
- **Producción:** no certificada.
