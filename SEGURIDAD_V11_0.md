# Seguridad SKY v11.0 — Alcance y riesgos pendientes

- **HTTPS:** el smoke test valida nombre `sky.test`, cadena firmada por CA temporal y expone solo el proxy en `127.0.0.1:18443`. No equivale a un certificado público de producción.
- **Redis:** red interna y contraseña en secreto montado; nunca publicar 6379. La autenticación y salud se verifican en CI.
- **Worker:** sin interfaz HTTP, sin ruta de red; healthcheck observa el proceso. Permisos reducidos `cap_drop:ALL`, `read_only:true`, `no-new-privileges`.
- **Voz:** el binario open-weight de tercero no está auditado en profundidad. La CI usa audios TTS sintéticos; WER puede ser alto. No enviar audio de usuario sin consentimiento.
- **Backups:** AES-256-GCM, contraseña externa, comprobación de huella y restauración a directorio vacío sin acceso a bases activas; no reemplaza procedimiento de recuperación física entre servidores.
- **Prueba de carga:** limitada a loopback y `/api/health`; no prueba carga de IA, ataques de fuerza bruta ni capacidad de GPU.
- **Dependencias:** revisar CVE, firmar/escudriñar imágenes, pin a digest, generación SBOM, bloquear egress de procesos sensibles, monitorizar costes, activar MFA y WAF antes de prod.
- **CI:** dependencias y jobs deben finalizar en verde para hablar de integración verificada; si se bloquea o falla, registrar la incidencia y no afirmar éxito.
