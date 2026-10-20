# Seguridad SKY v10.5 — Alcance y lista de verificación

## Implementado y probado en entorno local

- Cifrado autenticado AES-256-GCM con scrypt; nonce y sal aleatorios por copia.
- Instantáneas SQLite coherentes, SHA-256 por archivo y ensayo de restauración en memoria antes de restaurar a un nuevo directorio.
- Copia de medios de la biblioteca Creative Studio en una lista blanca de extensiones; rechaza archivos ocultos, claves, enlaces simbólicos, rutas maliciosas, archivos desmedidos y entradas duplicadas.
- Rechazo de sobrescritura, contraseña incorrecta y respaldos modificados.
- API de STT requiere credencial privada del creador y el segundo factor que la instalación tenga configurado.
- Límite de 10 MB/60 segundos para entrada de audio; sin envío implícito a servicios externos.
- No se crea un endpoint HTTP de backup/restauración ni se exponen los secretos en el ZIP de distribución.

## Seguridad que falta antes de producción pública

1. **Gestor dedicado de secretos**, rotación, inventario de claves y registro de acceso a secretos. Nunca comprometer `.env`, tokens, grabaciones ni claves MFA.
2. **MFA del creador y de roles críticos**, recuperación de cuentas, sesiones distribuidas, cookies seguras y control de roles revisado.
3. **Workers aislados** para FFmpeg y STT, sin privilegios, sin red si no es necesaria, límites efectivos de CPU/GPU/memoria, tiempos y tamaño de salida.
4. **WAF / protección DDoS, Redis, cuotas por usuario y por IP**, TLS confiable de extremo a extremo y reglas de origen.
5. **Backups externos cifrados y pruebas de restauración en otro servidor**, incluyendo videos, archivos y configuraciones autorizadas; objetivos RPO y RTO medidos.
6. **Escaneo de dependencias y SBOM, SAST/DAST, pentest independiente**, verificación de licencias, privacidad y políticas de retención.
7. **Pruebas reales de motores multilingües** con diferentes acentos, ruido, idiomas, sesgos y accesibilidad. Ningún idioma puede garantizar una tasa de error nula.

## Sobre la recuperación actual

`neural_core.sky_recovery_full` copia bases detectadas y recursos de `sky_creative.store_dir()/media`. No almacena contraseñas ni copia indiscriminadamente `local_data/`. La carpeta de restauración debe ser nueva; SKY no la incorpora automáticamente a su instalación en funcionamiento. Verificá los resultados antes de una migración manual planificada.
