# Seguridad de SKY IA v10.1 — medidas y pendientes

**Aplicado en esta versión:** `TrustedHostMiddleware` con lista explícita de hosts; CSP con scripts del mismo origen, prohibición de iframes/objetos, bloqueo de MIME sniffing, no-cache para API y rutas de propietario, política de referencia restrictiva, controles de permisos de navegador, HSTS para solicitudes HTTPS, validación de claves del creador constante y existente, protección básica contra ráfagas de 401, tamaño de JSON restringido, mensajes de error de Gemini sin trazas privadas, aislamiento opcional del renderizador, máscaras/archivos manejados por identificadores validados y sin `shell=True`.

**Pendiente para exposición pública real:** MFA (TOTP/FIDO2) con recuperación segura, gateway de autenticación con roles, rotación y revocación de credenciales, WAF y rate-limiting distribuido, mitigación de DDoS, límites por usuario y presupuesto, escaneo SCA de dependencias, antivirus/sandbox de medios, PostgreSQL/Redis para escala, controles de privacidad y retención, registro de auditoría resistente a manipulaciones, cifrado/backup fuera de banda, secretos administrados, CORS estricto de cualquier origen añadido, control de subida de archivos y pruebas de penetración. Un entorno local no sustituye el despliegue endurecido.

**Cuidados al desplegar:**
- HTTPS en proxy de confianza; limita `--forwarded-allow-ips` únicamente a IP del proxy. No escuches `0.0.0.0` sin controles perimetrales.
- No uses `SKY_TRUSTED_HOSTS=*` (se rechaza).
- El throttling en memoria **no es distribuido ni persiste reinicios**.
- La portada de BAQUEANO es solo HTML de acceso y no expone datos, pero la API requiere clave de administrador. Para uso público se debe añadir cuenta administrativa/MFA.
- No hay garantías de protección absoluta ni de cobertura de «todas las vulnerabilidades».

Documentación sobre hosts y proxy: https://fastapi.tiangolo.com/advanced/middleware/ y https://fastapi.tiangolo.com/advanced/behind-a-proxy/.
