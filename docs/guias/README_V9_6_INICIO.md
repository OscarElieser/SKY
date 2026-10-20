# SKY IA v9.6 · Contextual Coordination

**Visión, autoría conceptual y promoción del proyecto:** Oscar Elieser Chamorro Guzmán.

Esta versión conserva el código de SKY v9.5 y agrega **contexto, revisión del plan y edición de entregables** desde la conversación privada del creador. La portada continúa sencilla y BAQUEANO sigue dentro del acceso privado del creador. No se han desplegado cambios en baqueanonicaragua.com.

## Instalación

1. Descomprimí el ZIP en una **carpeta nueva**. Necesitás Python 3.11 o 3.12 (no está certificada otra versión).
2. Ejecutá `INICIAR_SKY_V9_WINDOWS.bat` en Windows o `bash iniciar_sky_v9_linux_mac.sh` en Linux/macOS, según los requisitos de tu equipo.
3. Abrí `http://127.0.0.1:8765/sky` y seleccioná **Acceso privado**. Si no configuraste `SKY_API_KEY` en tu `.env`, SKY generará un token local en `local_data/sky_api_token.txt`.
4. Indicá el objetivo desde la conversación, por ejemplo: «Crea un proyecto completo para una academia virtual de historia y cultura con materiales».
5. **Antes de aprobar**, elegí «Editar este plan» y explicá qué agregar o retirar. Confirmá únicamente cuando revisés el resumen de etapas.
6. Durante la ejecución, SKY guarda el trabajo en SQLite. Al terminar, cada entregable ofrece una opción para crear **una nueva versión** sin eliminar la anterior. Descargá el ZIP del proyecto desde el chat.

## Contexto y tipo de resultado

- Interpretación local de órdenes frecuentes, normalización de tildes y verbos de creación. **No es comprensión universal**; solicitudes ambiguas o especializadas pueden requerir aclaración.
- Los borradores Word, PowerPoint y PDF incorporan destinatarios y ejes **solo cuando el usuario los especifica**, y reflejan pendientes de validación. No se inventan datos, estudios ni referencias.
- Para crear Excel desde el chat, debés proporcionar un CSV explícito con encabezados y filas, por ejemplo:

  ````text
  Crea un Excel de gastos con mis datos:
  ```csv
  Concepto,Monto
  Transporte,180
  Materiales,75
  ```
  ````

- Los mundos siguen siendo **procedurales** y los diseños web son **plantillas editables**; no representan generación fotorrealista ni reconstrucción geométrica completa.
- Las nuevas versiones de documentos anexan las instrucciones de revisión; los diseños y mundos se regeneran con los cambios solicitados. No se sobrescriben los artefactos originales, ni se promete edición semántica exhaustiva del contenido.
- Las revisiones de CSV/XLSX existentes se realizan mediante Office Studio para preservar fórmulas y datos originales.

## Seguridad

Las rutas de coordinación requieren **`X-SKY-KEY` de creador**. Las sesiones sociales no pueden gestionar sus proyectos, revisiones ni BAQUEANO. No se ejecuta ningún plan ni revisión sin autorización explícita con su huella SHA-256 actual. Una operación interrumpida después de adquirir permiso pasa a revisión conservadora en vez de repetirse automáticamente. No hay ejecución libre de shell, transacciones, pagos, cambios de BAQUEANO ni despliegues automáticos.

**Nota:** El modo propietario local se autentica con la posesión de una clave, no con verificación legal ni MFA. Para publicar un servicio multiusuario son imprescindibles permisos de propiedad, HTTPS, MFA, monitoreo, límites y pruebas de carga.

## Migrar desde v9.5

1. Detené SKY y respaldá `local_data/`, archivos generados y `.env` en una ubicación privada.
2. Conservá la versión anterior. Instalá v9.6 en otra carpeta y **copiá los datos personales solo con el servidor apagado**.
3. Ejecutá `python sky_preflight.py --json` e iniciá SKY. La base `sky_intelligent.sqlite3` agrega `intelligent_revisions` mediante creación compatible; no elimina ni sustituye tablas preexistentes.
4. Verificá mundos, proyectos, documentos y la identidad de tu propietario. Usá `python sky_backup.py` para respaldos consistentes con documentos.
5. No publiques `.env`, `local_data/` ni claves en repositorios o archivos para compartir.

## Comprobaciones realizadas

- **162 pruebas automatizadas superadas** (154 heredadas y 8 nuevas).
- Prueba con **Uvicorn y HTTP reales**: salud, preparación, edición y autorización, sin errores de API.
- Chromium con HTML/CSS/JS reales de SKY y un transporte de pruebas puente a la API HTTP real (el navegador del entorno bloquea conexiones directas a localhost): inicio del creador, solicitud, edición del plan y nueva propuesta, sin errores de JavaScript.
- Generación de proyecto real: mundo GLB, diseño HTML, documento Word original y revisión, descargables juntos en ZIP.
- Render de documento Word de ejemplo a páginas para inspección de layout. No hay conexión probada con proveedores de IA externos en estas pruebas.

Documentos: `CHANGELOG_V9_6.md`, `VALIDACION_V9_6.md`, `SKY_CONTEXTUAL_API.md`.
