# SKY IA v10.8 — Global Voice & Recovery Operations

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

- Copias completas cifradas bajo programación **externa**: creación, autenticación, rotación con bloqueo no concurrente, permiso 0700 y retención entre 2 y 90.
- Ensayo de restauración en carpeta aislada con medición de RTO del caso probado y estimación de edad de copia; nunca sobrescribe producción.
- Protección frente a backups manipulados, secretos expuestos, rutas enlazadas, ejecuciones concurrentes y borrado de archivos ajenos.
- Archivo systemd de referencia con `LoadCredential`, sin instalar ni habilitar servicios automáticamente.
- Auditor de configuración Docker y prueba opcional de importación en contenedor aislado, sin red ni puertos publicados. Docker no disponible en el entorno de creación.
- Benchmark de transcripción local en dos o más idiomas, con WER y sin revelar audios o transcripciones en registros. No hay pesos de modelo en el ZIP; no se comprobó una voz Whisper real.
- 18 etiquetas de operación traducidas en 9 idiomas. Las traducciones siguen siendo parciales.
- Pruebas automáticas y workflow para GitHub Actions. Revisar resultados reales de CI al publicar.
- Ninguna modificación al sistema productivo BAQUEANO ni a los recursos personales en `local_data`.
