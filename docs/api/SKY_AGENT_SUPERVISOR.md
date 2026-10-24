# SKY Agent Supervisor — coordinación multiagente automática

**Proyecto:** SKY API original, compatible con `SKY CORE`, `sky_workflows`, `sky_workbench` y el HUD. Esta implementación es **automática en el reparto del trabajo**, pero **no concede autonomía ilimitada**: el propietario aprueba cada flujo antes de ejecutar acciones.

## Arquitectura comprobable

```text
Usuario (voz/chat/panel) → SKY CORE → SKY Agent Supervisor
                                   ├─ analizar intención y capacidades reales
                                   ├─ dividir hasta 8 tareas y asignar roles
                                   ├─ comprobar entradas y políticas
                                   └─ crear Workflow [awaiting_approval]
                                     ↓ aprobación explícita del propietario
                      SKY Workflows (SQLite + scheduler existente)
                           ├─ Planificador → plan
                           ├─ Documentalista → document
                           ├─ Diseñador → experience
                           ├─ Creador 3D → world
                           └─ Memoria → memory
                                     ↓
                            SKY Workbench (acciones reales)
                                     ↓
                      Estado + artefactos + errores + recibos
                                     ↓
                             SKY responde al propietario
```

**No son cinco modelos nuevos en ejecución constante.** Son ejecutores internos disponibles mientras el servicio SKY está activo. SKY conserva la única interfaz conversacional. Una vez aprobado el workflow, el scheduler existente ejecuta pasos automáticamente y deja resultados persistentes en SQLite. No funciona cuando SKY está apagada.

### API autenticada

| Método | Endpoint | Función |
|---|---|---|
| GET | `/api/sky/supervisor/catalogue` | Información de roles, límites y restricciones |
| POST | `/api/sky/supervisor/analyze` | Descomponer solicitud sin crear ni ejecutar trabajo |
| POST | `/api/sky/supervisor/prepare` | Crear workflow pendiente de aprobación |
| GET | `/api/sky/supervisor/jobs/{workflow_id}` | Resumen real de pasos completados, errores y artefactos |

Se reutilizan estas rutas de SKY:
- `GET /api/sky/workflows/{id}/preview`: descripción y `fingerprint` de la orden concreta.
- `POST /api/sky/workflows/{id}/approve` con `{"approve":true,"expected_fingerprint":"..."}`: autorización explícita.
- `GET /api/sky/workflows/{id}/events`: auditoría.
- `POST /api/sky/workflows/{id}/pause`, `resume`, `cancel`: control de tareas entre pasos.

Ninguna ruta de supervisor se publica sin `require_key` y el segundo factor habilitado en SKY.

### Ejemplo de entrada

```json
{
  "request": "Creá una presentación y diseñá una interfaz sobre este contenido",
  "source_text": "# Tema\nDescripción completa proporcionada por el dueño...",
  "document_format": "pptx",
  "request_id": "presentacion-2026-001"
}
```

SKY asigna automáticamente Planificador, Documentalista y Diseñador. El flujo queda en `awaiting_approval`, sin ejecutar. Cada tarea se verifica contra las capacidades existentes. El planificador pasa su `plan_summary` al siguiente rol mediante una referencia `{{step.1.plan_summary}}`, resuelta por SKY Workflows. La referencia sirve como **contexto de la tarea**, no reemplaza el texto real del documento. El supervisor no inventa fuentes ni datos para completarlo.

`request_id` es opcional; si se repite con datos idénticos, se recupera el workflow previo en lugar de crear otro. Si cambia el contenido, se rechaza como conflicto.

### Uso mediante SKY, no mediante aplicaciones separadas

Desde texto o voz:
- «SKY, coordiná diseñar una interfaz educativa».
- «SKY, delegá crear un informe usando este contenido» (requiere `source_text` en la llamada o el panel).
- «SKY, organizá preparar un mundo 3D sobre un museo».

La API `/api/asistente/mensaje` y la transmisión `/api/asistente/stream` interceptan únicamente estos pedidos explícitos. La respuesta sigue siendo de **SKY** (`atendido_por: SKY`), con el `workflow_id` y explicación del estado, no una falsa confirmación de ejecución.

Para material extenso o archivos de referencia, usar la sección **SKY Agent Supervisor** dentro de `/flows`: proporciona descripción, texto de referencia y formato, muestra el reparto de roles y permite preparar el trabajo. Después se aprueba en Seguimiento.

### Estados y evidencia

El resultado en `/api/sky/supervisor/jobs/{id}` incluye:
- `status`: `awaiting_approval`, `scheduled`, `running`, `completed`, `failed`, `needs_review` y estados equivalentes del motor.
- `completed_steps` y `total_steps` tomados de los resultados de Workflows.
- `results[]`: rol, acción, identificador de trabajo y resultado real del Workbench.
- `verified_complete`: solamente `true` cuando el workflow está completado y todos los pasos tienen resultados.
- `last_error`: error real si se produjo.

La cancelación o pausa se aplica entre pasos, siguiendo la política del motor actual; no garantiza interrumpir una escritura ya iniciada.

### Límites presentes y trabajo posterior

Esta versión aplica **descomposición determinista por intención**, con reglas verificables (documentos, diseño, 3D, memoria y planificación). No afirma que sea un planificador LLM general o que use automáticamente modelos externos.

La investigación web con fuentes, pagos, acciones de terminal, despliegues y operaciones destructivas no se incorporan al motor sin un ejecutor específico autorizado. Si la solicitud depende de esas capacidades, SKY registra un **bloqueo** (`needs_input`) y explica exactamente qué falta. Para documentos requiere material original; para hojas de cálculo requiere datos tabulares.

Para una versión avanzada futura: selección de modelos por especialidad, supervisor con razonamiento dinámico y validación por contrato, planificación con DAG de dependencias, cotas de tokens/costos/tiempo, paralelismo limitado, verificación semántica independiente de cada entregable y separación de memoria por proyecto. Esas capacidades NO están implementadas por el simple hecho de diseñarlas.

### Pruebas

`tests/test_sky_supervisor.py` valida la autenticación, reparto automático, bloqueos, confirmación del propietario, traspaso de resultados, archivo real generado, idempotencia y consulta del resultado.

La ruta nueva también está registrada en las comprobaciones Linux y Windows de GitHub Actions. Una ejecución satisfactoria de CI no sustituye una prueba de interfaz y voz en la PC del propietario. **No fusionar a main hasta validar el último commit y la prueba local.**
