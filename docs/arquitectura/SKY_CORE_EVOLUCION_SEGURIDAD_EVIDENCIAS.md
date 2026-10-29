# SKY CORE — Arquitectura evolutiva, seguridad por capas y pruebas (2026-10-28)

**Rama oficial:** main · **Estado:** componentes incrementales funcionales en código; dispositivos y capacidad a gran escala pendientes de pruebas.
**Principio:** no borrar lo construido; mejorar con regresiones verificadas, cambios reversibles y evidencias de cada ejecución relevante.

## 1. Arquitectura actual y objetivo

```text
Android SKY            Windows/HUD               Integraciones externas
    |                      |                             |
    +------- acceso autenticado a API SKY ----------------+
                               |
                   FastAPI /api/sky/...
                               |
                   Identidad + límites + MFA*
                               |
               Núcleo cognitivo y planificación
                   /api/sky/cognition
                     |        |        |
                memoria   estrategia   investigación
                cifrada   adaptativa   con fuentes
                     \       |        /
                     SKY agentes especializados
                               |
                    Política y permisos de acción
                               |
                     Ejecutor de dispositivo
                               |
                    Resultado y evidencia
                               |
                   Métricas y mejora propuesta
```

`* MFA` y autenticación efectiva dependen del despliegue y del punto de entrada. La API de cognición reutiliza la dependencia existente `require_key`. No se deben publicar secretos en APK, README, logs ni repositorios.

**Módulos reales:**
- `neural_core/sky_cognition.py`: clasificación, planificación sin ejecución, fuentes bajo consentimiento y estilo de respuestas.
- `neural_core/sky_neural_memory.py`: memoria personal cifrada y resultados operacionales; exige propietario, clave Fernet y confirmación.
- `neural_core/sky_adaptive_policy.py`: **motor nativo** de estadística adaptativa, sin inferencia por proveedor ni llamadas a la nube. Calcula límite inferior de confianza de Wilson sobre resultados disponibles y aconseja revisar fallos.
- `metaverse/sky_cognition_api.py`: API propia de SKY con control de acceso existente.
- `neural_core/sky_tiny_transformer.py`: Transformer educativo opt-in que modifica pesos solo mediante entrenamiento explícito con dataset autorizado; **no reemplaza el modelo de chat de Android/Windows**.

### API propia: nuevos endpoints

Estos endpoints requieren la autenticación de SKY existente. No deben exponerse directamente a internet sin TLS, rate limiting en el reverse proxy, supervisión y límites de sesión.

| Método | Ruta | Resultado real |
|---|---|---|
| GET | `/api/sky/cognition/native-evolution` | Historial agregado por rol y estado del motor independiente |
| POST | `/api/sky/cognition/adaptive-plan` | Plan explicable y fiabilidad estadística, sin ejecutar herramientas |

Ejemplo de solicitud autenticada a la API local:

```json
{"query":"Investiga fuentes académicas sobre formación técnica","device":"android"}
```

**Importante:** una llamada a `adaptive-plan` nunca abre una aplicación ni modifica permisos. El motor consume contadores previos; por sí solo no entrena pesos ni navega en internet. El proceso de registro de resultados debe demostrar procedencia: un booleano aportado por un proceso interno NO constituye atestación criptográfica.

### Qué significa que SKY aprenda

1. **Aprendizaje estadístico ya integrado:** lee las ejecuciones registradas, observa aciertos y fallos por rol, actualiza su asesoría al recibir nuevas evidencias; sin almacenar la consulta del usuario.
2. **Memoria persistente:** hechos personales cifrados únicamente con autorización; contenido recuperable y eliminable.
3. **Conocimiento incremental:** registros de fuentes públicas etiquetadas como no confiables hasta contrastarlas; no ejecutar instrucciones contenidas en documentos.
4. **Entrenamiento de pesos:** experimental y opt-in; falta evaluación rigurosa, datasets autorizados, infraestructura y aislamiento para producción. Sin estos requisitos NO afirmar que un LLM de SKY se ha entrenado o que es equivalente a ChatGPT, Gemini o Claude.

## 2. Defensa en profundidad

