# SKY IA Android — capacidades comprobables y plan de excelencia

**Revisión:** 30/10/2026 (hora Nicaragua). **Propósito:** elevar las calificaciones de la auditoría mediante resultados y evidencias, nunca cambiando puntuaciones arbitrariamente ni afirmando que un mock es producción.

## Identidad y producto

SKY es una IA propia como producto, orquestación, experiencia y controles. Se pueden implementar capacidades comunes de asistentes avanzados (conversación, investigación, archivos, creación, código, voz, automatización y memoria) con herramientas y modelos legalmente disponibles, **sin copiar pesos, servicios privados o tecnología propietaria de ChatGPT**. Ollama en infraestructura controlada es la prioridad. La autoría, historial, identidad visual y funciones existentes de SKY Windows y Android se deben conservar. BAQUEANO queda completamente aislado.

## Incremento técnico de esta iteración

- `MobileChatRequest` en SKY API permite **hasta 16.000 caracteres** solo para `sky_auto` y `ollama` autenticados. Los demás proveedores conservan el máximo **4.000**. La SKY Home API general conserva su límite previo.
- `sky_smart_router` y `sky_inference_gateway` validan el límite por mensaje. Los prompts largos **no se envían a nubes externas**, aunque exista autorización general de respaldo; si Ollama falla, se conserva el contenido y se devuelve un error en lugar de recortar/transmitir parcialmente.
- La inferencia propia puede solicitar **hasta 2.048 tokens de salida** (máximo aceptado por el gateway actual). Esto no representa un DOCX de 350 páginas ni una conversación ilimitada. El contexto real del modelo depende de su tamaño, VRAM y configuración.
- `SkyOwnApiRoutingPolicy` conserva `sky_auto` como valor predeterminado y habilita hasta 16K solo en rutas propias. La selección manual externa, compatibilidad Gemini y seguridad de consentimiento siguen disponibles.
- La interfaz Android ya no exige escribir «Modo profundo» solo para enviar un texto largo a nuestra API. Para Gemini u otros proveedores, conserva las restricciones y la selección explícita.
- `sky_answer_quality.system_prompt` da orientación de rigor contextual a **investigación académica, matemáticas, física, química, programación, y solicitudes de archivos**. Es un contrato de instrucciones *enviado al modelo real*; no una supuesta creación de archivos ni mejora de exactitud sin evaluación.
- `tests/test_sky_smart_mobile_api.py`, `tests/test_sky_smart_router.py`, `tests/test_sky_answer_quality.py` y las pruebas Kotlin verifican la interfaz y el protocolo con stubs/mocks únicamente. No son evidencia de un GPU de producción ni de respuestas científicamente correctas.
- `scripts/verify_sky_local_inference.py --long-academic` exige un **modelo Ollama real** instalado y ejecuta un prompt de unos 11.500 caracteres con identificación de operación y métrica de tokens, sin proveedores comerciales. Si no hay modelo, falla explícitamente sin fingir resultados.

## Matriz para elevar puntuaciones con evidencia

| Área | Criterio de salida medible | Prueba exigida |
|---|---|---|
| Android | APK firmada del mismo commit de `main`; 0 errores críticos en flujos principales; Android API 35/36 y Samsung físico | CI verde + video/log de pruebas físicas y permisos |
| Exactitud y calidad | Conjunto de al menos 100 solicitudes reales (academia, ciencias, código, operaciones, archivos) con evaluación humana y fuentes cuando proceda; registrar aciertos y fallos | Reporte reproducible, criterios y evidencia sin datos sensibles |
| Voz | Manos libres con consentimiento, activación y suspensión persistentes, bloqueo de pantalla conforme a Android, medición de interrupciones y consumo | Prueba de 30 min en Samsung con permisos y límites reales |
| Multimedia | Reproducir música solicitada con audio audible y controles; no afirmar ejecución por solo abrir app | Prueba con volumen multimedia, sesión y resultado observable |
| Archivos | Abrir y leer PDF/DOCX, imagen y video dentro de límites reales; confirmar qué hacer; vista previa antes de sobrescribir | Muestras de prueba controladas, hashes de salida, sin borrar originales |
| Historial | Nuevo chat limpio, anteriores accesibles y SQLite migrado sin pérdida | Test instrumentado con reinicio y recuperación |
| Seguridad | Sin secretos en APK; token limitado revocable; consentimiento; pruebas de aislamiento por usuario | Pentest autorizado, asesor Supabase, auditoría permisos y RLS |
| Escalabilidad | Inferencia GPU propia en HTTPS; SLO medido; cola y límite por cliente; prueba controlada de 10 → 100 sesiones | Latencia p50/p95/p99, errores, recursos, saturación y recuperación |
| Sostenibilidad | Costos por 1.000 tokens y por usuario, presupuesto, retención, reposición de GPU, respaldo | Modelo financiero a partir de uso real |
| Lanzamiento | Versionado trazable, licencias, Términos y Privacidad, soporte y prueba piloto | Revisión independiente y decisión GO/NO-GO documentada |

Las metas son **criterios futuros**, no mediciones ni prestaciones implementadas. Un puntaje solo se actualiza al aprobar su criterio con evidencia.

## Capacidad comparable a asistentes avanzados: estado real

**Capacidades existentes o en desarrollo:** conversación con varios proveedores, SKY API privada, memoria/historial, clasificación básica de solicitudes, acciones de Android autorizadas, comprensión de algunos archivos, generación de contenido, primeros módulos de voz y modelos locales del lado servidor. Cada una requiere aceptación física o end-to-end antes de certificarse.

**Pendiente de desarrollo y validación:** motor generativo genuino offline dentro de Android, recuperación de documentos con referencias verificadas y evaluaciones anti-alucinación, edición real de Word/Excel/PDF en flujo Android con vista previa, voz manos libres fiable con pantalla bloqueada, orquestación de herramientas transaccionales, aislamiento multiempresa y escalabilidad masiva. No habilitar conexiones directas a sistemas sensibles por una sola instrucción del modelo.

## Puertas de verificación

1. **G0:** `main` compila, backend CI y Kotlin pasan, y ninguna regresión conocida invalida pruebas anteriores.
2. **G1:** modelo Ollama de SKY instalado en servidor controlado; prueba `python scripts/verify_sky_local_inference.py` y `--long-academic` con resultados reales, sin nube externa.
3. **G2:** pruebas instrumentadas API 35/36 y aceptación en Samsung; anexar evidencia de voz, YouTube, historial y archivos.
4. **G3:** seguridad de consentimiento, aislamiento por tenant, permisos, gestión de secretos, revisión legal.
5. **G4:** pruebas de carga de concurrencia y 72 h operativas, costos, fallos, alertas y recuperación.
6. **G5:** piloto cerrado monitorizado con usuarios autorizados y cero P0 abiertos.

**Estado de estas puertas:** pendiente de reevaluación final con resultados actuales de CI y pruebas reales. No declarar una versión de APK liberada solo por un commit.

[Auditoría previa](AUDITORIA_SKY_ANDROID_API_PRELANZAMIENTO_2026-10-30.md) · [CI](https://github.com/OscarElieser/SKY/actions) · [Releases](https://github.com/OscarElieser/SKY/releases).
