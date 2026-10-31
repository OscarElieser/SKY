# SKY Automático — IA propia como motor principal

**Estado:** nueva ruta de código integrada en `main` el 30 de octubre de 2026. No implica despliegue productivo, inferencia comprobada en un GPU real, APK instalada ni capacidad demostrada para miles de usuarios.

## Objetivo

El usuario habla con **SKY**, no elige Gemini, Groq u OpenRouter para cada mensaje. SKY debe conservar la identidad, el historial y la interfaz. El modelo escogido queda indicado como procedencia técnica de cada respuesta. **El control de SKY API es propio; los pesos de Ollama aún provienen de modelos abiertos con sus respectivas licencias.**

## Comportamiento exacto de `sky_auto`

1. El chat móvil autentica por `X-SKY-CHAT-TOKEN` y un dispositivo emparejado. Las rutas anteriores `auto`, `ollama` y manuales no cambian; no se modifica SKY Windows.
2. `neural_core/sky_smart_router.py` intenta generar primero con `sky_inference_gateway.generate`, vía Ollama privado en loopback y recursos propios.
3. Si Ollama está sobrecargado o no disponible, el servidor **no** envía nada a un tercero por defecto.
4. Solo cuando **ambas autorizaciones** están presentes (cliente autorizó nube y datos privados para este envío o concedió consentimiento persistente informado) **y** el operador del servidor configuró respaldo, SKY elige automáticamente el primer proveedor configurado y sin suspensión temporal.
5. Se permiten como máximo **dos intentos externos distintos** por consulta; agotamiento HTTP 429 activa un enfriamiento en memoria y evita seguir insistiendo. Nunca se fuerza un modelo de pago ni se invocan enlaces o herramientas desde una respuesta de texto.
6. Si ningún motor puede responder, se devuelve un error veraz y el borrador de SKY Android permanece disponible. No se fabrica contenido y no se declara completada una operación.

## Configuración del operador — servidor, no APK

`SKY_AUTO_CLOUD_ORDER` es una lista de prioridad de proveedores **aprobados y configurados expresamente**. Vacía por defecto para impedir tráfico externo accidental.

Ejemplo, **solo cuando ya existan claves válidas y permiso operativo**:

```dotenv
SKY_INFERENCE_MODEL=llama3.2
SKY_INFERENCE_WORKERS=http://127.0.0.1:11434
SKY_AUTO_CLOUD_ORDER=groq,openrouter,mistral
SKY_OPENROUTER_FREE_ONLY=1
```

No incorporar claves reales ni credenciales de proveedores a este archivo, al README, al APK o a Git. La lista de respaldo admitida es `groq`, `openrouter`, `mistral`, `cloudflare` y `gemini`. Configurar las claves y modelos en un gestor seguro del servidor. La sola presencia de una clave **no** autoriza gastos ni transferencias de texto. Si no hay cuota, crédito o modelo disponible, devolver error.

**Privacidad:** La autorización persistente de respaldo externo está **desactivada por defecto**. Al activarla en Ajustes, SKY advierte que el texto y contexto, incluidos posibles datos personales, podrán ser enviados al proveedor usado en el respaldo. El consentimiento se puede revocar sin alterar el historial ni las credenciales de emparejamiento. La app mantiene las opciones de consentimiento por turno. Se requiere una futura clasificación de datos y controles multiusuario más granulares antes de comercializar.

**Verificación de fuentes:** solicitudes de actualidad o investigación que requieren citas verificables no se deben tratar como información real obtenida por un modelo offline. El motor de búsqueda con fuentes verificadas es una ruta distinta y requiere la autorización correspondiente.

## Diferenciadores de SKY a desarrollar

- Evaluación propia de calidad: tareas de educación técnica, programación, ciencias, explicaciones multietapa, citas y verificación de resultados.
- Memoria persistente cifrada y aislada por usuario, sin reenviar todo el historial innecesariamente.
- Observabilidad multiusuario: presupuesto por plan, latencia p50/p95/p99, tokens por usuario, tasa de error, saturación, costo por solicitud, resultado de fallbacks.
- GPU workers reales y colas con admisión distribuida, circuit breakers compartidos, autoscaling solo tras pruebas reales, seguridad y licencias de pesos abiertos.
- Inferencia nativa en Android solo tras validación de runtime y de un modelo descargado con hash y licencia.

## Pruebas y criterios de aceptación

`tests/test_sky_smart_router.py`: local primero, secreto/consentimiento, límites de intentos, cuota, modo solo local, lista aprobada del operador y validación de mensajes.

`tests/test_sky_smart_mobile_api.py`: emparejamiento real, aislamiento de token, revocación y transmisión de permisos hasta el router.

`SkyOwnApiRoutingPolicyTest.kt`: SKY Automático por defecto, proveedores manuales conservados, consentimiento global/per-turno, no confundir `sky_auto` con un proveedor externo manual.

`.github/workflows/sky-mobile-agent.yml`: pruebas Python y compilación Android.

Falta verificar resultados satisfactores de esas pruebas, compilar APK firmada, comprobar Android API 35/36, la escucha de voz y ejecutar una **generación real con Ollama** en el servidor. La plataforma todavía no está lista para ofrecer a muchos clientes. 

[GitHub Actions](https://github.com/OscarElieser/SKY/actions) · [Releases Android](https://github.com/OscarElieser/SKY/releases) · [Infraestructura comercial](SKY_API_COMERCIAL_INFERENCIA_2026.md).
