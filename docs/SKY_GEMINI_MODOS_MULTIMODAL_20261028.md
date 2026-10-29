# SKY Android — modos Gemini y capacidades multimodales (28/10/2026)

## Auditoría de capacidad existente (sin sustitución del núcleo)

En `main` ya existen: `neural_core/providers.py` (pasarela de proveedores), `neural_core/gemini_provider.py` (SDK de Gemini en Windows), `neural_core/sky_cognition.py` (clasificación y plan), `neural_core/sky_neural_memory.py` (memoria), y, en Android, `SkyPhoneCloud.kt`, `SkyGeminiFiles.kt`, `SkyAttachmentBatch.kt` y `SkyOfficeStreaming.kt`. Esto NO significa que SKY haya entrenado Transformers ni posea TPU propias. SKY delega razonamiento multimodal en modelos autorizados por el usuario.

## Nueva integración aditiva para Android

Se incorpora `SkyGeminiModes.kt` y selección **expresa por cada consulta**, sin cambiar el modelo de otras conversaciones:

| Comando en SKY | Modelo de API | Propósito |
| --- | --- | --- |
| Consulta habitual (sin prefijo), o `Modo económico: ...` | `gemini-3.5-flash-lite` | Conserva el comportamiento económico habitual |
| `Modo flash: ...` o `Modo equilibrado: ...` | `gemini-3.8-flash` | Consultas de mayor complejidad |
| `Modo profundo: ...` o `Razonamiento profundo: ...` | `gemini-3.1-pro-preview` | Análisis extenso que el propietario elige explícitamente |

Se admite anteponer `SKY,` a estos comandos. El prefijo se retira de la pregunta enviada al modelo, pero no de la conversación mostrada o archivada en el teléfono. La selección es por consulta y no queda activada para siempre. **No hay cambio automático a un proveedor, modelo ni tarifa diferente después de un fallo.**

El chat económico conserva 8 entradas recientes del historial y el mismo límite de respuestas; el modo flash admite 14 y el profundo 30 entradas recientes, con mayores presupuestos de texto por entrada y salida. No significa que todo el historial acumulado esté dentro del contexto: siguen existiendo límites de la aplicación, del proveedor, de cuotas y de tokens. Los modelos profundos requieren acceso y cuota apropiados; el modelo Pro es preliminar y puede cambiar o dejar de estar disponible. Los errores de red, permiso o cuota deben notificarse, no presentarse como análisis exitosos.

El comando de modo también se aplica a **análisis conjunto de archivos** mediante `SkyGeminiFiles.analyze` y `SkyPhoneCloud.analyzeFileReferences`, conservando sus cargas por bloques, límites de 100 MiB por archivo, PDF máximo 50 MiB, máximo 5 archivos y consentimiento antes de subir. La subida no autoriza a procesar archivos privados sin una acción explícita. No se habilita entrenamiento automático de pesos ni navegación sin supervisión.

## Límites de arquitectura y seguridad

1. La multimodalidad nativa es una propiedad del modelo Gemini remoto: la aplicación SKY combina archivos y texto para enviarlos a la API, no entrena desde cero un Transformer multimodal propio.
2. Las TPU y los clústeres de entrenamiento son infraestructura del proveedor, no recursos nuevos instalados en el teléfono o en Windows.
3. Mantener la distinción entre **memoria consultable**, **contexto temporal** y **entrenamiento**. Guardar consultas no modifica los pesos del modelo.
4. Las acciones Android se realizan mediante servicios/herramientas con permisos y verificación local, no porque Gemini afirme haberlas ejecutado.
5. Las claves de usuario no deben aparecer en el repositorio, mensajes de error ni logs. Las consultas remotas y archivos pueden salir del dispositivo después del consentimiento.
6. No prometer acceso gratis ilimitado: Gemini aplica cuotas, precios y restricciones de modelo.
7. Se respetan la voz, la interfaz animada, el historial por consulta, la compatibilidad con Android sin Windows y el resto de funciones existentes.

## Validación

- `SkyGeminiModesTest.kt`: modos explícitos, economía predeterminada, contexto y URLs permitidas.
- `SkyPhoneCloudTest.kt`: claves, límites de salida, cambios que exigen fuentes y compatibilidad.
- CI: `SKY Mobile Android Agent` y `SKY Android Signed Release Candidate`; deben aprobar antes de afirmar que existe una APK instalable de esta versión.
- El funcionamiento real de micrófono, lectura de archivos, respuesta remota, apertura de apps y bloqueo de pantalla requiere pruebas en un dispositivo Android. Pasar CI no las sustituye.

Documentación oficial: https://ai.google.dev/gemini-api/docs/models · https://ai.google.dev/gemini-api/docs/files · https://ai.google.dev/gemini-api/docs/video-understanding
