# SKY IA Project Hub API — v9.2

**Autenticación:** enviar `X-SKY-KEY: <clave-maestra>` en todas las rutas.
Base: `http://127.0.0.1:8765`. Solo está diseñado para administración local.

| Método | Ruta | Resultado |
|---|---|---|
| POST | `/api/sky/projects` | Crea proyecto `{title,description}` |
| GET | `/api/sky/projects` | Lista proyectos privados |
| GET | `/api/sky/projects/{pid}` | Ficha + enlaces + estados de las tareas |
| PUT | `/api/sky/projects/{pid}` | Actualiza `{title,description,expected_version}`; error 409 si cambió |
| POST | `/api/sky/projects/{pid}/tasks` | Crea y vincula una tarea `{task,action,params}` (requiere ejecutar después) |
| POST | `/api/sky/projects/{pid}/links` | Vincula `{kind:task|world|experience,ref,label}` existente |
| DELETE | `/api/sky/projects/{pid}/links/{lid}` | Desvincula; no borra el artefacto original |
| POST | `/api/sky/projects/{pid}/notes` | Almacena nota privada `{title,content}` |
| GET | `/api/sky/projects/{pid}/notes` | Lee notas del proyecto |
| DELETE | `/api/sky/projects/{pid}/notes/{nid}` | Borra nota |
| GET | `/api/sky/projects/{pid}/messages` | Lee hasta 40 mensajes anteriores |
| DELETE | `/api/sky/projects/{pid}/messages` | Borra conversación del proyecto |
| GET | `/api/sky/projects/{pid}/export.zip` | Descarga ZIP de entregables, sin notas ni conversaciones |

## Continuar conversaciones de un proyecto

`POST /api/sky/assist` acepta cuatro nuevos campos opcionales:

```json
{
  "message": "Prepará la siguiente etapa de la academia",
  "provider": "local",
  "project_id": "prj_...",
  "share_project_context": true,
  "share_project_history": false,
  "save_to_project": true,
  "include_memory": false
}
```

- `project_id` enlaza la conversación a un proyecto existente.
- `share_project_context=true` agrega solo resumen y títulos de entregables.
- `share_project_history=true` agrega hasta 12 mensajes recientes a un modelo externo.
- `save_to_project=true` guarda intercambio usuario/SKY en SQLite local.
- `include_memory=true` añade recuerdos globales solo si el usuario lo autorizó.
- Para **modelos externos**, SKY solicita confirmación en el navegador. Los
  clientes API propios deben implementar también su aviso/confirmación.
- Para `provider=local`, SKY planifica con roles y herramientas propias; no se
  presenta como modelo general entrenado offline.

**Creación de tareas:** `POST /api/sky/projects/{pid}/tasks` sigue siendo la etapa de
preparación. `POST /api/sky/tasks/{tid}/execute` con `{"approve":true}` es otra
solicitud y mantiene el flujo de confirmación existente.

## Contratos y límites

- Una sola persona administradora mediante clave local; no sustituye la seguridad
  por usuario de Social Universe.
- Las bases de datos SQLite tienen transacciones y `busy_timeout`, pero
  esta implementación no es apropiada todavía para un clúster multiinstancia.
- Exportación limitada a 45 MB descomprimidos y 80 enlaces por proyecto; la ruta
  no añade contraseñas, notas ni mensajes.
- Los archivos `.glb` de mundos procedimentales se exportan cuando están
  disponibles sus dependencias; de lo contrario, queda el `.json` editable.
- Nunca enviar el ZIP de `local_data/` o `.env` a servicios públicos.
