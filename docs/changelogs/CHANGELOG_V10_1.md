# SKY IA v10.1 — Multilingual & Creative Security

**Proyecto impulsado por Oscar Elieser Chamorro Guzmán.**

## Cambios comprobables

- `sky_languages`: catálogo extensible de **31 códigos base** de idioma, negociación de `Accept-Language`, etiquetas BCP-47 acotadas, mensajes estáticos revisados **en 10 idiomas** y respaldo a español. Selección guardada localmente; las demás lenguas del catálogo quedan preparadas para extensión, sin garantizar traducción automática completa.
- `language_api`: rutas de catálogo, glosario, preferencias privadas, pista de escritura y traducción opcional. El texto solo se envía a Gemini u Ollama tras seleccionar proveedor y autorizar expresamente. No se adjuntan memorias automáticamente en esta ruta.
- `assistant`: prioriza el idioma expresamente pedido o el idioma del texto; de lo contrario, la preferencia configurada. Esto depende del idioma realmente comprendido por el modelo conectado.
- Interfaz: selector de idioma discreto en inicio y estudio; corrección de un error de alcance JavaScript en los controles de Creative Studio v10.
- Editor de video: pistas visuales sobre la composición **global** (no solo por clip), fotogramas de posición y máscaras interpoladas entre imágenes de máscara, renderizadas fotograma a fotograma con FFmpeg y exportadas a `.skyzip`.
- Seguridad: hosts permitidos, CSP, protección contra iframe, no sniffing, caché privada, limitación de cargas JSON y estrangulamiento básico de intentos fallidos, sin confianza implícita en cabeceras proxy del cliente. Mensajes Gemini genéricos para no exponer detalles de SDK.
- `sky_render_worker.py`: trabajador de render separable del servidor HTTP; conserva colas existentes y revisión de trabajos interrumpidos.
- Un ejemplo comprobado: MP4 renderizado por el trabajador externo, PNG extraído del render y proyecto editable.

## Verificaciones

- 191 pruebas de regresión y nuevas (`PYTHONPATH=. pytest -q`).
- `node --check` de `creative.js`, `sky-home.js` y `sky-language-ui.js`.
- Generación reproducible de MP4 desde un proceso worker independiente.
- Gemini **NO probado** con credenciales de producción en este entorno. No se afirmó lo contrario.
- Browser Chromium restringe acceso al sitio local; prueba visual integral **pendiente**.

## Limitaciones reales

- Los idiomas catalogados no son traducciones integrales. Hay frases offline en 10 idiomas; las restantes requieren paquetes lingüísticos, traducción bajo autorización y revisión humana.
- Las máscaras actuales interpolan imágenes alfa; todavía no reconocen semánticamente personas u objetos a lo largo de un video. Las pistas son gráficas, no sustituyen una línea de tiempo profesional NLE completa.
- Seguridad en profundidad no significa protección absoluta. Antes de exponer SKY públicamente hacen falta identificación administrativa independiente con MFA, TLS, protección perimetral (WAF), limitación distribuida, alertas, backups restaurados y auditoría externa.
- No se ha modificado BAQUEANO en producción.
