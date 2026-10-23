# SKY v10.9 — Matriz de seguridad y riesgos pendientes

**Controles incorporados:** HTTPS con CA local verificada en ensayos CI; Redis con contraseña desde secreto montado; clave del creador y semilla TOTP separadas del código; API y Redis no publicados; renderizador sin red; archivos de respaldo autenticados y cifrados; huella externa obligatoria en restauración; destino nuevo y no sobrescribible.

**Permisos de Docker Compose (advertencia importante):** cuando `secrets:` usa archivos locales como bind mounts en Linux, `0600` del host puede impedir su lectura a un contenedor sin privilegios UID/GID 10001. En el CI efímero se otorga acceso de lectura al grupo 10001 y se prohíbe reutilizar un directorio `deploy/secrets` existente. **En producción, el administrador debe crear un grupo de servicio, establecer ACL mínimas y ensayar el acceso real sin hacer claves legibles para todos.**

**Riesgos aún abiertos:**
- Caddy `tls internal` es solo para ensayos CI. Producción exige certificados de CA pública y hostname real validado.
- El proxy necesita revisión de confianza en cabeceras reenviadas y gestión de IP de cliente; la limitación de Redis usa el cliente visto desde la API, potencialmente el proxy. Añadir cabeceras confiables desde un único proxy y pruebas anti-suplantación antes del lanzamiento.
- El ensayo de restauración en otro contenedor **no prueba** pérdida de zona, cambio de servidor físico, ruptura de DNS ni reposición de secretos.
- Los backups no contienen credenciales, certificados, configuraciones externas o pesos de voz. Son imprescindibles un gestor de secretos, respaldos remotos inmutables, rotación de claves y un ejercicio integral con otra máquina.
- La prueba de voz de CI usa locuciones sintéticas de tres idiomas, no audios naturales consentidos de usuarios. La WER informa desempeño de muestra, no certifica uso público o calidad universal.
- Falta auditoría independiente de dependencias, SAST/DAST, SBOM, pentest contratado, revisión de sesiones y monitoreo operativo.

**BAQUEANO:** no se modifican bases, servicios ni producción de BAQUEANO. Su acceso administrativo permanece solo para el creador.
