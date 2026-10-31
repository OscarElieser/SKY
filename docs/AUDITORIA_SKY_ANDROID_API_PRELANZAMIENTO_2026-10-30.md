# Auditoría técnica de lanzamiento — SKY Android / SKY API

**Fecha de revisión:** 30 de octubre de 2026 (Nicaragua).  
**Alcance:** aplicación Android 0.8.42 publicada desde un commit anterior y cambios posteriores en `main`, API FastAPI Python, motor local Ollama, enrutamiento SKY Automático, workflows de GitHub Actions y proyecto Supabase SKY-IA.  
**Dictamen:** **NO-GO para acceso público comercial**. Es razonable preparar un **piloto cerrado** únicamente después de completar los bloqueadores P0.  
**Evidencia:** revisión remota de código, resultados de CI, Releases y metadatos reales de Supabase. **No hubo** instalación en Samsung, prueba de síntesis de voz en el teléfono, benchmark con GPU real, medición de uptime de varios días, prueba de intrusión ni prueba del endpoint con JWT en vivo.

## Resumen ejecutivo

**Lo que existe de verdad**
- Repositorio público `OscarElieser/SKY`, integración `main` y APK Android 0.8.42 *pre-release* firmada, con huella de firmante y SHA256, publicada desde `d2834ef0`. La release NO contiene la totalidad de los cambios posteriores a ese commit.
- APK 0.8.42 declarada en Gradle (`versionCode=55`) y publicada el 31/10/2026 01:37 UTC desde `d2834ef0`, anterior a la selección completa `sky_auto`, nuevas pruebas y despliegue cloud. El código actual en `main` es más nuevo que la APK y requiere una nueva compilación con trazabilidad de commit.
- FastAPI de SKY, endpoints autenticados de chat móvil y tokens limitados por dispositivo. Inferencia Ollama en `neural_core/sky_inference_gateway.py`, con registro agregado de latencia/tokens y máximo dos generaciones simultáneas **por proceso**.
- Enrutador `neural_core/sky_smart_router.py` con Ollama prioritario, respaldos externos opcionales autorizados, enfriamiento por cuota y sin intentos ilimitados.
- Supabase **SKY-IA** está `ACTIVE_HEALTHY`. Función `sky-instagram` activa y nueva función `sky-platform-readiness` **ACTIVE v1 con `verify_jwt=true`**. Esto confirma un servidor de control real, **no** una GPU Ollama en línea. BAQUEANO es un proyecto separado y no se tocó.

**Lo que falta demostrar**
- Generación real desde un modelo Ollama instalado en un servidor de inferencia accesible, con autenticación y HTTPS end-to-end.
- APK 0.8.42 final firmada, todos los workflows relevantes verdes **sobre el mismo commit**, y prueba física de Android 15/16 (especialmente micrófono en segundo plano, volumen YouTube, rutas de archivos, recuperación y voz).
- Seguridad y aislamiento de datos reales para varios clientes distintos, facturación, cuotas por tenant, control de costos, observabilidad y restauraciones comprobadas.
- Prueba de carga y de resistencia, métricas de errores y latencia p95/p99 y objetivo de servicio medidos.

## Evaluación cualitativa (0 a 5; estimación de auditoría, no benchmark)

| Área | Evaluación | Justificación |
|---|---:|---|
| Existencia de funciones Android | 2.5/5 | APK previa firmada y funciones en código; aceptación Samsung de nueva versión sin evidencia |
| Calidad y verificación de respuestas | 2/5 | Algunos tests; incidencia real de tesis desviada a clima; límite de texto backend 4.000 caracteres |
| Seguridad comercial | 2.5/5 | Autenticación móvil y consentimientos, pero la matriz completa de amenazas y privacidad multiusuario no está verificada |
| Escalabilidad de inferencia | 1/5 | Dos inferencias simultáneas/proceso; no hay control distribuido ni workers GPU medidos |
| Sostenibilidad económica | 1.5/5 | No hay costo medido por 1.000 tokens, hardware elegido ni presupuesto por cliente |
| Preparación para distribución pública | 1/5 | Sin evidencia conjunta de versión final, infraestructura de inferencia, piloto, controles comerciales y soporte |

**Conclusión:** producto precomercial con piezas prometedoras de ingeniería, NO plataforma lista para competir comercialmente por SLA ni para miles de usuarios. No es correcto recomendar el uso general hasta cerrar las puertas de aceptación.

## Hallazgos críticos por evidencia

