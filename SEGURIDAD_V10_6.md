# SKY IA v10.6 — Seguridad: estado y límites

**Verificado localmente:** 233 pruebas; claves de IA no transferidas al proceso STT bajo la prueba; límite de tiempo; lectura de audio de tamaño limitado; restauración cifrada en directorio nuevo; comparación de integridad; autenticación API privada.

**Todavía no verificado para Internet:** aislamiento real de procesos mediante contenedores y perfiles de sistema, autenticación de cuentas a gran escala, MFA administrado centralmente, Redis HA distribuido, límites por usuario y por IP, TLS gestionado, gestión de secretos rotados, auditoría de dependencias/SBOM externa, test de penetración, recuperación de desastres y transcripción exacta con un modelo local instalado.

**No subir a GitHub:** `.env`, llaves API, archivos `local_data/`, secretos MFA, paquetes de respaldo `.skybackup`, grabaciones privadas, medios privados, modelos descargados ni volcados de bases de datos. Los permisos del sistema de archivos importan: el STT ejecuta un proceso separado pero no es una sandbox de kernel.

El ensayo `sky_recovery_drill_v106` usa datos sintéticos por defecto; `--installed` es explícito y debe ejecutarse con SKY detenido. No constituye prueba de restauración de todos los servidores, correos, servicios de terceros o dominios.

Las traducciones son **parciales**: catálogo de idiomas no significa 100 % de navegación localizada ni reconocimiento de voz equivalente para todas las lenguas.

**BAQUEANO:** ninguna modificación de código o datos de producción.