| Capa | Regla obligatoria | Evidencia/pendiente |
|---|---|---|
| 1. Identidad | Propietario autenticado; MFA según servicio; dispositivo independiente y revocable | Validar sesiones en Android y API |
| 2. Entrada | Límite de tamaño, origen, tipos de datos y aislamiento de contenidos no confiables | Pruebas negativas y fuzzing |
| 3. Contexto y memoria | Minimización, cifrado, consentimiento, revocación; nunca divulgar tokens | Revisar cifrado y accesos por usuario |
| 4. Política cognitiva | Recomendaciones **sin** permisos implícitos ni autoejecución | `test_sky_adaptive_policy.py` |
| 5. Acciones | Mínimo privilegio, aprobación supervisada, control del origen e idempotencia | Pruebas Android + acciones de alto riesgo |
| 6. Verificación | Diferenciar solicitado, despachado, confirmado y fallido; no inferir ejecución de textos de IA | Estandarizar recibos de ejecutor |
| 7. Entrega | Código versionado, CI, firmas/hash, registros de errores, rollback | Workflows y pruebas en hardware |

Referencias de diseño: [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/) — inyección de instrucciones, exceso de agencia, envenenamiento, información privada y consumo descontrolado; [NIST AI RMF Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1). Estas referencias orientan los controles; no equivalen a una auditoría de conformidad.

La autorización de "control total supervisado" del usuario NO equivale a desactivar las reglas del sistema operativo, la política de plataformas ni las defensas de SKY. Operaciones destructivas o externas requieren confirmación contextual y prueba de resultado.

## 3. Evidencias de compilación y trazabilidad

`.github/workflows/sky-native-core-evidence.yml` se ejecuta ante cada cambio en `main` (y manualmente). Su alcance es el **núcleo adaptativo**, no toda la app. Registra:
- Commit/ref y enlace exacto de GitHub Actions.
- Hash SHA-256 de cuatro archivos de código y pruebas.
- Resultado de `py_compile`, número de tests y estado final.
- Artefactos `sky-native-evidence.json` + su SHA-256, subidos al run con retención de 90 días.
- Falla el job si falla una comprobación; nunca convierte un error en "aprobado".

**No guarda** conversaciones, claves, variables de entorno ni logs de usuario en el artefacto. Los artefactos de GitHub Actions son **temporales**: para conservación permanente, conservar una copia controlada del manifiesto y el registro de releases en almacenamiento con retención definida. Las APK firmadas siguen el workflow separado `sky-mobile-release.yml`; exigir SHA-256, firma y pruebas reales en Samsung antes de declarar cada release validada en dispositivo. Un workflow "verde" no prueba escalabilidad ni una API de Meta funcional.

Ejecutar localmente sin acceder a servicios externos:

```sh
python -m py_compile neural_core/sky_adaptive_policy.py neural_core/sky_cognition.py metaverse/sky_cognition_api.py
python -m unittest discover -s tests -p 'test_sky_adaptive_policy.py' -v
```

## 4. Medición de calidad y capacidad

**Objetivos por validar** (NO son resultados obtenidos):

| Dimensión | Indicador | Criterio de entrada a producción |
|---|---|---|
| Fiabilidad | % tareas terminadas y verificadas | Baseline reproducible por tipo de tarea; cero falsos éxitos |
| Seguridad | Pruebas de inyección, permisos, recuperación | Ninguna escalada de permisos en pruebas negativas |
| Latencia | p50/p95 por dispositivo y tipo de consulta | Umbrales definidos y medidos en Android/Windows |
| Escala | usuarios simultáneos, solicitudes/seg, p95, errores | Carga gradual desde 10 hasta 100 000; no afirmar soporte sin ensayos |
| Aprendizaje | mejora real sobre conjunto de evaluación independiente | Comparar baseline vs nuevo modelo y conservar evidencia |
| Sostenibilidad | CPU/RAM, energía, coste/inferencia | Límite de recursos medido y alertas activas |

## 5. Siguiente secuencia técnica

1. Verificar CI del motor nativo y pruebas; conservar manifests reales.
2. Registrar resultados de ejecución desde ejecutores autenticados, no desde texto del modelo.
3. Incorporar evaluación adversarial y aislamiento del conocimiento externo.
4. Medir latencia y fiabilidad con datos de pruebas reproducibles; optimizar la API propia.
5. Integrar un modelo generativo local de SKY solo tras pruebas de calidad, seguridad y compatibilidad; mantener proveedores opcionales como respaldo.
6. Pruebas de carga y fallos progresivas; probar Android físicamente y confirmar accesibilidad/permisos.
7. Mantener README, esquema de arquitectura y tabla de funcionalidades sincronizados con los commits y releases.

**Estado de esta entrega:** desarrollo incremental del motor nativo y del sistema de evidencia. No se ha demostrado aún entrenamiento autónomo continuo, 100 000 usuarios simultáneos, ni equivalencia de calidad con servicios comerciales.