### P0 — Bloquean lanzamiento

1. **API de IA no desplegada en servidor de inferencia real y validado.** El proyecto Supabase activo hospeda función de control/Instagram, no un proceso GPU persistente. Supabase Edge Functions tienen recursos limitados y no son apropiadas para hospedar Ollama grande. `sky-platform-readiness` indica explícitamente `ollama_inference=not_verified`. Requiere instancia de cómputo real con modelo aprobado, endpoint HTTPS propio y prueba `python scripts/verify_sky_local_inference.py`.
2. **Seguridad del fallback inicialmente fallida.** En GitHub Actions `41155473762`, tests de credenciales fallaron **4**, aprobaron **55**, porque el regex llevaba doble escape. Se corrigió en commit `22f6576a`. La ejecución posterior `41156279036` aprobó **59 pruebas de backend** en 4,20 s, incluyendo las cuatro pruebas de credenciales que anteriormente fallaban. Esto no equivale a una auditoría DLP completa ni a aprobación de Android. El detector es heurístico, no DLP completo.
3. **Build actual no certificado.** La release pública 0.8.42 está firmada pero el tag `d2834ef0` no corresponde al `main` actual. Verificar Android debug + release firmado, emulator API 35/36, proveedor 429 y consentimientos en una misma revisión estable. No publicar si hay fallos o workflows cancelados.
4. **Android real sin pruebas de aceptación suficientes.** La experiencia reportó clasificación equivocada de tesis, rechazos 429, audio ausente al reproducir YouTube, y necesidad de tocar ojos para voz; las correcciones en código no equivalen a resultado probado con pantalla bloqueada, permisos, ahorro de batería, interfaz, Spotify/YouTube y archivos grandes.
5. **Sin identidad multi-tenant ni privacidad verificable.** Los tokens de chat emparejan dispositivos bajo control del propietario; no equivalen a suscripciones comerciales aisladas por usuario/empresa. Deben añadirse cuentas, consentimiento, límites por usuario, borrado/exportación, defensa contra abuso, auditoría y pruebas de aislamiento.
6. **No hay métricas de capacidad y costo productivo.** Solo dos generaciones por proceso y un rate-limit de chat en el servidor. Los límites en memoria no se comparten entre réplicas. Hacer pruebas reales de rendimiento antes de ofrecer continuidad de servicio o anunciar miles de clientes.

### P1 — Alto impacto antes de beta amplia

- **Rigor académico y multimodalidad.** Cuellos de botella: 4.000 caracteres de la SKY Home API por turno y salida de `max_output_tokens=1200`; un prompt de tesis de 350 páginas debe ejecutarse por etapas con evidencia de fuentes y entregables DOCX comprobables. No vender una tesis completa en un turno.
- **Tokens y claves.** La API comercial necesita rotación y revocación, gestión de secretos por entorno, comprobación de CSRF/OAuth, herramientas privilegiadas separadas, cifrado de registros y auditoría externa antes de múltiples clientes.
- **Datos.** Proyecto SKY-IA Supabase tiene 6 tablas de Instagram con RLS activada **sin políticas**; el asesor lo clasifica `INFO`, normalmente adecuado para tablas internas de acceso exclusivo por service role, pero hay que verificar roles SQL efectivamente autorizados y documentar el aislamiento. No crear políticas públicas por comodidad.
- **Registro y soporte.** Faltan métricas centralizadas, alertas de seguridad, reportes de crash, trazabilidad de operaciones, límites de almacenamiento y procedimientos medidos de backup/restore y respuesta a incidentes.
- **Distribución.** Verificar Play Protect, cumplimiento de permisos Android, publicación autorizada en tienda o distribución privada explícita, página de privacidad, términos, soporte, versiones y actualizaciones reproducibles.
- **Licencias.** Comprobar la licencia comercial y redistribución de cada modelo y SDK; una API propia no significa haber entrenado un modelo base desde cero.

## Verificación de infraestructura realizada

