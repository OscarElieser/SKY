# SKY v10.9 — Validación reproducible

- Se ejecutaron 12 pruebas nuevas de contrato para Docker/TLS/Redis, secreto, recuperación y glosario; aprobación local.
- La regresión completa v10.9 se ejecutó en tres lotes con salida independiente. Los módulos heredados y nuevos no registraron fallos en esos lotes.
- La auditoría estática de `deploy/compose.yml` y `deploy/compose.integration.yml` pasó.
- La restauración sintética verificó SQLite, un archivo PNG, SHA-256 transferido, clave equivocada, ruta enlazada y destino existente.
- El escáner local de secretos es heurístico y **no** sustituye auditoría independiente.
- Docker no está instalado en el entorno local de desarrollo; el workflow de GitHub es responsable de demostrar la ejecución real del conjunto de contenedores.
- El modelo Whisper no está instalado en el entorno local de desarrollo. El job de CI intenta ejecutarlo con audios sintéticos y registra el resultado. No debe decirse que funciona hasta verificar la ejecución del job.
- Un contenedor de recuperación aislado **no equivale** a otro servidor físico ni implica una restauración real de producción.

## Resultado final de regresión local

Se ejecutaron 28 módulos de pytest separados en tres procesos para evitar un problema previo de cierre de procesos multimedia:

- Internacionalización, seguridad y recuperación (incluidos tests de v10.9): **84 aprobadas**.
- Creative Studio, automatizaciones, proyectos, integraciones: **91 aprobadas**.
- Motores heredados, dispositivos, Office y comunidad: **94 aprobadas**.
- **Total: 269/269 pruebas locales aprobadas.**

El ensayo Docker/HTTPS/Redis está definido para GitHub Actions, pero **no se ha ejecutado con Docker en este entorno local**. El reconocimiento con modelo auténtico será verificable por los resultados del job CI; las pruebas unitarias locales no miden precisión real de Whisper. El servidor remoto real sigue pendiente.
