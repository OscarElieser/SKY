# SKY IA v9.0 — API del Experience Orchestrator

**Concepción del proyecto:** Oscar Elieser Chamorro Guzmán.

## Arranque privado

```bash
python -m pip install -r requirements_studio.txt
python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765 --workers 1
```

Panel web: `http://127.0.0.1:8765/studio`. Documentación OpenAPI: `http://127.0.0.1:8765/docs`.

Las rutas `api/sky` requieren `X-SKY-KEY: <clave-local>`. En primer arranque,
se genera una clave aleatoria en `local_data/sky_api_token.txt`. No compartirla,
no incluirla en Git, no pegarla en una URL y no exponer el servidor en Internet
sin HTTPS, administración de identidades, control de acceso y protección adicional.

## Contrato de planificación (sin efectos secundarios)

```http
POST /api/sky/plan
X-SKY-KEY: <clave privada>
Content-Type: application/json

{"task":"Diseñá una academia virtual con cursos y un mundo 3D"}
```

Respuesta: roles elegidos, habilidades sugeridas y etapas por verificar.
Los roles son **enfoques de asistencia**, no profesiones certificadas ni motores neuronales diferentes.

## Gestión de tareas — dos fases

`POST /api/sky/tasks` crea una tarea pendiente:

```json
{
  "task": "Crear mi sitio de cursos de tecnología",
  "action": "experience",
  "params": {"title":"Academia SKY", "template":"classroom", "palette":"sky"}
}
```

`POST /api/sky/tasks/{id}/execute` con `{"approve":true}` la ejecuta **una sola vez**. La misma tarea no puede volver a ejecutarse con la misma ID. Hay bitácora de acciones en `GET /api/sky/audit`.

Acciones permitidas y sus resultados:

| `action` | Herramienta real | Salida |
|---|---|---|
| `plan` | Motor de roles | Plan persistido |
| `experience` | SKY Visual Creator | HTML/CSS + especificación JSON persistente |
| `world` | SKY Metaverse Engine | Mundo 3D creado en SQLite, exportación GLB |
| `document` | SKY Office Studio | DOCX, XLSX, PPTX, PDF, MD, HTML o CSV |
| `memory` | Registro privado SQLite | Nota personal, con lectura y eliminación |

### Ejemplo de documento

```json
{
  "task": "Preparar una presentación editable sobre innovación",
  "action": "document",
  "params": {
    "document": {
      "kind":"pptx",
      "title":"Innovación en Nicaragua",
      "content":"# Diagnóstico\nNecesidad identificada...\n# Propuesta\nPrototipo técnico..."
    }
  }
}
```

El archivo se guarda en el directorio privado `local_data/sky_outputs`, con nombre
vinculado a la ID y suma SHA-256. Después se descarga autenticadamente en
`GET /api/sky/files/{id}`. No se crea un documento con contenido ficticio si falta el texto/datos.

### Vistas editables

- `POST /api/sky/experiences/preview` → vista HTML y JSON sin guardar.
- `GET /api/sky/experiences` → catálogo privado.
- `GET /api/sky/experiences/{id}` → datos editables JSON.
- `GET /api/sky/experiences/{id}/html` → descarga HTML autenticada.
- `GET /api/sky/creator/options` → plantillas y paletas.

La exportación HTML es una página web responsive editable **generada por reglas y plantillas**. No produce fotos ni modelos de lenguaje internos. Si se quiere arte original, foto a 3D avanzado, video o audio, se necesitarán los modelos y el hardware correspondientes.

## Chat y especializaciones

- `GET /api/sky/roles` → catálogo de especialidades.
- `POST /api/sky/assist` → identifica roles y responde con plan local, sin nube.
- Con `"provider":"gemini"` (u OpenAI, Anthropic, Ollama, etc.), SKY envía el mensaje **solo al proveedor solicitado**.
- `"include_memory": true` se requiere expresamente para que SKY incluya notas privadas en una solicitud externa.

## Actividad / Neural Core

`GET /api/sky/activity` devuelve una **muestra real** de rutas usadas,
tiempos y códigos de estado, sin cuerpos de mensajes ni IP. No son activaciones
internas de neuronas; los pesos y estados internos de los proveedores no son observables.

## Seguridad

- Servidor de desarrollo enlazado exclusivamente a `127.0.0.1`, por defecto.
- Autenticación en todas las rutas privadas. No se permite ejecutar shell arbitrario.
- Salidas descargables solo por ID aprobada; sin recibir nombres de archivo de un cliente en la ruta.
- Previsualización HTML en `<iframe sandbox>` y texto escapado.
- Almacenamiento de notas y tareas local y separado de la comunidad multiusuario.
- No pagos, no negociación bursátil, no cambios en BAQUEANO, no publicación de webs sin confirmación y conectores específicos.
- Respaldo consistente con `python sky_backup.py` para bases existentes y archivos de Office.

## Limitaciones verificadas

Las pruebas automáticas validan el código local y el servidor API. No equivalen a
una auditoría de penetración, disponibilidad empresarial, ni pruebas de VR, cámaras,
micrófonos físicos o APIs externas. Para un lanzamiento mundial se requieren pruebas
multiusuario, migración de SQLite a servicios preparados para escalado, seguridad,
moderación, operación continua, copias de seguridad externas y observabilidad.
