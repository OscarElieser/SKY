# SKY: analizar, proponer y aprobar cambios (30 octubre 2026)

Análisis: GET /api/sky/safe-files/analyze/{name}. Texto y estadísticas
parciales, SHA256; no usa proveedores externos ni cambia archivos.

Propuesta: POST /api/sky/safe-files/edit/preview. Campos: name, mode
(replace_once o append_text), expected_sha, find y replacement.
Reemplazo literal exige una única coincidencia, sin expresiones regulares
ni ejecución de código; el servidor devuelve comparación, conteos y digest.

Aprobación: POST /api/sky/safe-files/edit/prepare envía además
proposal_digest. Valida que original y resultado propuesto permanezcan
idénticos; usa sky_approvals existente y su token ligado a la sesión.

Guardado: POST /api/sky/safe-files/commit con el recibo de un uso, PIN,
comprobación SHA256 y escritura atómica de sky_safe_workspace. Sin PIN no
se modifican archivos; si cambia la propuesta, se exige nueva vista previa.

Alcance: TXT, MD, CSV, JSON, PY y HTML; DOCX/PDF/PPTX/XLSX conservan
solo lectura. No se promete conservar estructura de binarios complejos
al editarlos. No hay autoedición por solicitudes libres ni permiso al token
del chat Android para modificar archivos.


## Análisis asistido voluntario (solo Ollama local)
POST /api/sky/safe-files/ai-analyze: name, expected_sha, instruction.
Envía un fragmento de hasta 9000 caracteres al Ollama configurado en localhost;
si Ollama no está operativo, devuelve 503 sin fallback a nube. El fragmento se
trata como contenido no confiable (defensa ante instrucciones incrustadas).
Respuesta consultiva, no ejecutable, sin guardado, sin verificación factual
independiente. La aplicación muestra claramente que las sugerencias NO se han
aplicado. Para modificar sigue siendo indispensable comparar, preparar recibo y
confirmar con PIN. El botón no envía nada hasta que el dueño lo pulsa.
