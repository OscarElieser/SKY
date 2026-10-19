# Seguridad de SKY v10.7 — alcance y pendientes

## Protecciones nuevas verificadas mediante código y pruebas

- Las claves de acceso y de MFA pueden proporcionarse por archivo privado fuera del repositorio; una configuración doble o un secreto ilegible no se ignora silenciosamente.
- El modo público requiere la clave del propietario, MFA, Redis, TLS delegado y worker de render separado. El resultado de `validate_environment` sigue indicando `public_ready: false` hasta una auditoría externa.
- La base Compose elimina puertos públicos de API y Redis, instala cap drop y no-new-privileges, ejecuta API/renderizador como UID 10001 y configura red nula para el renderizador.
- Recuperación cifrada AES-256-GCM (implementada en versiones anteriores): ahora tiene ensayo sintético de desastre ante clave equivocada y archivo alterado.
- Audio de voz procesado localmente sin subirlo automáticamente a proveedores externos; la auditoría no imprime transcripciones privadas.

## Límites importantes

**La sintaxis YAML y las propiedades declaradas no garantizan que Docker ejecute correctamente la pila.** En este entorno no hay Docker, así que faltan smoke tests reales de HTTPS, permisos de secretos, networking, disponibilidad del renderizador y redis. **MFA actual es TOTP en proceso y no un servicio multiinstancia compartido**. Los flujos autónomos se deshabilitan por defecto en el perfil público.

Las credenciales provisionales deben generarse con `scripts/provision_secrets_v107.py` únicamente en el servidor privado. No añadir `deploy/secrets/`, `deploy/production.env`, `.env`, `local_data`, bases privadas ni medios personales al repositorio. El script no muestra los secretos. Asegurar que la semilla TOTP se registre fuera de banda en el autenticador del propietario.

Se requieren adicionalmente: HTTPS real, MFA probado en varios dispositivos, vigilancia, límites de tasa comprobados, gestión de secretos central, bloqueo de imágenes/dependencias por digest, copias remotas cifradas, pruebas de restauración integral y pentest de un tercero. No existe certificación de invulnerabilidad ni de producción mundial.
