# SKY Android · IA integral y modo de conversación local

**Objetivo final del producto:** SKY no se limita a abrir aplicaciones. Debe evolucionar hacia un sistema multimodal de conversación y trabajo (razonamiento, programación, investigación documentada, documentos, análisis de archivos, voz y acciones supervisadas), usando un motor propio y conectores de otros modelos según disponibilidad y decisión del usuario.

## Implementado en esta rama

- Nuevo interruptor **«CONVERSACIÓN SOLO LOCAL»**. Se conserva apagado por defecto para no alterar el comportamiento del usuario anterior.
- Al habilitarlo, los comandos del teléfono, voz, cálculos, memoria guardada, planes locales y respuestas conocidas siguen disponibles. Las peticiones de chat generativo sin solución local se conservan como borrador y no se transmiten por la ruta de IA remota.
- Las solicitudes de noticias, investigación, clima o generación de textos por proveedor externo se detienen antes de contactar servicios de IA desde la ruta de conversación.
- El flujo de voz no intenta crear textos externos ni consultar Instagram y permite enviar consultas generales al mismo control sin nube.
- Ajustes → **DIAGNÓSTICO REAL · MOTORES DE IA**, con información honesta de qué se configuró y qué sigue pendiente.
- No se elimina la API privada ni la configuración HTTPS: simplemente deja de ser necesaria **para los comandos y respuestas locales de conversación**.
- Código propio Android, sin permisos Android nuevos ni cambios en SKY Windows o BAQUEANO.

## Diferencia fundamental

**Local en Android:** ejecución en el mismo teléfono, sin solicitudes HTTP/HTTPS para la conversación. La APK no contiene pesos de un LLM (modelo generativo). Por tanto, el modo local actual todavía NO puede producir conversaciones tan complejas como ChatGPT, Claude o Grok sin un motor añadido.

**SKY API con Ollama propio:** el modelo se ejecuta en un servidor administrado por el usuario. Para conectarlo por Internet, se exige TLS/HTTPS. No es inferencia dentro del teléfono.

**Gemini/Groq (actualmente presentes):** modelos externos sujetos a conexión cifrada, cuotas, claves y autorización. Su integración no implica acceso a sus aplicaciones, datos privados ni funciones exclusivas.

**Claude/Grok:** no hay todavía adaptadores móviles verificados. No deben aparecer como funcionales en la interfaz. Integrarlos en el futuro requerirá API pública oficial o backend autorizado, claves en servidor y pruebas de cuotas, errores y privacidad.

## Criterios previos al primer LLM completo EN EL TELÉFONO

1. Evaluar runtime oficial `llama.cpp/examples/llama.android` o un proveedor Android aprobado (p. ej., ML Kit GenAI sobre AICore, sujeto a disponibilidad por dispositivo).
2. Descargar/cargar pesos GGUF con licencia compatible **en almacenamiento privado**, checksum SHA-256, límites de RAM y almacenamiento, y cancelación. No incluir arbitrariamente modelos grandes en una APK ni abrir un puerto accesible a la red local.
3. Medir primera respuesta, tokens/segundo, RAM, batería, temperatura, suspensión y recuperación en Samsung real. Un modelo de 0,5–1,5B cuantizado puede ser un candidato de prueba, pero rendimiento y calidad requieren evidencia.
4. Implementar chats con streaming de tokens, contexto y privacidad local, elección explícita de proveedor, informes de evidencia y recuperación de errores. Ningún texto privado se envía a terceros sin autorización.
5. Mantener un ejecutor de herramientas separado del modelo: los prompts, documentos o resultados web no tienen permisos de dispositivo. Acciones sensibles requieren aprobación humana.
6. Crear tests instrumentados Android 15 y 16, compilación release firmada con la clave existente, verificación de Play Protect y actualización sin pérdida de historial.

## Sobre «sin restricciones»

El objetivo es una SKY flexible y capaz; ningún sistema puede garantizar acciones ilimitadas, saltarse permisos de Android, acceder sin autorización a servicios ajenos, eludir cuotas o garantizar exactitud infalible. Se preservan consentimientos, cifrado de la red externa y controles del dispositivo.

**Estado:** esta rama introduce una separación de conversación local/remota y diagnóstico transparente, **no un modelo de lenguaje completo ni una APK certificada**.
