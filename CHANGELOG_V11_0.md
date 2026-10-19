# SKY IA v11.0 — Production Readiness / Seguridad / Voz Global

**Dirección conceptual:** Oscar Elieser Chamorro Guzmán. **BAQUEANO:** sin cambios.

## Funciones añadidas y verificadas

- Probe de salud del worker renderizador basado en la presencia del proceso de trabajo, sin abrir red ni inventar un endpoint HTTP; corrige `docker compose up --wait`.
- Proceso independiente de render sin privilegios, solo lectura y `network_mode:none`, conservando secretos fuera del worker.
- Prueba de carga sintética limitada mediante HTTPS con validación real de CA y nombre DNS (rechaza certificados para un host distinto).
- Dependencias de CI para OpenCV y lectura Excel; versiones de Numpy/Trimesh que corresponden con una combinación local previamente verificada para GLB.
- Prueba real de un modelo ASR multilingüe `faster-whisper-base` en GitHub Actions con métricas por idioma, sin guardar audios/transcripciones en artifacts; **no es certificado de calidad**.
- Evaluación por separado: una prueba funcional del modelo puede aprobar aunque su WER no cumpla el objetivo; un `workflow_dispatch` con `enforce_voice_quality=true` exige el umbral y falla honestamente si no se cumple.
- Mantiene respaldo/restauración cifrada aislada; **no equivale a una restauración en un servidor físico distinto**.
- Workflow v11 activo y workflow v10.9 conservado solo para ejecución manual para evitar duplicar inferencias reales en cada `push`.

## Evidencia y límites

- `PYTHONPATH=. SKY_CREATIVE_WORKER=0 SKY_WORKFLOWS_ENABLED=0 pytest -vv tests` : **282 pruebas locales aprobadas**, sin fallos.
- 13 pruebas nuevas, incluyendo un servidor HTTPS de prueba y verificación de nombre en certificado.
- Docker no está instalado en el entorno local: el despliegue de cuatro contenedores debe superar el workflow de GitHub; no afirmar éxito antes de comprobarlo.
- La primera ejecución v10.9 con Whisper tiny tuvo WER es=0,90, fr=0,75, en=0,3333. La precisión de `faster-whisper-base` no se ha verificado hasta consultar su propio run.
- El test de carga ataca solo una ruta de salud sintética en loopback, no demuestra capacidad global, coste de GPU, capacidad multiusuario ni resistencia a un ataque real.
- Pendientes: pentest independiente, WAF, observabilidad, rotación real en servidor, restauración en segundo equipo físico, auditoría de privacidad y voz con participantes autorizados.
