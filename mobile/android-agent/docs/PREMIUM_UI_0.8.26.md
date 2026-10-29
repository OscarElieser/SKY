# SKY Android 0.8.26 — paneles premium

## Cambios de interfaz
- Chat más limpio: desaparecen de la zona inferior «Privacidad», «Motor» y «Acceso» y de la cabecera «Enseñar» e «Historial». Ningún permiso o comando se elimina; están en Ajustes.
- Ajustes: ventana con fondo oscuro, tarjetas índigo/cian, botón de cierre y pestañas horizontales: Motor, Privacidad, Acceso, Creatividad, Memoria, Herramientas, Historial, Diagnóstico y Voz.
- Privacidad: las casillas de autorización de nube y datos privados modifican los controles **reales** de la próxima consulta; se mantienen las restricciones y consentimientos anteriores.
- Historial: buscador, filtro Hoy/Ayer/Groq/Gemini/Favoritos, resultados paginados, detalles, abrir en conversación, editar título, favoritos, borrar un registro y exportar.
- La migración SQLite v1→v2 es aditiva: se conserva `sky_conversations.db` y solo se añade `is_favorite`. Renombrar no modifica los textos originales.

## Pruebas incorporadas
`SkyPremiumHistoryRuntimeTest` verifica en Android que guardar, renombrar, consultar, filtrar, marcar favoritos y eliminar no altera preguntas/respuestas. Los flujos de CI existentes exigen también compilación de APK y pruebas de Android 15 y 16 antes de publicar.

## Cómo comprobar en Samsung
1. Instalar solo una APK 0.8.26 **firmada con la misma clave** que 0.8.20, cuando exista en GitHub Releases y se confirme el flujo.
2. No desinstalar 0.8.20: actualizar sobre la aplicación anterior.
3. Abrir chat: verificar que abajo solo haya el compositor y los controles de adjuntar/enviar; los tres botones de texto deben desaparecer.
4. Abrir engranaje: comprobar todas las categorías y que cada sección cambia el contenido al tocarla.
5. Ir a Privacidad: marcar permisos para una consulta de prueba y comprobar que se desmarcan luego de enviarla.
6. Ir a Historial: filtrar Groq, editar el título de un registro de prueba, marcar favorito, reabrir y exportar. Comprobar que los registros antiguos permanecen.
7. Confirmar funcionamiento en modo vertical con teclado visible, letra del teléfono ampliada y navegador de accesibilidad.

**No equivale a validar una APK real:** hasta ver CI satisfactoria, instalación, navegación y datos persistentes en el Samsung, la función queda *implementada en código / prueba real pendiente*. SKY Windows no se modifica.
