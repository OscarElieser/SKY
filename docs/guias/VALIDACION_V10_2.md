# Registro de validación — SKY v10.2

- Base verificada: ZIP v10.1 íntegro; `191 passed` antes de cambios.
- Código v10.2: `199 passed` al ejecutar `PYTHONPATH=. pytest -q` (191 heredadas + 8 nuevas).
- Multimedia: `SKY_Global_subtitulos_reales.mp4` renderizado desde un MP4 auténtico y SRT en español/árabe; PNG extraído con FFmpeg, y VTT Unicode.
- Seguridad: pruebas para MFA, caducidad/revocación, sesiones no reutilizadas, origen de peticiones, aislamiento de idiomas por cuenta y bloqueo del modo público incompleto.
- UI: `node --check` de los scripts y acceso de páginas validado por API. **Chromium no se pudo ejecutar contra localhost**: `net::ERR_BLOCKED_BY_ADMINISTRATOR`. Por tanto no se ha certificado visualmente en un navegador real.
- No se realizaron llamadas reales a Gemini/gTTS, ni Redis real, ni se desplegó el servidor públicamente. No se han hecho pentests independientes.

Comandos:

```bash
PYTHONPATH=. pytest -q
for f in metaverse/static/*.js; do node --check "$f"; done
python scripts/benchmark_sky_v10.py --requests 80 --workers 8
```

La prueba de latencia es sobre una ruta ligera y no representa el rendimiento del renderizador o el metaverso bajo carga masiva.

Microbenchmark local complementario de ruta `/api/creative/capabilities`: 80 solicitudes con 8 trabajadores, **0 errores**, p50 15.83 ms, p95 20.39 ms y ~482 solicitudes/s en el entorno de prueba. Estos números no son un SLA ni representan los costos de video, IA o comunidad.
