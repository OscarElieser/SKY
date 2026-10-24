# SKY CORE — Atención central y seis roles internos

## Contrato de producto

**SKY es la única asistente con la que conversa el propietario** (chat, voz y API de asistente). Las herramientas y subagentes NO deben crear interfaces conversacionales paralelas ni atribuirse una respuesta final de forma independiente. SKY interpreta, prepara, distribuye a especialistas autorizados, comprueba el resultado y lo comunica con su propia identidad.

A una solicitud legítima SKY debe:
1. Entenderla y consultar memoria/recursos autorizados.
2. Elegir herramientas o roles internos según las capacidades reales.
3. Proponer un plan cuando tenga varias etapas.
4. Exigir aprobación específica ante tareas con efectos externos, irreversibles o con acceso privado.
5. Ejecutar mediante herramientas reales y registrar estado (SENT no es VERIFIED).
6. Revisar el resultado y presentar respuesta SKY.
7. Si falta un permiso, integración, red o capacidad, informar la limitación y ofrecer un camino concreto. **No inventar ejecuciones ni prometer resolver absolutamente cualquier petición.**

## Los seis roles internos permanentes

| Rol | Responsabilidad | Ejecutor existente |
|---|---|---|
| 1. SKY CORE | Centro de conversación, autenticación, planificación y coordinación | SKY API / asistente |
| 2. Planificador | Planes y estructuras de investigación, sin acceso web implícito | `planificador → plan` |
| 3. Documentalista | Crear documentos desde contenido verificado o aportado | `documentalista → document` |
| 4. Diseñador | Diseños/experiencias del Workbench | `diseñador → experience` |
| 5. Creador 3D | Escenas 3D permitidas por Workbench | `creador_3d → world` |
| 6. Memoria | Guardar notas autorizadas y recuperar contexto permitido | `memoria → memory` |

El componente transversal de seguridad (SKY SENTINEL) debe evaluar todas las acciones. No es un séptimo agente que pueda saltarse controles.

Estos seis son **roles disponibles continuamente mientras SKY está ejecutándose**, no seis LLM o servicios que consumen memoria sin necesidad. Que un rol esté `ready_while_service_running` significa **registrado y seleccionable**, no que haya ejecutado una tarea. Para operar después de reiniciar Windows, el servicio de SKY debe instalarse/autoiniciarse voluntariamente con controles de pausa, permiso, supervisión y recuperación. No hay garantía de actividad si el equipo está apagado o el servicio no tiene conexión.

## API existente extendida

Todas estas rutas usan el sistema **existente** `require_key` y segundo factor si está habilitado.

- `GET /api/sky/internal-roles`: configuración y disponibilidad lógica de SKY + cinco ejecutores internos.
- `POST /api/sky/internal-roles/preview`: valida un plan de varios roles (1 a 8 pasos) usando exactamente los mismos controles que `sky_workflows`. Solo muestra la propuesta, **no crea ni ejecuta**.
- `POST /api/asistente/mensaje` y `POST /api/asistente/stream`: cada respuesta final incluye `atendido_por: SKY`, y una sugerencia técnica `rol_interno_sugerido`. Esto **no representa una ejecución**. Se preservan los contratos de respuesta anteriores.
- `POST /api/sky/workflows` + vista previa + aprobación individual: ejecución real de procesos seguros mediante el motor existente, con resultados verificables.
- `/api/sky/subagents/*`: perfiles personalizados creados por el dueño; no reemplazan los seis roles base.

Ejemplo de vista previa de trabajo interno sin ejecución:

```json
{
  "name": "Preparar presentación profesional",
  "steps": [
    {"agent": "planificador", "action": "plan",
     "task": "Organizar estructura de la investigación", "params": {}},
    {"agent": "documentalista", "action": "document",
     "task": "Crear el material de apoyo en Markdown",
     "params": {"document": {"kind": "md", "title": "Informe", "content": "# Informe\nContenido verificado..."}}}
  ]
}
```

Para convertirlo en trabajo real, se crea un workflow con los pasos validados y el propietario aprueba su huella exacta. Los roles **no crean permisos**, ni contactan servicios cloud de manera encubierta.

## Próximos roles temáticos (solo propuesta)

Sobre los ejecutores y las futuras Skills registrables: investigación global y académica, desarrollo de software, docencia, administración/finanzas, diseño gráfico, multimedia, turismo y viajes, cuidado del hogar, deportes y productividad personal. No están activos simplemente por nombrarlos. Cada uno debe tener herramientas reales, contratos, pruebas y permisos específicos.

## Criterios de aceptación

- Solo SKY figura como centro de atención en los resultados de conversación por voz y texto.
- Sin ninguna aprobación no se ejecutan flujos; planificar no es actuar.
- Rol externo o combinación de rol/herramienta incongruente devuelve 422.
- El catálogo no exige que los cinco roles estén ejecutando procesos continuamente.
- Los cambios no tocan `main` hasta obtener CI Linux/Windows, validación de permisos y pruebas reales de escritorio.
- Estado real reportado: `implementado`, `probado`, `pendiente`, `bloqueado`, nunca un éxito ficticio.
