# SKY Android 0.8.46 — legibilidad premium y limpieza de estados

**Estado:** código en validación por GitHub Actions. No declarar que Play Protect aceptó la instalación ni que voz/audio funcionan físicamente en el Samsung sin probarlo.

## Problemas corregidos en la interfaz Android

1. **Respuesta parcialmente invisible.** `SkyMobileHome.makeBubble` abría WebViews de altura inicial fija de solo 56 dp, reajustándolos con temporizadores y con techo de 30.000 dp. Esto podía dejar texto cortado o crear saltos. Se reemplazan por **TextView nativos** con altura dinámica y márgenes, contraste y tipografía; no se crean WebViews por cada mensaje.
2. **Markdown/explicaciones poco legibles.** `SkyReadableAnswer` presenta títulos, énfasis, bloques de código y listas con tipografía nativa. Las fórmulas/MathML y tablas conservan el visor aislado de `SkyScientificMarkup`, pero se abren en un **lector oscuro casi a pantalla completa**, con desplazamiento vertical, opción de copiar todo y cierre claro. La vista de chat muestra la respuesta completa mientras sea de hasta 12.000 caracteres; para respuestas superiores muestra vista previa rotulada y ofrece leer el texto original completo, sin sobrescribir ni recortar el historial. Las preguntas extensas tienen tratamiento similar para evitar desbordes.
3. **Estados que no se limpian.** Los mensajes temporales de error o sugerencia dejan de ser burbujas permanentes. Se eliminan tras ocho segundos, al iniciar otra petición, al cerrar el panel o mediante `×`. No se borra el historial real. Los errores faciales transitorios se restablecen a estado inactivo tras ocho segundos sin interrumpir el micrófono ni la voz en curso.
4. **Pantalla que salta al final.** El chat solo baja automáticamente al comenzar o finalizar una solicitud, no al redibujar por cualquier estado o aviso. Leer una respuesta anterior deja de provocar desplazamiento involuntario.
5. **Guardado y exportación.** Cuando SQLite no puede guardar una respuesta, el mensaje sigue visible en la sesión y aparece un aviso explícito de que no quedó archivado. Al crear Word, se exporta **la consulta recién persistida**, no la última consulta anterior; si no se guardó, no se finge el documento.

## Seguridad y pruebas

- Renderizado nativo sin HTML/JavaScript de red; el lector aislado mantiene JS desactivado y bloquea archivos, contenido y cargas de red.
- Probar texto normal, Markdown, química, matemáticas, tablas, código, consultas largas, Unicode y lectura completa.
- Verificar que los mensajes de error se limpien, que el borrador no desaparezca, que no se borre el historial SQLite, y que la exportación no use una respuesta anterior.
- Verificar accesibilidad de botones, tamaño del panel con teclado, color/contraste en teléfono real y posibles cambios de escala de fuente.
- CI Android y pruebas instrumentadas API 35/36; pruebas físicas Samsung, Play Protect y Ollama con pesos reales permanecen pendientes si no se muestran evidencias de esos entornos.

**No se cambian** proveedor/modelos, claves de firma, permiso especial de notificaciones, SKY Windows ni BAQUEANO. La beta 0.8.45 previa permanece disponible durante esta revisión.