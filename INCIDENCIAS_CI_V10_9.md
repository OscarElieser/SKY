# SKY v10.9 — Resultados reales de integración, 19 de octubre de 2026

**Repositorio:** OscarElieser/SKY. **Autoría conceptual:** Oscar Elieser Chamorro Guzmán.

La primera ejecución GitHub Actions del workflow v10.9 (run `39299384091`) **falló** en tres trabajos. La publicación del código no equivale a un despliegue de producción verificado.

1. **Regresión:** falló `test_subtitle_render_actual_mp4` por `ModuleNotFoundError: cv2`. Se corrigió la línea de instalación del job para incluir `opencv-python-headless>=4.10,<5`. Las 12 pruebas nuevas del stack siguen aprobadas tras el cambio local.
2. **Docker completo:** Compose llegó a crear los cuatro servicios, pero marcó al renderizador `unhealthy`. El Dockerfile hereda un HEALTHCHECK HTTP apropiado para la API y no para el worker. Se desactivó ese chequeo HTTP heredado **solo en el servicio renderer** de los dos archivos Compose; el estado de salud de la API y de Redis continúa comprobándose.
3. **Whisper auténtico:** el runner descargó `Systran/faster-whisper-tiny`, sintetizó tres WAV con eSpeak y ejecutó tres transcripciones reales. WER: **es=0.9000, fr=0.7500, en=0.3333**; el umbral `0.8000` falló para español. No se cambió el umbral ni se inventó una aprobación. Se requieren grabaciones naturales consentidas y posiblemente un modelo mejor antes de afirmar calidad global.

**Separación de evidencias:** 269 pruebas locales aprobadas en tres lotes; Docker y voz real se ejecutaron en GitHub Actions y generaron los resultados anteriores, no en la máquina local. La restauración aislada de un backup sintético no es una restauración en un segundo servidor físico. BAQUEANO no fue modificado.

**Pendiente:** consultar el workflow reejecutado después de las correcciones, solucionar otros errores si aparecen y probar la restauración en un servidor diferente con credenciales y autorización del operador.