- **SKY-IA Supabase:** proyecto existente `ACTIVE_HEALTHY`. Sin infraestructura nueva de base de datos ni cambios a Instagram.
- **`sky-platform-readiness`:** función nueva v1 desplegada en el proyecto SKY-IA; exige JWT. Fuente: `supabase/functions/sky-platform-readiness/index.ts`. Su respuesta distingue la disponibilidad del control cloud de la disponibilidad del modelo. `SKY_BACKEND_HEALTH_URL` es opcional y no se ha configurado: no hay un backend de inferencia conectado. La ejecución HTTP con JWT real no se pudo completar desde esta auditoría.
- **`sky-instagram`:** sigue en versión 18 ACTIVE, no modificada. Su endpoint puede admitir callbacks públicos; debe auditarse individualmente su verificación de firma y autorización antes de comercializar.
- **Supabase:** no hospeda un worker persistente de GPU. Edge proporciona control, auth y orquestación; compute de modelo requiere servidores dedicados.
- **GitHub:** `main` es la rama fuente; no se realizó ningún rebase destructivo, borrado de Windows, sustitución de Releases ni modificación de BAQUEANO.

## Arquitectura objetivo

`SKY Android → API Gateway HTTPS / identidad y autorización → SKY Orchestrator (local-first) → Ollama/vLLM en worker GPU dedicado`; solo si existe autorización explícita: `→ proveedor externo temporal`. Supabase SKY-IA presta control, Auth/DB/Storage y estado; Redis/cola y observabilidad resuelven admisión multiinstancia; object storage conserva archivos por tenant; Cloudflare/Caddy gestionan TLS y protección en perímetro. El puerto Ollama `:11434` debe permanecer en loopback/red privada cerrada; ninguna clave maestra se incluye en la APK.

No contratar GPU por suposición. Elegir configuración según pruebas de modelo, contexto y carga. La PC doméstica puede servir para prototipos **pero no** es infraestructura fiable de ventas masivas.

## Puertas de lanzamiento

| Puerta | Condición verificable | Estado |
|---|---|---|
| G0 — código | main coherente, tests backend/Android de versión actual sin fallos | Backend 59/59 aprobado sobre `22f6576a`; Android y release de `main` pendientes |
| G1 — seguridad | token, permisos, DLP, auth, revocación, aislamiento y secretos probados | Pendiente |
| G2 — inferencia real | 100 solicitudes al modelo propio, registradas por operación y sin API externa | No ejecutada |
| G3 — dispositivos | Android 15/16, Samsung real, manos libres, volumen YouTube, adjuntos, bloqueo y reanudación | No ejecutada |
| G4 — carga | concurrencia medida, cola, p95 y error bajo carga; definir umbrales según hardware/plan | No ejecutada |
| G5 — continuidad | 72 horas de prueba controlada, fallos/reinicio/restore y alarmas verificadas | No ejecutada |
| G6 — comercial | contratos, licencia de modelos, política de datos, soporte, control de cuota por usuario y plan | No ejecutada |
| G7 — piloto | participantes autorizados, consentimiento, métricas de éxito, cero P0 abiertos | No ejecutada |

**Recomendación de distribución:** no lanzar al público general. Prueba de laboratorio primero; luego piloto cerrado con usuarios consentidos, monitorizado y con capacidad real. Pasar a beta pública solo si G0–G7 cumplen condiciones concretas. Ni la cantidad de commits ni las estrellas en GitHub reemplazan pruebas.

## Fuentes de evidencia (enlaces directos)

- [SKY Releases](https://github.com/OscarElieser/SKY/releases) — APK firmadas publicadas
- [Backend 59 pruebas aprobadas tras corrección](https://github.com/OscarElieser/SKY/actions/runs/41156279036)
- [APK 0.8.42 firmada publicada desde commit anterior](https://github.com/OscarElieser/SKY/releases/tag/sky-android-v0.8.42)
- [GitHub Actions](https://github.com/OscarElieser/SKY/actions)
- [CI con regresiones en credenciales](https://github.com/OscarElieser/SKY/actions/runs/41155473762)
- [Issue P0 Android](https://github.com/OscarElieser/SKY/issues/97)
- [SKY Inference Gateway](https://github.com/OscarElieser/SKY/blob/main/neural_core/sky_inference_gateway.py)
- [SKY Automatic](https://github.com/OscarElieser/SKY/blob/main/neural_core/sky_smart_router.py)
- [Control cloud de SKY-IA](https://github.com/OscarElieser/SKY/blob/main/supabase/functions/sky-platform-readiness/index.ts)
- [Supabase Edge Function limits](https://supabase.com/docs/guides/functions/limits)
- [Plan comercial de SKY](https://github.com/OscarElieser/SKY/blob/main/docs/SKY_API_COMERCIAL_INFERENCIA_2026.md)

**Condición de reauditoría:** medir datos reales y revisar nuevamente antes de toda recomendación comercial. Las notas de software de terceros y los avisos de GitHub no prueban ejecución en el dispositivo ni respuesta audible.
