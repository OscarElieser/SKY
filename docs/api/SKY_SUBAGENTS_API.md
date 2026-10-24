# SKY Subagent Manager — API de subagentes (propuesta funcional de SKY)

**Alcance:** creación de subagentes especializados *dentro de la API y el motor existentes* de SKY. No reemplaza `sky_workflows`, `sky_agent`, la interfaz holográfica, ni `SKY CORE`.

## Qué existe en esta rama

- Perfiles persistentes en SQLite con nombre, misión, especialidad, estado y capacidad permitida.
- Especialidades operativas admitidas de `sky_workflows.ROLE_ACTION`: `planificador` → `plan`; `documentalista` → `document`; `diseñador` → `experience`; `creador_3d` → `world`; `memoria` → `memory`.
- El propietario puede crear, activar, consultar historial y desactivar desde `/flows` → **Mis subagentes**.
- Una delegación es un workflow de un paso, pendiente de aprobación; **no ejecuta nada hasta que el propietario apruebe el flujo**.
- La ejecución de una tarea aprobada reutiliza SKY Workbench, validación de pasos, reintentos y registro de resultados ya existentes. No se agregan comandos de shell, pagos ni privilegios nuevos.
- `SKY_SUBAGENTS_DB` (opcional) define la ruta SQLite; defecto `local_data/sky_subagents.sqlite3`.
- Por seguridad, un subagente creado inicia desactivado. No crea otros subagentes; solo propietario autenticado puede crear.
- Límites: 60 perfiles, 5 flujos activos/pendientes por subagente, 30 delegaciones cada 24 horas.
- Desactivar bloquea **nuevas delegaciones**. No cancela automáticamente flujos ya aprobados; el propietario los cancela en Seguimiento para evitar pérdidas de trabajo.

## Endpoints, todos con `X-SKY-KEY` y MFA cuando esté habilitado

| Método | Ruta | Función |
|---|---|---|
| GET | `/api/sky/subagents/catalogue` | Roles permitidos, políticas y límites |
| POST | `/api/sky/subagents` | Crear perfil desactivado (`name`, `mission`, `role`) |
| GET | `/api/sky/subagents` | Listar perfiles |
| GET | `/api/sky/subagents/{id}` | Detalle y permiso real |
| POST | `/api/sky/subagents/{id}/enable` | Activar delegación manual |
| POST | `/api/sky/subagents/{id}/disable` | Impedir futuras delegaciones |
| POST | `/api/sky/subagents/{id}/delegate` | Preparar tarea (`task`, `params`, `project_id?`) |
| GET | `/api/sky/subagents/{id}/delegations` | Historial con estado del workflow |

### Ejemplo: crear un subagente académico

Petición autenticada del propietario:

```json
{
  "name": "SKY Investigador",
  "mission": "Planificar investigaciones educativas con fuentes verificadas",
  "role": "planificador"
}
```

La API devuelve un identificador `sub_...` y `enabled: false`. Al activarlo, el dueño puede delegar:

```json
{
  "task": "Diseñar un plan para investigar metodologías educativas inclusivas",
  "params": {}
}
```

La respuesta incluye `workflow_id`, `status: awaiting_approval` y `preview_url`.
Para ejecutar, el usuario visita `GET /api/sky/workflows/{id}/preview` y aprueba en el panel (API `POST /api/sky/workflows/{id}/approve` con `expected_fingerprint`).

**La misión es metadato informativo**, no un prompt privilegiado. Un nombre como «Administrador» no entrega permisos de administrador. El rol permitido determina las herramientas.

## Limitaciones reales

Este primer incremento **no es** un entorno de agentes que decidan por sí solos, naveguen libremente, creen ejecutores programables, cambien modelos o funcionen permanentemente cuando SKY está apagada. Los roles ejecutables son los cinco existentes; habilidades futuras deben integrarse individualmente con pruebas, límites y permisos.

Los pasos de creación de documentos requieren contenido real; no basta pedirle al subagente «inventá todo». El acceso a internet, a repositorios o a cuentas se integra únicamente mediante herramientas autorizadas de SKY, nunca añadiendo poderes a este registro de perfiles.

Para evolucionar a subagentes con razonamiento avanzado y cooperación real:
1. Añadir contratos de capacidad por Skill con pruebas de seguridad, proveedor/costo y datos permitidos.
2. Incorporar un **supervisor** para dividir tareas, coordinar subagentes y fusionar resultados.
3. Asignar presupuestos, tiempos de ejecución, límites de tokens, y acceso mínimo por tarea.
4. Incorporar agentes IA externos solo como razonadores; acciones se ejecutan por la API de SKY.
5. Seguir requiriendo aprobaciones explícitas antes de acciones externas o irreversibles.
6. Probar en Windows, web y móviles por separado sin declarar compatibilidad no verificada.

## Verificación
`tests/test_sky_subagents.py` cubre autenticación, permisos, persistencia, roles, límites y delegaciones sin ejecución automática. La prueba está integrada en CI de seguridad y Windows; antes de fusionar verificar que el SHA final tenga las comprobaciones verdes.

**Importante:** no confundir `SKY_SUBAGENTS_DB` con el motor de workflow `SKY_WORKFLOWS_DB`. Las definiciones van a la primera base; los trabajos se guardan en la segunda, que ya dispone de su propio sistema de recuperación.
