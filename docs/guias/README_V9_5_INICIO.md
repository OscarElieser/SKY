# SKY IA v9.5 — Intelligent Workspace

**Visión y promoción del proyecto: Oscar Elieser Chamorro Guzmán.** La documentación de autoría es una declaración de proyecto, no un registro oficial de marca o propiedad intelectual.

## Novedad comprobable

La portada principal sigue siendo minimalista. El creador, al ingresar con la **clave maestra SKY**, puede solicitar en la conversación: «Crea mi proyecto completo de academia virtual». El coordinador SKY Intelligent Workspace prepara un plan estructurado que reúne los módulos preexistentes. No ejecuta automáticamente el mensaje: muestra una **vista previa de las etapas** y pide aprobación antes de iniciar el flujo.

Con la aprobación explícita, el motor v9.4 ejecuta tareas locales mientras el servidor permanezca encendido, con seguimiento en la misma conversación. Al terminar, el propietario puede descargar sus entregables (documentos editables, diseños HTML y mundos GLB) desde el propio chat. La petición, la referencia del proyecto y el flujo persisten en SQLite. Un trabajo interrumpido se recupera de forma conservadora: operaciones ambiguas requieren revisión y no se duplican automáticamente.

Los resultados son reales pero tienen un **alcance inicial limitado**: el mundo 3D es procedural, el diseño HTML es una plantilla editable y el documento constituye un primer borrador derivado de las instrucciones; el sistema **no realiza investigación especializada ni generación fotorrealista completa sin motores adicionales**. No se inventan datos financieros. Una solicitud de Excel sin datos tabulares se rechaza, indicando al usuario que debe aportar filas desde Office Studio.

## Instalación

1. Instalá Python 3.11 o 3.12. Extraé este ZIP en una carpeta nueva, sin sobrescribir la versión previa.
2. Instalá las dependencias según `requirements.txt`; en Windows ejecutá `INICIAR_SKY_V9_WINDOWS.bat` o en Linux/macOS `bash iniciar_sky_v9_linux_mac.sh`.
3. Abrí `http://127.0.0.1:8765/sky` y elegí **Acceso privado**. Si no definiste `SKY_API_KEY`, SKY creará un token local en `local_data/sky_api_token.txt`.
4. En el chat escribí «Crea mi proyecto completo de academia educativa con metaverso». Revisá las etapas y pulsá **Aprobar y crear proyecto**.
5. El seguimiento aparece debajo del chat y se actualiza mientras el servidor está abierto. Descargá archivos individuales o el ZIP del proyecto. Podés seguir conversando, seleccionar «Continuar este proyecto» o acceder a los módulos avanzados desde «Espacios».

## Migración desde SKY v9.4

1. **Detené SKY v9.4.** Guardá una copia externa de `local_data/`, de las salidas de archivos y de `.env`.
2. Instalá v9.5 en una carpeta nueva y copiá los datos privados únicamente con el servidor detenido. Nunca publiques `.env` ni claves maestras en el repositorio.
3. Ejecutá `python sky_preflight.py --json`; iniciá el servidor y verificá que tus mundos, proyectos y automatizaciones anteriores sigan disponibles.
4. El módulo v9.5 añade **una base de datos nueva**, `local_data/sky_intelligent.sqlite3`; no reemplaza las bases existentes. La utilidad `python sky_backup.py` ahora la incluye en el respaldo extendido.
5. Conservá la copia de v9.4 hasta terminar la validación de tus trabajos.

## Seguridad y disponibilidad

- Las rutas `/api/sky/intelligent/*` requieren la clave del creador; un usuario de comunidad no obtiene acceso a proyectos o BAQUEANO administrativos.
- Solo la posesión de la clave confirma permisos en esta edición local; una producción pública requerirá cuentas de propietario verificadas, MFA, HTTPS, autorización por recurso, auditorías y copias remotas.
- Las acciones que crean archivos/mundos necesitan aprobación explícita. Esta versión no ejecuta comandos arbitrarios, pagos, transacciones, despliegues ni cambios de BAQUEANO.
- Los borradores y contextos de proyectos **no salen hacia modelos externos** al elaborar el flujo. El chat puede usar IA externa únicamente si el propietario selecciona un proveedor, con las opciones existentes de compartir contexto.
- El planificador de tareas permanece activo **solo mientras SKY y su servidor funcionen**. Las conexiones con cámara, audio, proveedores externos y muchos usuarios no se certifican con esta prueba.
- Para uso continuo por una comunidad mundial hacen falta pruebas de carga, una base de datos de producción, colas robustas, observabilidad, escalado y arquitectura multiusuario revisada.

## Comprobaciones reproducibles

```bash
python -m pytest -q
python sky_preflight.py --json
node --check metaverse/static/sky-home.js
```

Se probaron **154 casos automatizados** en el entorno de trabajo. Se ejecutó además una validación HTTP real con un servidor Uvicorn, scheduler activo y exportación de Word, HTML y GLB; hay evidencias JSON en `ejemplos/sky_v9_5/VALIDACION_HTTP_REAL.json`. La interfaz se comprobó en Chromium con las peticiones reenviadas a la API real mediante un transporte controlado, ya que el navegador del entorno bloquea conexiones directas a `localhost`. **No equivale a una certificación de producción.**

Documentación adicional: `SKY_INTELLIGENT_WORKSPACE_API.md`, `CHANGELOG_V9_5.md` y `VALIDACION_V9_5.md`.
