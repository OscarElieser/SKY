# SKY IA v9.3 — Registro de validación

**Alcance:** prototipo local funcional de UI minimalista, integración autorizada con el creador y automatización persistente.

## Comprobaciones realizadas

1. **140 pruebas automatizadas** pasaron (`python -m pytest -q`), incluidas las 131 de v9.2.
2. FastAPI respondió sobre TCP real a `/api/health`, devolviendo la versión `9.3.0`.
3. Se creó un flujo con una llamada HTTP, quedó `awaiting_approval`, se autorizó mediante otra llamada y el worker interno lo ejecutó en segundo plano sin comandos manuales.
4. En pruebas locales: persistencia SQLite, fechas futuras, repetición programada, cancelación, generación real de DOCX, asociación con Project Hub, respaldo SQLite y detección de trabajos ambiguos.
5. Un usuario real de prueba inscrito por invitación autenticó su cuenta comunitaria, pero no pudo consultar ni la ruta privada de BAQUEANO ni los flujos administrativos ni el Project Hub.
6. La portada y el editor de flujos se renderizaron con Chromium usando HTML/CSS/JS original y datos simulados de API para la comprobación visual. Se revisó el ancho de la vista móvil de 390 px y no hubo errores JavaScript en la prueba de la portada.
7. El navegador no pudo abrir directamente localhost por restricciones del entorno. No se confunde la prueba visual controlada con la prueba HTTP del servidor real.

## No probado en esta entrega

- Micrófonos o cámaras físicos; VR/AR;
- integraciones reales con Gemini, OpenAI, Anthropic, Tailscale y dispositivos;
- redes de producción, picos de tráfico, SLA, balanceo de carga;
- sistemas de identificación legal, recuperación de contraseñas o MFA;
- modificaciones de BAQUEANO en producción.

**Autoría conceptual y visión:** Oscar Elieser Chamorro Guzmán. Esta documentación es evidencia de trabajo, no registro oficial de marca o autoría.
