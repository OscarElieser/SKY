# SKY IA v9.3 — Registro de cambios

**Visión y autoría conceptual: Oscar Elieser Chamorro Guzmán.**

## Interfaz y experiencia

- Nueva portada minimalista (`/`, `/sky`) para evitar decenas de elementos visibles al abrir SKY.
- Conversación central, voz en navegadores compatibles y acceso a capacidades desde «Espacios».
- Experiencia responsive adaptada a escritorio y móvil.
- Metaverso 3D anterior conservado en `/world`; comunidad y panel Studio siguen disponibles.
- SKY Studio y Office Studio conservan las funciones que ya tenían; v9.3 no los reconstruye.

## Privacidad y BAQUEANO

- El enlace a Control Center BAQUEANO se construye únicamente tras comprobar una clave maestra correcta.
- Nuevo panel privado `/owner/baqueano` con nueva comprobación de la clave antes de leer datos.
- Nueva ruta `/api/sky/owner/baqueano` protegida con `X-SKY-KEY`. Una cuenta social no obtiene acceso.
- No hay credenciales administrativas ni tokens de BAQUEANO en el frontend o el ZIP.
- Sin acciones sobre el sitio público o repositorio de BAQUEANO en producción.

## SKY Autonomous Workflow Engine

- Nuevo módulo `neural_core/sky_workflows.py`, con estado y eventos SQLite persistentes.
- Nuevas rutas `metaverse/workflow_api.py` autenticadas.
- Motor asíncrono de ejecución local en el ciclo de vida del servidor FastAPI, sin base de datos en memoria.
- Agentes locales con catálogo fijo de funciones Workbench; creación de documentos/mundos/diseños/planes/notas.
- Aprobación, programación por fecha o intervalo, registro de resultados y asociación con Project Hub.
- Operaciones ambiguas tras interrupción requieren revisión humana para prevenir duplicados.
- Respaldo ampliado para incluir proyectos y workflows.

## Compatibilidad

- 140 pruebas pasan (131 anteriores y 9 nuevas).
- El contrato de estado de Integration Center conserva `version=9.2.0` por retrocompatibilidad e informa `platform_version=9.3.0`.
- Los viejos módulos no fueron sustituidos, y los nuevos artefactos se guardan con IDs existentes de SKY.
- La URL `/` ahora muestra SKY Inicio; para el antiguo mundo tridimensional usar `/world`.

## Pendientes que no afirmamos terminados

- Despliegue público, alta disponibilidad, miles de usuarios, pruebas de carga, VR físico, llamadas reales a proveedores externos.
- Identificación legal del titular con MFA: v9.3 usa clave maestra local como permiso técnico, no verificación civil.
- Automatizaciones entre servicios terceros / BAQUEANO publicadas; hoy solo acciones locales auditadas.
