# SKY v10.4 — controles comprobados y pendientes de seguridad

**Resultado local:** 214 pruebas superadas y escaneo de 292 archivos sin coincidencias de los patrones incluidos. No se ha realizado un pentest independiente ni una auditoría formal de dependencias.

## Nuevo: protección de respaldos

- `python -m neural_core.sky_secure_backup create --file <ruta>` genera un archivo cifrado local `.skybackup` usando AES-256-GCM y clave derivada con scrypt. Obtiene instantáneas SQLite mediante Online Backup API; admite fuentes SQLite WAL.
- `python -m neural_core.sky_secure_backup verify --file <ruta>` autentica el archivo, confirma SHA-256 de cada base y la puede cargar en memoria para ejecutar `PRAGMA integrity_check` sin tocar las bases activas.
- Ni la contraseña ni las bases aparecen en texto plano en el archivo resultante. El modo CLI no crea endpoints públicos.
- Rechaza respaldo alterado, frase incorrecta, enlaces simbólicos, sobreescritura, nombres y rutas inválidos, y archivos de tamaño excesivo.
- Es indispensable conservar la clave privada fuera de SKY. La recuperación probada no cubre todo el entorno: biblioteca multimedia, archivos, `.env`, tokens, datos de proveedores, claves MFA y configuraciones del sistema se respaldan por procedimientos diferentes.

## Actualización lingüística

- Se amplía el catálogo revisado de la UI en siete idiomas adicionales sin fingir una cobertura completa de los 90 idiomas disponibles en el selector.
- El localizador actualiza atributos accesibles `aria-label` y `title` reconocidos; no traduce conversaciones, proyectos ni datos privados.
- La cobertura detectada por auditoría se describe en `VALIDACION_V10_4.md`.

## Bloqueos restantes antes de exponer el servicio

1. MFA obligatorio con recuperación segura y sesiones distribuidas resistentes a reutilización.
2. Proxy HTTPS y verificación de cabeceras de origen desde proxies de confianza; WAF y gestión de secretos dedicada.
3. Escaneo de archivos multimedia, aislamiento de FFmpeg y recursos en workers no privilegiados; cuotas de CPU/almacenamiento.
4. Cuotas distribuidas verificadas en Redis, logs y métricas centralizados con controles de retención.
5. Backups de bases y multimedia, restauración real en un servidor separado y pruebas RPO/RTO.
6. Auditorías independientes de seguridad, privacidad, dependencias, accesibilidad y rendimiento con usuarios reales.

**BAQUEANO es independiente y su producción no ha sido modificada.**
