# SKY IA v10.7 — Production Hardening & Global Voice

**Promotor y visión del proyecto:** Oscar Elieser Chamorro Guzmán.

## Implementado

1. Lectura segura de claves del propietario desde archivos montados, con exclusión entre `_FILE` y variables inline, rechazo de enlaces simbólicos y límites de tamaño.
2. Configuración opcional de contenedores en `deploy/` con Caddy HTTPS, API como usuario no-root, Redis con contraseña en secreto, red backend privada y renderizador sin red. **No se ejecutó Docker en este entorno**.
3. Creación local de claves aleatorias sin sobrescribir ni revelarlas por el informe.
4. 22 etiquetas estáticas revisadas en siete idiomas, con medición real de cobertura; no se traducen mensajes privados.
5. Auditor offline de modelo `faster-whisper` instalado por el administrador y WER con audio de referencia real. **Sin modelo disponible, no hubo validación de transcripción real**.
6. Ejercicio de recuperación cifrada de SQLite WAL y medios en directorio temporal, con detección de contraseña incorrecta y archivo manipulado.
7. Doce pruebas nuevas y mantenimiento del conjunto de 233 pruebas heredadas.
8. Portada minimalista y separación de BAQUEANO preservadas; sin cambios sobre su producción.

## Pendiente antes de lanzar al público

- Probar contenedores en infraestructura real, permisos de secretos Compose, proxy TLS, Redis, workers y límites de recursos.
- Validar un modelo local real con audios de distintos idiomas y reporte de WER por idioma.
- Completar la cobertura lingüística; **solo 7 diccionarios recibieron 22 textos adicionales** en esta versión.
- Bloquear dependencias, pin de imágenes, escaneo de vulnerabilidades, auditoría/pentest independiente, backups externos y simulacro de desastre en máquina independiente.
- Asegurar que el perfil público cumple legislación aplicable de privacidad y tratamiento de datos.
