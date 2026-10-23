# SKY v10.8: controles demostrados y pendientes

## Implementado

El backup se cifra y autentica mediante el motor de v10.5, verifica SQLite y SHA-256 y mantiene una rotación segura con bloqueo exclusivo. Se exige secreto de archivo, permisos estrictos y restauración hacia una carpeta nueva, nunca sobre la instalación activa. La tarea periódica requiere instalación manual del operador. La prueba de contenedores respeta un contenedor efímero sin red ni puertos publicados cuando se ejecuta voluntariamente.

## Por comprobar en servidores reales

- Ejecutar y monitorizar Docker Compose en una infraestructura temporal, sin exponer a usuarios reales.
- Usar un gestor central de secretos, almacenamiento remoto cifrado e inmutable, y probar recuperación tras pérdida del servidor completo.
- Supervisar errores, latencias, tasa de restauración, integridad y tasa real de transcripción por idioma.
- Probar TLS, MFA en sesiones reales, controles distribuidos, SBOM, CVE, SAST/DAST y pentest autorizado por terceros.
- Validar límites de cuota, cifrado en tránsito, permisos de grupos y compatibilidad en Windows. El scheduler v10.8 está validado en Linux/POSIX.
- Instalar un modelo Whisper compatible y auditar licencia/pesos antes de confiar en sus resultados.

**No es certificación de producción ni auditoría de penetración.**
