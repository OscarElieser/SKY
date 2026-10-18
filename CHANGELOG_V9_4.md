# SKY IA v9.4 — Continuidad y autonomía supervisada

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

## Cambios efectivos sobre v9.3

- **Continuidad verificable entre pasos:** referencias como `{{step.1.world_id}}`, `{{step.1.name}}`, `{{step.1.plan_summary}}` y `{{project.title}}` se resuelven desde entregables ejecutados, no de texto inventado. No admiten consultas a secretos, referencias futuras ni llamadas a internet.
- **Contexto aprobado e inmutable:** al crear un flujo vinculado a un proyecto se guarda una instantánea de su título, descripción y versión. Una edición posterior del proyecto no modifica el contenido ya aprobado. Las bases v9.3 se migran automáticamente mediante nuevas columnas, sin borrar trabajos.
- **Previsualización y huella SHA-256:** `GET /api/sky/workflows/{id}/preview` devuelve los pasos, referencias, posibles escrituras y huella del plan. El cliente incluye la huella al aprobar; si no coincide, recibe error 409. La aprobación sigue requiriendo la clave del propietario.
- **Pausa/reanudación entre pasos:** endpoints nuevos `/pause` y `/resume`. Una operación que ya está ejecutándose no se cancela abruptamente ni se pausa a mitad de una escritura.
- **Continuidad por proyecto:** `GET /api/sky/projects/{id}/continuity` reúne los entregables enlazados, los flujos, los progresos y los errores. No expone mensajes ni notas privadas en el resumen.
- **UI avanzada:** controles de revisión, aprobación, pausa, reanudación y resumen de proyecto añadidos dentro de `/flows`. La portada `/sky` sigue minimalista; BAQUEANO permanece accesible solo con clave administrativa.
- **Plan local estructurado reutilizable:** la herramienta `plan` ahora produce `plan_summary`, que puede incorporarse a un DOCX posterior. Es una estructura determinista, no un análisis LLM oculto.
- **Trazabilidad:** el registro de cada paso conserva una huella del texto de entrada resuelto sin almacenar su contenido en el evento.

## Qué se conservó

Toda la base v9.3: comunidad, metaverso, voz, multia-IA opcional, Studio 3D, Office Studio, Project Hub, catálogo de agentes, bases persistentes, API y Control Center BAQUEANO privado. No se realizó ningún cambio de producción en BAQUEANO.

## Validaciones reproducibles

- `python -m pytest -q` → **146 pruebas superadas** (v9.3 y anteriores más 6 nuevas).
- `node --check metaverse/static/sky-flows.js` → sintaxis correcta.
- `python sky_preflight.py --json` → diagnóstico local operativo en el entorno utilizado.
- Prueba sobre **servidor Uvicorn real**: crear proyecto → plan → mundo 3D → DOCX usando el ID del mundo → experiencia HTML → exportar ZIP con archivos reales (`ejemplos/sky_v9_4/`). Se comprobó aprobación errónea rechazada, pausa, reanudación y endpoint exclusivo del propietario.
- **Prueba visual del navegador no completada**: Chromium del entorno bloquea abrir servidores locales y el origen de prueba. No se certifican interfaces en producción.

## Límites y riesgos actuales

Trabajos automáticos requieren que el proceso local permanezca activo. SQLite y Uvicorn de un proceso no son infraestructura para millones de usuarios. No se han certificado Chrome móvil, dispositivos físicos, servicios externos, WebXR, despliegue de BAQUEANO ni funcionamiento continuo con carga alta. Referencias permitidas contienen únicamente campos seleccionados de resultados estructurados, nunca el archivo binario ni recuerdos privados ajenos.
