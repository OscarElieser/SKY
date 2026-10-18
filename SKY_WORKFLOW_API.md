# SKY v9.3 — Autonomous Workflow Engine API

Base: `http://127.0.0.1:8765`.

Todas las rutas siguientes requieren encabezado **`X-SKY-KEY`** con la clave administrativa de tu instalación. Los tokens `Authorization: Bearer` de cuentas sociales **no** sirven para estas rutas.

| Método | Ruta | Acción |
|---|---|---|
| GET | `/api/sky/workflows/catalogue` | Agentes disponibles y acciones locales permitidas |
| GET | `/api/sky/workflows/status` | Conteo de flujos y estado del motor |
| POST | `/api/sky/workflows` | Crear flujo (`awaiting_approval`) |
| GET | `/api/sky/workflows` | Listar flujos del propietario |
| GET | `/api/sky/workflows/{id}` | Leer un flujo y resultados |
| GET | `/api/sky/workflows/{id}/events` | Bitácora de eventos |
| POST | `/api/sky/workflows/{id}/approve` | Aprobar con `{"approve":true}` |
| POST | `/api/sky/workflows/{id}/cancel` | Cancelar flujo que no esté ejecutándose |
| POST | `/api/sky/workflows/{id}/retry` | Reintentar tras revisión explícita |
| GET | `/api/sky/owner/baqueano` | Datos mínimos del panel BAQUEANO solo creador |

## Ejemplo de flujo de dos pasos

```json
{
  "name": "Plan y documento para mi curso",
  "project_id": null,
  "steps": [
    {
      "agent": "planificador",
      "action": "plan",
      "task": "Preparar un plan educativo de tecnología e innovación",
      "params": {}
    },
    {
      "agent": "documentalista",
      "action": "document",
      "task": "Elaborar un documento sobre metodologías activas",
      "params": {
        "document": {
          "kind": "docx",
          "title": "Metodologías activas",
          "content": "# Plan de trabajo\nObjetivos, contenidos y actividades verificables."
        }
      }
    }
  ],
  "run_at": null,
  "interval_minutes": null
}
```

Ejemplo con cURL para crear (sustituí el token solo en tu equipo, jamás lo publiques):

```bash
curl -X POST http://127.0.0.1:8765/api/sky/workflows \
  -H "X-SKY-KEY: $SKY_API_KEY" \
  -H 'Content-Type: application/json' \
  --data @mi_flujo.json
```

Una respuesta 201 **no ejecuta nada**: el nuevo flujo queda `awaiting_approval`. La aprobación es independiente y necesita `POST /api/sky/workflows/{id}/approve` con `{"approve":true}`. Una vez aprobado, SKY lo ejecutará cuando corresponda mientras el servidor esté activo.

## Estados

`awaiting_approval` → `scheduled` → `running` → `scheduled` (pasos restantes) → `completed`.

También existen `retry_wait` (solo tareas idempotentes), `failed`, `needs_review` (efecto potencialmente ambiguo, revisión antes de reintentar) y `cancelled`.

Los flujos recurrentes retornan a `scheduled` al completar cada ciclo, conservando un historial limitado de resultados y manteniendo su aprobación original. Para cancelar próximos ciclos usá la ruta de cancelación.

## Permisos e idempotencia

- Los agentes están vinculados 1:1 a operaciones concretas: `planificador/plan`, `creador_3d/world`, `diseñador/experience`, `documentalista/document`, `memoria/memory`.
- Sin soporte para ejecutar comandos del sistema, herramientas descubiertas dinámicamente, pagos, control remoto ni publicaciones externas.
- El registro `work_item` de cada paso se conserva para prevenir la duplicación de pasos terminados después de un reinicio.
- Un `work_item` cuyo resultado quedó ambiguo detiene el flujo; la confirmación del reintento de acciones con efectos requiere `{"acknowledge_partial_effects":true}`.
- Los documentos periódicos, mundos 3D y recuerdos requieren un intervalo de al menos 60 minutos.
- Para exportaciones de archivos desde los resultados, usá `/api/sky/files/{work_item_id}` con la misma clave.

El motor no reentrena modelos neuronales ni crea herramientas nuevas por sí mismo. Sus capacidades son las implementadas y probadas dentro de SKY Workbench.

## SKY v9.4 — Continuidad supervisada

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/api/sky/workflows/{id}/preview` | Pasos detallados y huella SHA-256 del plan para autorización |
| POST | `/api/sky/workflows/{id}/pause` | Detener el siguiente paso mientras el flujo esté entre tareas |
| POST | `/api/sky/workflows/{id}/resume` | Reanudar un flujo previamente aprobado y pausado |
| GET | `/api/sky/projects/{id}/continuity` | Estado de flujos, progreso y entregables enlazados del proyecto |

La ruta `/approve` admite `{"approve":true,"expected_fingerprint":"<SHA-256 entregado por preview>"}`. Sigue siendo válida la aprobación heredada sin `expected_fingerprint` para clientes antiguos, pero **la interfaz v9.4 utiliza siempre la huella**.

Un paso posterior puede utilizar `{{project.title}}`, `{{project.description}}` y `{{step.1.world_id}}`, `{{step.1.name}}`, `{{step.1.plan_summary}}`, etc. Solo puede referirse a resultados de pasos anteriores **de la misma ejecución recurrente**. Si un campo no existe, el flujo falla y registra el error en vez de inventar datos. El contexto del proyecto queda congelado al crear el flujo para evitar cambios silenciosos.

Pausa y reanudación se permiten solamente entre pasos; una tarea en ejecución no es interrumpida a la mitad. Las nuevas columnas SQLite se migran sin eliminar los datos de v9.3. Las rutas requieren la clave administrativa `X-SKY-KEY`.
