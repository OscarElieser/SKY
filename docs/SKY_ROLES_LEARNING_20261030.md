# SKY IA — Memoria operativa de fallos por especialidad (30/10/2026)

## Problema abordado
SKY ya incluía \`sky_reflective_core\` para memorizar las pruebas del Skill
Builder, pero el módulo \`sky_verified_roles\` no compartía información sobre
los errores de herramientas especializadas entre ejecuciones.

Este bloque agrega **memoria categórica separada** para las operaciones
comprobadas de matemáticas, datos, física, química, educación, programación,
seguridad e investigación.

## Funcionamiento real
1. Antes de cada herramienta, SKY revisa si existe una lección basada en
   fallos anteriores de esa combinación exacta de rol y herramienta.
2. Ejecuta la herramienta bajo los mismos permisos actuales.
3. La verificación numérica conserva un máximo de dos intentos.
4. Clasifica el resultado en un vocabulario cerrado: input inválido,
   permiso necesario, dependencia indisponible, discrepancia del verificador
   o fallo de ejecución.
5. Guarda en SQLite solamente rol, herramienta, estado, categoría, intentos,
   duración y fecha. Una consulta posterior puede recibir recomendaciones
   operativas sobre el fallo típico. No guarda prompts, archivos, errores
   textuales, rutas, contraseñas ni tokens. Retención de 90 días y 2000
   observaciones.

\`prior_lesson\` es **consultivo**: no cambia automáticamente los argumentos,
no instala dependencias, no modifica código y no permite acciones de dispositivo.
La recuperación no prueba por sí sola que la próxima operación tenga éxito.

## API propia
GET \`/api/sky/verified-roles/learning\` (autenticación SKY existente)

La respuesta ofrece estadísticas por rol/herramienta, tasa de verificación
local, fallos clasificados e intentos repetidos. Distingue
\`RETRIEVED_UNVERIFIED\` de \`VERIFIED_LIMITED_SCOPE\`.

## Comprobación
CI \`sky-verified-roles.yml\` ejecuta las suites científicas previas más
\`test_sky_role_lessons.py\`. Las pruebas deben demostrar que:
- un fallo previo produce lección visible en la siguiente ejecución;
- fallos del revisor agotan los reintentos y detienen planes;
- rechazos de permisos nunca activan red;
- un secreto en los argumentos no se guarda en SQLite;
- expiración y categorías restringidas funcionan correctamente.

## Limitaciones
Esta memoria no sustituye la memoria reflexiva del Skill Builder y tampoco
actualiza pesos del modelo. La mejora es trazabilidad y asesoría verificable.
La validación en el teléfono Android físico, el servidor de casa y la
sincronización de memoria continúan pendientes. No se modifica la APK.
