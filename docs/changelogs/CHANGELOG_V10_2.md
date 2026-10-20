# SKY IA v10.2 — Global Intelligence · Multilenguaje y seguridad

**Dirección y visión del proyecto:** Oscar Elieser Chamorro Guzmán.

## Entregado con código y pruebas

- Localización transversal de las páginas principales: portada, Creative Studio, Office, proyectos, automatizaciones, comunidad, metaverso y panel privado. Selector común, cambio instantáneo, idioma de documentos y prompts a proveedores, orientación RTL para escrituras de derecha a izquierda y preferencia por perfil comunitario guardada en SQLite.
- Catálogo de **90 lenguas** seleccionables con etiquetas BCP-47 acotadas; traducción revisada del núcleo de **28 cadenas en 13 idiomas adicionales**, y catálogo completo de 108 etiquetas comunes para inglés y español. Los otros idiomas tienen respaldo explícito, no traducción global ficticia. Integración opcional con Gemini u Ollama para traducir texto bajo consentimiento.
- Captura por voz del navegador vinculada al idioma activo en portada, Studio, Office y metaverso; compatibilidad real condicionada al navegador y al servicio de reconocimiento.
- Subtítulos: importar SRT, exportar WebVTT con Unicode, quemar subtítulos sobre MP4 mediante FFmpeg, ejemplo MP4 real; no es todavía transcripción automática.
- Narración MP3 mediante gTTS opcional, únicamente con consentimiento explícito para compartir texto con proveedor externo. No hay clonación de voces ni doblaje sincronizado automático de películas.
- MFA TOTP opcional para la clave privada del creador; sesión temporal con SHA-256 de tokens y revocación; código temporal no reutilizable en proceso; las sesiones de comunidad no pueden sustituir la credencial privada.
- Modo público con barreras de arranque: requiere MFA, dominio permitido, terminación TLS administrada y Redis accesible con limitador compartido; renderizador creativo separado. **No significa que el servidor esté certificado para internet**.
- Protección de Origin para mutaciones de API, cabeceras CSP/no-cache, limitación de cuerpos JSON y medios, descarga privada de renders temporales, no inclusión de bases y secretos en ZIP.
- Conservadas rutas anteriores, proyectos y exportaciones; interfaz principal sigue sencilla. BAQUEANO no fue modificado.

## Pruebas

- **199 pruebas automáticas superadas**: 191 heredadas y 8 nuevas (catálogos, cuentas independientes, MFA, API, render de video subtitulado, bloqueo de origen y controles de despliegue).
- Sintaxis de Python y JavaScript verificada. FFmpeg genera un MP4 y un PNG reproducibles desde una fuente auténtica.
- Se intentó Chromium con servidor HTTP real: el entorno bloqueó el navegador con `ERR_BLOCKED_BY_ADMINISTRATOR`. **Prueba visual integral pendiente**, no se presentan capturas falsas.
- Sin prueba en vivo de Gemini, gTTS, Redis real ni despliegue público; requieren servicios/configuraciones del operador.

## Limitaciones

- La interfaz NO está completamente traducida a 90 idiomas; la cobertura es explícita y crece por paquetes revisados. Respuestas en otras lenguas dependen del modelo IA seleccionado.
- MFA se activa al configurar `SKY_OWNER_MFA_SECRET`, no automáticamente en instalaciones locales anteriores. En producción pública sí se exige.
- El limitador distribuido está implementado con Redis opcional pero no ha sido ejercitado contra un clúster real aquí.
- Las funciones multimedia importan subtítulos creados previamente. No hay reconocimiento de voz masivo, traducción de películas o doblaje labial.

## Continuidad

Paquete actualizado de v10.1; conservar `local_data` con un respaldo y **no publicar contraseñas, tokens, mensajes ni SQLite**.
