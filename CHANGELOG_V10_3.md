# SKY IA v10.3 — Global Platform / Voice & Internationalization

**Dirección y visión del proyecto:** Oscar Elieser Chamorro Guzmán.

## Funciones implementadas (locales, comprobables)

1. Localización: se amplían 40 etiquetas del sistema; traducciones revisadas para pt, fr, ar, zh, ja y sw. El localizador del navegador actualiza mensajes dinámicos y marcadores de posición, mantiene excepciones para conversaciones y documentos privados, permite RTL y cambia de idioma sin recargar.
2. Auditoría lingüística real: `GET /api/i18n/coverage` (acceso privado) y `python scripts/audit_ui_locales.py` reportan etiquetas detectadas por pantalla, traducciones existentes y pendientes. No se presentan los 90 idiomas seleccionables como 90 traducciones completas.
3. Voz local: `GET /api/global-media/voice/local-capabilities`, `POST /api/global-media/voice/local-wav` y `POST /api/global-media/voice/dub-mp4`; motor eSpeak local y FFmpeg. Los idiomas dependen de las voces instaladas, sin transmitir texto a Internet. El MP4 original se conserva.
4. Reconocimiento de voz: endpoint privado `GET /api/global-media/voice/transcription/availability` para diagnosticar la presencia de `faster-whisper` y un modelo local previamente instalado. No descarga modelos automáticamente ni promete transcripción sin él. El dictado del navegador se conserva sujeto a permisos y capacidades de la plataforma.
5. Estudio creativo: un panel plegable de voz local y doblaje, sin ampliar la portada principal.
6. Seguridad: scanner `scripts/security_audit_v103.py` y flujo CI propuesto `.github/workflows/security-v103.yml`. Estos controles no equivalen a una auditoría externa ni certifican seguridad de producción.
7. Versiones anteriores: inventario SHA-256 y archivo histórico separado, con procedimiento Git para alojar snapshots sin reescribir `main` ni incluir secretos. No se considera subida a GitHub un ZIP que solo está en la conversación.

## Pruebas

`PYTHONPATH=. pytest -q` — **205 pruebas aprobadas** (199 anteriores y 6 nuevas), en el entorno local actual. Incluye WAV y MP4 generados realmente.

## Límites pendientes

- El porcentaje de traducciones comprobadas sigue siendo parcial y diferente por idioma/pantalla. Las respuestas generativas dependen del modelo contratado o instalado.
- eSpeak no ofrece voces naturales de estudio ni soporta todos los idiomas listados.
- No hay transcripción local lista para usar sin instalar el modelo; tampoco validación real de Gemini con API key.
- No se ha certificado despliegue público, penetración de seguridad, calidad de traducción automática ni pruebas de escala masiva.
