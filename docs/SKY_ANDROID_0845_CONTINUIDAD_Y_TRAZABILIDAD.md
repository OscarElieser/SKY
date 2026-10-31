# SKY Android 0.8.45 — integridad del contexto y trazabilidad

Estado: mejoras de código sujetas a CI, emulador y pruebas Samsung. No afirmamos Ollama productivo sin comprobar generación real, ni funcionamiento certificado por Google Play Protect.

## Defecto crítico encontrado en 0.8.44

El chat Android guardaba las respuestas completas hasta 100.000 caracteres en SQLite, pero enviaba respuestas de conversación recortadas de forma silenciosa a 5.000 caracteres. Además, el esquema servidor heredado de `HomeChat` solo aceptaba ocho turnos de **2.000 caracteres**, mientras el gateway de inferencia privada admitía 4.000 por turno. Una investigación extensa seguida de «continuá el capítulo» podía fallar con **HTTP 422** aun cuando la primera respuesta se hubiera generado correctamente.

## Corrección implementada

- `SkyPrivateHistoryPolicy`: cada sesión envía **como máximo ocho turnos** anteriores; el chat local propio acepta hasta **4.000 caracteres por turno** y el adaptador de proveedores externos sigue limitado a **2.000**. Los extractos conservan inicio y final e incluyen una advertencia explícita. No se presenta un extracto como texto completo.
- `MobileChatRequest`: define un contrato propio para contexto Ollama hasta ocho turnos de 4K. La ruta externa revalida el contrato antiguo de `HomeChat`, evitando transferir 4K de contexto privado a proveedores no autorizados.
- `MainActivity`: los turnos temporales de sesión usan extractos marcados en lugar de `take(5000)` silencioso. La pregunta y respuesta originales siguen en `SkyConversationArchive` sin migraciones ni borrados.
- `SkyNetwork` limita cada respuesta de chat por bytes a **512.000**; el canal de control continúa en 16.384. Superar el presupuesto cancela la lectura sin mostrar JSON parcial.
- `sky_inference_gateway`: presupuesto de respuesta HTTP de Ollama de 512.000 bytes y payload de solicitud hasta 400.000 bytes; los límites del modelo (48K caracteres por petición, 6.144 tokens de respuesta, contexto condicionado a 65.536 tokens) permanecen intactos. Más bytes de transporte no significan más capacidad de modelo.
- El identificador `operacion` se añade al metadato visible del chat únicamente si tiene 32 caracteres hexadecimales válidos, para ayudar a correlacionar consultas sin registrar el texto privado.

## Pruebas de aceptación

- Python: contrato privado de 8 turnos x 4K, aislamiento de nube 2K, respuestas extensas Unicode, rechazo de respuestas excesivas.
- Kotlin: política de historial, conservación de los dos extremos del contexto, límite de ocho turnos, ausencia de roles de sistema inyectados, identificación de operación confiable, transporte Unicode y tamaño máximo.
- Pruebas instrumentadas API 35 y API 36, compilación estándar y firma real.
- Samsung físico: repetir dos capítulos académicos largos; revisar historial completo antes y después del reinicio, exportación de Markdown/DOCX y avisos de continuidad; verificar audio, voz y archivos. **No** certificar si faltan estas evidencias.
- Verificación de Ollama real en servidor propietario mediante `python scripts/verify_sky_local_inference.py --maximal-academic` (requiere `SKY_INFERENCE_NUM_CTX=65536`, modelo instalado y capacidad medida). Los mocks de CI no acreditan generación de IA real.

No se toca SKY Windows, BAQUEANO, certificados, permisos de instalación ni credenciales. Este bloque corrige integridad de conversaciones antes de ampliar aún más tokens o publicitar escalabilidad comercial. La compatibilidad de la versión anterior se conserva bajo el mismo identificador Android y migraciones SQLite.
