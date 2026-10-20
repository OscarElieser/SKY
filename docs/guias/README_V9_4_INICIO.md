# SKY IA Universal v9.4 — Instalación y continuidad

**Proyecto conceptual y visión: Oscar Elieser Chamorro Guzmán.** Esta entrega es código de aplicación local real, con funcionalidades y pruebas documentadas; no constituye una plataforma pública lista para operar a escala mundial.

## Inicio rápido

1. Instalá Python 3.11 o 3.12; v9.4 se ha probado también en Python 3.13 en el entorno de desarrollo, pero no certifica compatibilidad universal.
2. Extraé el ZIP en una carpeta **nueva**. No mezcles archivos de v9.3 copiándolos sobre la carpeta anterior.
3. Windows: `INICIAR_SKY_V9_WINDOWS.bat`. Linux/macOS: `bash iniciar_sky_v9_linux_mac.sh`.
4. Abrí `http://127.0.0.1:8765/`. La portada sigue teniendo solo el chat, la voz y el acceso a «Espacios».
5. Dentro de «Espacios», abrí **Automatizaciones** (`/flows`) e introducí la clave privada del creador; si usás el token generado automáticamente, estará en `local_data/sky_api_token.txt`.
6. Para crear proyectos y diseñar, abrí `/studio`; para archivos Office, `/office`; para metaverso, `/world`.

## Hacer un proceso con continuidad real

1. En **SKY Project Hub**, creá un proyecto, por ejemplo «Museo interactivo».
2. En **Automatizaciones**, elegí ese proyecto y añadí un paso «Crear mundo 3D».
3. Añadí otro paso «Crear documento Word» y utilizá estas referencias en el contenido:

```text
# Guía de {{project.title}}
Mundo creado: {{step.1.name}}
ID del mundo: {{step.1.world_id}}
```

4. Pulsá «Preparar flujo para aprobación». No ejecuta nada aún.
5. En seguimiento, elegí «Revisar y autorizar»: leé los pasos de la vista previa y aprobá la huella del plan.
6. SKY ejecuta las tareas aprobadas al llegar su turno mientras el servidor siga encendido. Podés pausarlo **entre pasos** y reanudarlo después.
7. Elegí el proyecto y pulsá «Ver resumen». Los entregables también están disponibles en Project Hub y pueden exportarse en un ZIP.

**Referencias admitidas:** `{{project.title}}`, `{{project.description}}` y `{{step.N.campo}}` cuando `N` es un paso anterior y `campo` pertenece a `kind`, `world_id`, `name`, `title`, `file_name`, `download`, `id`, `message`, `label` o `plan_summary`. Los campos ausentes detienen la tarea; SKY no inventa información. Una referencia `project.*` requiere elegir un proyecto.

## Actualización segura desde v9.3

1. Detené SKY v9.3; hacé respaldo completo de `local_data`, tus salidas y `.env` privado.
2. Extraé v9.4 en otra carpeta, y con el servidor apagado copiá solo tus **datos privados** (`local_data`, salidas y `.env`) desde v9.3. No publiques claves.
3. Ejecutá `python sky_preflight.py --json`, seguido de `python -m pytest -q` si tenés el entorno de desarrollo.
4. Iniciá SKY v9.4. La primera conexión a la base de flujos añade dos columnas nuevas, `pause_requested` y `project_snapshot`; no elimina flujos antiguos.
5. Los flujos v9.3 ya aprobados que no tenían contexto congelado mantienen compatibilidad heredada y continúan usando la información del proyecto disponible. Si el contexto de ese flujo es sensible, cancelalo o revisalo antes de reanudar.
6. Conservá el respaldo v9.3 hasta comprobar que tus mundos, documentos, proyectos y automatizaciones siguen accesibles.

## Privacidad, permisos y disponibilidad

- Solo el creador que posee la clave maestra puede abrir flujos y resúmenes privados. La cuenta social normal no obtiene acceso a BAQUEANO ni a rutas administrativas.
- Esta clave **no es una prueba de identidad legal**. Para publicar el servicio, agregá autenticación de propietario, MFA, HTTPS, moderación y permisos separados.
- Los flujos solo permiten las cinco acciones locales del Workbench. Sin transferencias, pagos, comandos arbitrarios, despliegues ni cambios silenciosos en BAQUEANO.
- Las referencias entre pasos se guardan en el Workbench como parte del documento o tarea final; nunca pasan a un proveedor externo de IA desde los flujos.
- Para archivos y bases locales, usá `python sky_backup.py` y protegé los respaldos. Los archivos `.env`, `local_data/` y las credenciales no van dentro del paquete público.
- El motor de trabajos no sigue ejecutándose si se apaga el equipo o el servidor. La recuperación está diseñada para detener operaciones de efecto ambiguo y pedir revisión.

## Comprobación

```bash
python -m pytest -q
node --check metaverse/static/sky-flows.js
python sky_preflight.py --json
```

La prueba HTTP integrada y sus evidencias están en `ejemplos/sky_v9_4/`. La automatización de navegación visual quedó bloqueada por políticas del navegador de pruebas; no se declara validada.

Archivos complementarios: `CHANGELOG_V9_4.md`, `SKY_WORKFLOW_API.md`, `VALIDACION_V9_4.md`.
