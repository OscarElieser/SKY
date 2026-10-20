# Seguridad SKY IA v10.2 — alcance comprobado y trabajo pendiente

| Área | Implementado localmente | Antes de producción pública |
|---|---|---|
| Acceso del propietario | Clave larga; MFA TOTP opcional; sesión de segundo factor de 20 minutos; revocación y antirreutilización de código | MFA obligatorio, recuperación segura, FIDO2 opcional, provisión de identidades real y auditoría |
| Comunidad | Identidades y memorias separadas, sesión con bearer, preferencias de idioma por usuario | Control fino RBAC, detección de anomalías, revalidación de sesiones, políticas de privacidad |
| HTTP | Lista de hosts, CSP, no-store, anti-iframe, no-sniff, Origin para mutaciones | TLS con proxy de confianza, HSTS real, WAF y revisión de cabeceras por dominio |
| Límites | Límites de cuerpos JSON, cuotas locales, TOTP bajo rate limit | Redis compartido activo, limitación por cuentas/costo y protección DDoS externa |
| Multimedia | Ingesta por identificador, FFmpeg sin shell, tiempos máximos, subtítulos bounded | Sandbox de códecs, antivirus, worker dedicado, escáner SCA, presupuesto de CPU/GPU |
| Secretos | Ninguna API key en ZIP; `.env` fuera de control de versiones | Vault administrado, rotación/revocación y secretos separados por entorno |
| Estado | SQLite local | Migración planificada con respaldos y control de acceso, restauraciones comprobadas |
| Supervisión | API/diagnóstico y tests locales | Logs inmutables, métricas, trazas con retención, alertas y pentest independiente |

### Publicación controlada

- `SKY_DEPLOYMENT_MODE=local` permanece como valor seguro por defecto.
- `SKY_DEPLOYMENT_MODE=public` no inicia sin MFA TOTP, dominio en `SKY_TRUSTED_HOSTS`, Redis y `SKY_BEHIND_TLS_PROXY=1`, además de `SKY_CREATIVE_WORKER=0`.
- `SKY_BEHIND_TLS_PROXY=1` **no configura TLS por sí solo**: la terminación HTTPS, las IPs del proxy y las cabeceras de esquema deben implementarse y comprobarse aparte.
- Redis debe ser privado; el arranque comprueba conectividad cuando el modo es público. Esto no prueba resistencia ante grandes ataques.
- SRT se convierte y renderiza localmente; el render directo se deshabilita en modo público hasta aislarlo en worker.
- Gemini y gTTS nunca se consideran validados en vivo en esta entrega. No existe un servicio de auditoría externa conectado.

### Procedimientos pendientes

1. Pentest autenticado y no autenticado; revisión independiente de amenazas, flujos de datos y fallos de autorización horizontal/vertical.
2. Auditoría SCA y SBOM, licencias, actualizaciones con CVE, escaneo de malware al ingreso de medios.
3. Copias de seguridad cifradas y restauraciones en entorno separado; pruebas de recuperación por pérdida de MFA.
4. Infraestructura pública: Hostinger o proveedor elegido, Cloudflare, repositorio GitHub, base de datos acorde a escala; BAQUEANO continúa independiente.
5. Revisión de protección de datos y avisos para usuarios multilingües.

**No se afirma que SKY sea invulnerable, auditada externamente o lista para recibir usuarios públicos masivos.**
