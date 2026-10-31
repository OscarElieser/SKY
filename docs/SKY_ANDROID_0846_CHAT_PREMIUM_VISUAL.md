# SKY Android 0.8.46 — chat premium, lectura completa y borrador controlado

## Defecto reproducido por captura

La conversación nativa SKY Android imponía `dp(56)` de altura a **todos los mensajes de SKY**, incluidos avisos de autorización HTTPS y respuestas académicas de varias líneas. Los mensajes con salto de línea abrían siempre un `WebView` aunque fueran texto simple, cuyo contenido HTML terminaba recortado. El compositor era demasiado grande y, cuando una operación no estaba autorizada, el borrador se conservaba sin un mecanismo visible para descartarlo.

**El código Android está implementado en vistas nativas `ScrollView`, `TextView` y `WebView`, no en Jetpack Compose.** La corrección se realizó sobre la interfaz real, sin agregar otra estructura de UI incompatible.

## Correcciones

- **Globos:** `SkyChatPresentationPolicy` decide vista nativa para texto plano, incluidos múltiples párrafos; un `TextView` ahora se mide con `WRAP_CONTENT`, interlineado 1,07 y margen interior. Se elimina la altura rígida de 56dp.
- **Ciencia y programación:** conservar renderizador `SkyScientificMarkup` sin JS, almacenamiento ni red. Solo las respuestas con formato matemático/Markdown estructurado usan `WebView`; inician con 148dp y se redimensionan conforme a `contentHeight`, con controles de lectura completa.
- **Documentos muy extensos:** a partir de 9.000 caracteres se muestra una vista previa **identificada**; el botón `Leer mensaje completo` abre todo el texto original en un visor local desplazable. No se modifica, elimina ni recorta el contenido de SQLite.
- **Borrador:** el campo acepta 1–4 líneas visibles, permite desplazamiento interno y se acompaña de una `×` para borrarlo. Si la API todavía no está autorizada, SKY **no borra la orden sin enviarla**; conserva el borrador para reintentar y permite descartarlo explícitamente. Al iniciar un envío real se limpia el campo y se cierra el teclado; un fallo permite recuperar la consulta.
- **Nuevo chat:** limpia vista, avisos y borrador, vuelve al inicio y cierra teclado; el historial privado se conserva. Si hay una operación activa, la lógica original protege contra mezclar resultados entre sesiones.
- **Jerarquía:** barra superior y botones compactos, más contraste, campo inferior más ligero, áreas de desplazamiento y navegación accesibles; no se tocan permisos, autenticación, archivos ni manos libres.

## Pruebas y aceptación

1. Pruebas Kotlin de mensajes planos multilínea, referencias matemáticas/Markdown, vista previa explícita y lectura completa.
2. CI backend y Android, firma de APK, auditoría de manifiesto y emuladores Android 15/16 en la rama `main`.
3. **Samsung físico pendiente:** aviso HTTPS completo; enviar, limpiar y recuperar borrador; abrir otro chat; varias respuestas seguidas; fórmulas matemáticas, tablas y respuestas largas; teclado abierto/cerrado, rotación, tamaño de letra grande y Play Protect.
4. Control de regresión sobre voz, audio, archivos, historial SQLite, permisos mínimos y API propia; el éxito en emulador no acredita pruebas de voz o audio en el dispositivo.

**Seguridad:** nunca desactivar Play Protect ni eludir permisos. Mantener una sola SKY Android/Windows con contratos compatibles, sin modificar SKY Windows ni BAQUEANO en esta iteración. La versión 0.8.46 no implica validación de Ollama con pesos reales.
