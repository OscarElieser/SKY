# SKY IA v10.4 — Secure Recovery & Global UI

**Visión y dirección del proyecto:** Oscar Elieser Chamorro Guzmán.

## Implementado

- **Recuperación cifrada de bases SQLite:** `neural_core.sky_secure_backup` utiliza el respaldo en línea de SQLite y cifra los resultados con AES-256-GCM. La clave deriva de una frase privada mediante `scrypt`. No se publica una ruta HTTP para descargar estos respaldos.
- **Simulacro de recuperación verificable:** `verify` descifra y comprueba hashes SHA-256, estructura del archivo y `PRAGMA integrity_check` por cada base restaurada **solo en memoria**. No sobrescribe la instalación real.
- **Compatibilidad de respaldos con WAL:** normalización segura de las marcas SQLite del snapshot para recuperar archivos creados desde bases en modo WAL. Cubierto por una prueba de regresión real.
- **Defensa ante archivos adulterados:** autenticación de cifrado, rechazo de rutas con desplazamiento, archivos duplicados, tamaños excesivos, sobrescritura y enlaces simbólicos.
- **Idiomas aplicados en la UI:** más etiquetas revisadas para inglés, portugués, francés, árabe, chino, japonés y suajili. El localizador también gestiona automáticamente `aria-label` y `title` estáticos y permite volver al idioma anterior sin confundir traducciones con contenido privado.
- **Seguimiento honesto de cobertura:** auditoría de etiquetas HTML que distingue cadenas traducidas, pendientes y lenguas solamente seleccionables.
- **Validación:** 214 pruebas (205 heredadas y 9 nuevas), sintaxis JavaScript comprobada. Se mantienen las exclusiones de contenido personal en el localizador.

## Límites

- El respaldo cifrado **solo contiene bases SQLite**. Multimedia, `.env`, claves, archivos subidos, configuraciones específicas y archivos de resultados requieren un procedimiento de respaldo separado. No se recupera un entorno completo usando únicamente `.skybackup`.
- La frase de respaldo debe guardarse por medios seguros; sin ella no se puede descifrar el archivo. No se envía ni se guarda en el archivo.
- No se implementó restauración automática sobre bases en uso. La recuperación probada en memoria reduce riesgo pero no reemplaza los ensayos de restauración de extremo a extremo en un servidor independiente.
- Los idiomas seleccionables no están completamente traducidos, y la voz depende del motor local instalado o de proveedores autorizados. La cobertura actual debe consultarse antes de anunciar disponibilidad por lengua.
- SKY no está certificada para producción pública. MFA, proxy TLS, Redis privado y separación de workers siguen siendo necesarios; se requieren pentests y revisión independiente.

No se modificó BAQUEANO en producción.
