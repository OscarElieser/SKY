# SKY IA — conectores externos opcionales de la API propia

**Fecha:** 30 de octubre de 2026. **Estado:** código de adaptadores y pruebas agregado a `main`. Sin tokens reales vinculados ni servicios externos certificados desde este chat. No es una promesa de gratuidad, disponibilidad continua o uso ilimitado.

## Arquitectura y prioridad

`SKY Android → SKY API HTTPS → autenticación de chat por dispositivo → proveedor seleccionado`.

1. **Principal:** Ollama en la infraestructura controlada por SKY, sin cuotas de Gemini/Groq. Sigue limitado por potencia de cálculo, latencia, RAM/VRAM, red, seguridad y energía.
2. **Opcionales:** Gemini (por la integración previa de SKY), OpenRouter, Mistral, Groq y Cloudflare Workers AI. Todos se pueden seleccionar a través del **backend SKY**. Solo los cuatro últimos comparten el nuevo adaptador OpenAI-compatible; no se modificó el motor Windows.
3. El propietario debe activar «Priorizar mi SKY API privada» y seleccionar un proveedor desde «MOTOR SKY API · ELEGIR MODELO». El predeterminado es **Ollama**. Cada consulta externa requiere el permiso explícito de **Nube** y **Datos privados** en la pantalla; las fuentes de actualidad siguen necesitando herramientas de verificación y no se presentan como verificadas por el LLM.
4. Si falla un proveedor, **no** hay cambio oculto a otro ni reintento automático; el borrador permanece disponible. Un error HTTP 429 significa cuota agotada o límite temporal y no se debe intentar evitarlo creando solicitudes repetidas.

## Configuración únicamente del servidor (nunca agregar valores reales a GitHub)

| Proveedor | Variables del servidor | Modelo inicial de referencia | Endpoint fijo |
|---|---|---|---|
| Gemini (ruta ya existente) | `GEMINI_API_KEY`, `GEMINI_MODEL` | modelo configurado por el servidor | adaptador Gemini anterior de SKY; no nuevo endpoint implementado |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | `openrouter/free` | `https://openrouter.ai/api/v1/chat/completions` |
| Mistral | `MISTRAL_API_KEY`, `MISTRAL_MODEL` | `mistral-small-latest` | `https://api.mistral.ai/v1/chat/completions` |
| Groq | `GROQ_API_KEY`, `GROQ_MODEL` | `openai/gpt-oss-20b` | `https://api.groq.com/openai/v1/chat/completions` |
| Cloudflare Workers AI | `SKY_WORKERS_AI_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_MODEL` | `@cf/meta/llama-3.1-8b-instruct` | `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions` |

`SKY_WORKERS_AI_TOKEN` debe ser un token **dedicado** a Workers AI, de alcance mínimo. No reutilizar tokens generales de Cloudflare usados para DNS, zonas, seguridad o infraestructura. La cuenta Cloudflare debe disponer de acceso adecuado a Workers AI. No conectar el navegador o las cuentas personales de los clientes directamente con el token de SKY.

En OpenRouter, `SKY_OPENROUTER_FREE_ONLY=1` está activo por defecto. Solo admite `openrouter/free` o modelos cuyo identificador termine en `:free`. No adjuntar modelos de pago como respaldo sin aprobación comercial explícita; los modelos gratuitos tienen cuotas y disponibilidad variables. La opción `SKY_OPENROUTER_FREE_ONLY=0` es de configuración **del propietario del servidor** y puede generar costos.

Los modelos Mistral, Groq y Cloudflare deben comprobarse contra el catálogo y términos de sus cuentas antes de considerarlos aptos para un uso comercial; un endpoint compatible con OpenAI **no implica** modelo universal, cuota gratuita permanente ni equivalencia de calidad.

## Controles integrados

- Lista fija de nombres y endpoints. No se aceptan URLs de proveedor ni identificadores de cuenta entregados en prompts.
- HTTPS, encabezados Bearer construidos en servidor y **redirecciones bloqueadas** para evitar fuga de claves.
- Salida de texto, sin acceso a herramientas, datos del dispositivo, historial privado fuera del permiso solicitado ni control Android.
- Entrada de 4.000 caracteres por turno al API de chat actual; máximo 10 mensajes y 2.048 tokens solicitados por respuesta del adaptador; sin recortar en secreto.
- Respuestas y errores limitados en tamaño; no registrar prompts, API keys ni cuerpos de errores crudos.
- Códigos de cuota 429 reportados expresamente. Nunca cambiar silenciosamente a un modelo gratuito o de pago.
- Los tokens de chat móviles permanecen separados de los permisos del propietario; las operaciones de control del dispositivo no están autorizadas por este endpoint.
- Servidor propio: sigue usando protección de 12 solicitudes por minuto por sesión móvil. Esto no sustituye las cuotas globales, facturación ni el aislamiento por empresa pendientes de la comercialización.

## Verificación

- `tests/test_sky_optional_cloud_providers.py` prueba formas HTTP compatibles mediante respuestas locales simuladas sin gastar cuotas.
- `tests/test_sky_optional_provider_routing.py` prueba consentimiento de nube y datos privados, manejo de límites y que no cambia de proveedor.
- `tests/test_sky_home_routing.py` comprueba que el modo local obligatorio bloquea la nube.
- `SkyOwnApiRoutingPolicyTest.kt` prueba que Android selecciona Ollama por defecto y no utiliza conectores sin autorizaciones.
- GitHub Actions: `SKY Mobile Android Agent` ejecuta el backend y pruebas Android. Los resultados se verifican en [Actions](https://github.com/OscarElieser/SKY/actions); una prueba simulada no acredita clave, saldo, modelo real ni funcionamiento en Samsung.

## Requisitos previos a vender SKY

Primero probar Ollama auténtico con `python scripts/verify_sky_local_inference.py` en un servidor privado; luego probar los conectores autorizados con **claves de pruebas y datos no sensibles**, y finalmente ejecutar pruebas de carga por usuario y por empresa. No comenzar comercialización masiva hasta incorporar cuentas comerciales, aislamiento multiusuario, cuotas/tokens por plan, facturación, licencias de modelos, privacidad, observabilidad y evidencia de rendimiento.

Documentación oficial: [Gemini](https://ai.google.dev/gemini-api/docs), [Groq](https://console.groq.com/docs/api-reference), [OpenRouter](https://openrouter.ai/docs/quickstart), [Mistral](https://docs.mistral.ai/api), [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/).
