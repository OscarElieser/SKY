# SKY Android 0.8.47 — estados temporales, respuesta completa y exportación exacta

**Alcance:** actualización complementaria a la 0.8.46 ya integrada mediante PR #102. No reescribe el compositor, su botón para limpiar borradores ni la vista responsive de mensajes.

## Problemas que permanecían en 0.8.46

1. `pendingInfo` se mantenía como burbuja ordinaria incluso después de cerrar y reabrir el panel. El redibujado lo volvía a mostrar aunque el usuario hubiera terminado de leer el aviso.
2. `renderConversation()` desplazaba siempre la conversación al final. Al inspeccionar una respuesta anterior, cualquier aviso podía moverla y arruinar la lectura.
3. Las respuestas largas se abrían en un cuadro de aproximadamente dos tercios de la pantalla; faltaba una lectura inmersiva clara para fórmulas y tablas.
4. Si SQLite fallaba tras una respuesta correcta, `archive.append` podía lanzar una excepción durante el renderizado, dejando la respuesta invisible o el estado de espera atascado.
5. La exportación Word usaba la última entrada de SQLite en vez de la consulta recién generada. Si una respuesta fallaba al guardarse, era posible iniciar la exportación de una conversación previa.
6. La cara animada podía permanecer en estado de ERROR indefinidamente después de errores temporales.

## Correcciones

- Aviso temporal como tarjeta independiente, descartable con `×` y con expiración de ocho segundos, renovando su identidad por versión; se elimina al comenzar otro mensaje o cerrar la conversación. El cierre redibuja realmente la pantalla. Se conserva el borrador si falla la petición y no se borra historia SQLite.
- Solo se hace *auto-scroll* al comienzo o fin del mensaje, o al abrir el panel por primera vez; los avisos ya no fuerzan desplazamientos si se están leyendo respuestas antiguas.
- La lectura completa usa `SkyScientificMarkup` en WebView **sin JavaScript, archivos ni red**, dentro de un diálogo que ocupa el 94 % de la altura, con botones de copiar todo y cerrar. Las respuestas estructuradas también pueden abrir este visor cuando son cortas; se conserva el renderizado matemático inline ya implementado por 0.8.46.
- Si SQLite no puede persistir un intercambio, se muestra la respuesta en la sesión y se comunica que **no** quedó guardada. No se finge memoria exitosa.
- Word exporta exclusivamente la entrada que se guardó para el turno actual. Si esa escritura falla, se muestra el error y no se selecciona una conversación anterior.
- Los errores temporales de estado facial se restablecen a IDLE a los ocho segundos si no está activo el micrófono ni la voz.
- Paquete Android `versionName=0.8.47`, `versionCode=60`. Mismo identificador de app y sistema de firma que la distribución oficial.

## Criterios de aceptación

Pruebas backend y Kotlin, regresiones de voz/seguridad, APK estándar firmada y auditada, emuladores API 35/36. Pruebas físicas en Samsung Android 16 de lectura y cierre de avisos, teclado, respuestas extensas, exportación Word, reabrir conversación, Play Protect, micrófono y archivos. Las pruebas virtualizadas **no** certifican experiencia visual real ni ausencia de bloqueos Play Protect.

No modificar SKY Windows, BAQUEANO, API, credenciales, permisos ni historial anterior. Integrar a `main` solo tras CI. No declarar verificado Ollama real por validar el renderizado de chat.