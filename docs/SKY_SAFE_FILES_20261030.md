# SKY Safe Files — operaciones reales, alcance y evidencia

Fecha: 30/10/2026. Arquitectura central Windows/Linux y HUD web móvil/desktop.

## Qué hace
- Zona privada exclusiva local_data/sky_safe_workspace (configurable mediante SKY_SAFE_WORKSPACE_ROOT).
- Preparar y obtener autorización de **un uso** (3 minutos, ligada a sesión y
  parámetros), ejecutar solo al confirmar, comprobar SHA-256 al terminar.
- Crear archivos TXT, MD, CSV, JSON, PY, HTML; generar DOCX, XLSX, PPTX y PDF
  reutilizando sky_office, sin servicios cloud ni instalar nuevos permisos.
- Reemplazar, anexar texto, renombrar, mover a papelera y restaurar de papelera;
  no hay borrado definitivo. Nombre sencillo y extensión permitida, sin rutas.
- La API aplica autenticación de propietario y MFA existente. Las operaciones
  de modificación, renombre, anexado, papelera y restauración requieren el
  PIN configurado en Sentinel, además del token de aprobación.
- La creación también necesita autorización de un solo uso; el proceso de
  preparación es solo una vista previa, NO escribe el archivo.
- Nunca toca carpetas personales, apps ni archivos que no formen parte del
  espacio autorizado. Tokens Android de chat limitado no pueden entrar.

## API protegida
GET  /api/sky/safe-files/capabilities
GET  /api/sky/safe-files/list
GET  /api/sky/safe-files/trash
GET  /api/sky/safe-files/audit
GET  /api/sky/safe-files/download/{name}
POST /api/sky/safe-files/prepare
POST /api/sky/safe-files/commit

Ejemplo de preparación:
{"spec":{"op":"create","name":"informe.md","text":"Mi informe"}}
Se devuelve preview.expected_sha, preview.destination_state y approval_token.
Para ejecutar, POST /commit con spec idéntico, expected_sha,
destination_state y approval_token. El token caduca y no permite repetición.
La UI puede pedir el PIN de cada operación sensible si está configurado.

## Limitaciones verificadas
- Preparar no ejecuta cambios.
- Para editar documentos binarios se regenera una versión entera con datos
  explícitos; no hay edición interna arbitraria por voz.
- No se exponen rutas, claves ni contenido en registros de auditoría
  (se registran nombres cifrados por hash).
- La protección temporal de aprobaciones usa memoria de un solo proceso;
  para múltiples trabajadores requiere almacén compartido seguro antes de
  declararlo apto para producción multiinstancia.
- El hash de estado impide sobrescribir cambios detectados desde la vista
  previa, pero no sustituye control de acceso al sistema operativo.
- Se requiere validación física en Windows y Android; probar TestClient
  no demuestra compatibilidad de una APK ya instalada.
