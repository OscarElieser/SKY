# SKY v10.3 — Estado de seguridad y requisitos para publicación pública

Se conserva MFA TOTP del creador, permisos de API, validación de origen, límites de carga y controles de hosts de v10.2. Se añadieron pruebas y scanner local de archivos prohibidos. **No existe garantía de seguridad absoluta.**

## Antes de un servicio público

- Autenticación multiusuario y administrador con MFA resistente a phishing; sesiones almacenadas y revocadas en un backend compartido, no solo memoria del proceso.
- Gestor de secretos real con rotación, acceso mínimo y registros de uso; no dejar claves en Git, imágenes ni variables impresas.
- Redis para rate limiting global comprobado en balanceadores; HTTPS/TLS en reverse proxy con encabezados confiables y comprobación CSRF/CORS por rutas.
- Workers multimedia aislados con límites de CPU/memoria, permisos sin privilegios y subida de medios escaneados (formato, tamaño y duración).
- Protección de datos personales, mecanismos de borrado/exportación, controles sobre envíos a terceros y política de retención.
- Escaneo de dependencias y SBOM, revisiones SAST/DAST, pentest externo, carga concurrente y observabilidad. Backups cifrados con pruebas de restauración.
- Pruebas de idiomas, WCAG, RTL, audio y teclados internacionales por cada nueva pantalla.

## Controles verificados localmente

- `scripts/security_audit_v103.py` verifica nombres de rutas privadas y patrones de secretos de alto riesgo. No inspecciona paquetes instalados en busca de CVE ni detecta todos los secretos.
- 205 pruebas de la suite local aprobadas; incluye endpoints privados de voz y duplicación no destructiva de multimedia.
- `.github/workflows/security-v103.yml` define un chequeo automático futuro en GitHub Actions; su resultado real depende de los logs de Actions en el repositorio.

**SKY en modo local no debe exponerse directamente a Internet. BAQUEANO no fue modificado.**
