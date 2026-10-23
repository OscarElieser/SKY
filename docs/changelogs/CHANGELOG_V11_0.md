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

- **286 pruebas locales aprobadas en tres grupos separados** (109 + 87 + 90), por límite de ejecución del entorno; no se afirmó una única ejecución continua para esta revisión.
- 17 pruebas nuevas, incluyendo un servidor HTTPS de prueba y verificación de nombre en certificado.
- Docker no está instalado en el entorno local: el despliegue de cuatro contenedores debe superar el workflow de GitHub; no afirmar éxito antes de comprobarlo.
- La primera ejecución v10.9 con Whisper tiny tuvo WER es=0,90, fr=0,75, en=0,3333. La precisión de `faster-whisper-base` no se ha verificado hasta consultar su propio run.
- El test de carga ataca solo una ruta de salud sintética en loopback, no demuestra capacidad global, coste de GPU, capacidad multiusuario ni resistencia a un ataque real.
- Pendientes: pentest independiente, WAF, observabilidad, rotación real en servidor, restauración en segundo equipo físico, auditoría de privacidad y voz con participantes autorizados.

## CI — correcciones después de ejecutar el stack real

- La pila Docker de GitHub levantó los **cuatro servicios saludables** y validó HTTPS y Redis. Las 60 consultas HTTPS terminaron sin errores, p95=56,88 ms. El job falló posteriormente porque el auditor trataba un puerto **EXPOSE sin publicar** como puerto del host. Se corrigió con `scripts/ci_exposure_audit_v110.py` y pruebas de ambos casos.
- Las pruebas GLB del runner fallaban porque faltaba SciPy (`trimesh` importa `scipy.sparse`). Se añadió SciPy a requisitos y al conjunto de versiones verificadas.
- Whisper base realizó tres transcripciones sintéticas: WER es=1,9000, fr=0,1667, en=0,3333. El español **no** alcanzó el umbral de 0,80; el modelo no se considera aprobado.
- Estas correcciones deben comprobarse mediante un nuevo run de GitHub; hasta entonces no afirmar pipeline verde.
