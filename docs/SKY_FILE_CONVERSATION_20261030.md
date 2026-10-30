# SKY — Propuestas documentales desde conversación

Fecha: 30/10/2026. Conexión del chat normal y voz con el espacio seguro de SKY.

1. El parser sky_file_intents identifica frases completas sin utilizar proveedores
   ni ejecutar código; las órdenes incompletas continúan al asistente normal.
2. El tipo safe_file_proposal se entrega desde /api/asistente/mensaje o /stream.
3. El HUD muestra la operación y contenido, llama a /api/sky/safe-files/prepare
   con autenticación de propietario y recibe vista previa y recibo de un solo uso.
4. Únicamente tras pulsar Ejecutar, /api/sky/safe-files/commit comprueba sesión,
   PIN configurado, caducidad, parámetros y SHA-256. La voz no sustituye el clic.
5. Se informa éxito solo cuando el servidor acredita el cambio. De otro modo,
   se muestra error y se requiere volver a preparar la operación.

Ejemplos: Crea un archivo notas.md con contenido: Prueba.
Agrega al archivo notas.txt: nuevo texto.
Renombra el archivo notas.txt a notas_final.txt.
Mueve el archivo notas.txt a la papelera.
Restaura archivo notas.txt de la papelera con id [identificador de 32 caracteres].
Crea un documento informe.docx con contenido: Informe.

Límites: solo archivos del workspace privado, no archivos externos al sistema;
chat móvil con token limitado no modifica nada. No se han probado dispositivos
reales ni se ha generado APK en este bloque.
