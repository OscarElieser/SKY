# SKY Cognition Bridge v1 — extensión sin borrar funcionalidades

## Estado real

Implementación en código en la rama `main`. Pruebas automatizadas y validación
en Windows y Android son pasos independientes: **un commit no demuestra que esté
funcionando en el dispositivo**. Esta ampliación no sustituye módulos, proveedores,
memoria existente, HUD, agente Windows ni SKY Android.

## Componentes añadidos

- `neural_core/sky_cognition.py`: clasificación explicable, planificación
  consultiva, memoria explícita existente, referencias públicas almacenadas,
  selección de animación de emoción simulada y preprocesamiento de texto para TTS.
- `metaverse/sky_cognition_api.py`: rutas autenticadas con X-SKY-KEY y MFA
  existente, sin acceso público abierto.
- `metaverse/api.py`: opción `cognitive` en `POST /api/chat` para incorporar
  contexto en el prompt **solo cuando el propietario lo active**. La opción
  `cognitive_private` requiere Ollama local. La ruta y sus respuestas anteriores
  siguen siendo válidas por defecto.
- `tests/test_sky_cognition.py`: regresiones de seguridad, contexto y estilo.

## Rutas bajo `/api/sky/cognition`

| Método | Ruta | Efecto real |
|---|---|---|
| GET | `/capabilities` | Declara el alcance y los límites |
| POST | `/plan` | Devuelve plan propuesto, sin ejecutar |
| POST | `/context` | Recupera referencias públicas de caché y memoria cifrada bajo permiso |
| POST | `/personality` | Devuelve estilo y animación simulada |
| POST | `/speech` | Prepara texto para TTS, no reproduce audio |
| GET | `/execution-metrics` | Lee resultados verificados registrados previamente |

Todas requieren la autenticación del propietario. Ejemplo de PowerShell:

```powershell
$h = @{ "X-SKY-KEY" = $env:SKY_API_KEY }
$b = @{ query = "Investiga Flutter"; execution = "cloud"; include_public = $true } |
  ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8765/api/sky/cognition/context" -Headers $h -ContentType "application/json" -Body $b
```

Para conversar con contexto público (opt-in):

```json
{"message":"¿Qué novedades hay de Flutter?", "provider":"ollama", "cognitive":true}
```

Para memoria personal, el dueño debe primero configurar `SKY_NEURAL_MEMORY_KEY`
para el almacén existente y confirmar hechos mediante
`POST /api/sky/neural-memory/facts`. Luego puede solicitar:

```json
{"message":"¿Qué sabes del proyecto?", "provider":"ollama", "cognitive":true, "cognitive_private":true}
```

No enviar memorias a proveedores externos automáticamente. Si la clave cifrada no
está disponible, el sistema devuelve una advertencia y continúa sin recuerdos.
No hay sincronización de memoria Android ↔ Windows en esta versión.

## Qué NO hace esta etapa

No reentrena pesos del Transformer; no realiza búsquedas web en vivo desde el
puente (usa cachés citadas); no reproduce voz por sí mismo; no controla aplicaciones
ni concede permisos de forma automática; no acredita sensaciones reales de SKY;
no descarga ni publica APK; no habilita acceso oculto con pantalla bloqueada.

Los agentes y las funciones de investigación, docencia y multimedia ya existentes
se conservan. Para operaciones reales siguen siendo necesarias las herramientas
y aprobaciones existentes, comprobaciones del resultado y pruebas en dispositivos.

## Verificación

```powershell
python -m py_compile neural_core/sky_cognition.py metaverse/sky_cognition_api.py metaverse/api.py
python -m pytest -q tests/test_sky_cognition.py
```

En Android se conservan las funciones existentes. El puente Python todavía no está
incorporado a la APK; conectarlo requiere implementación nativa o API autenticada,
consentimiento de sincronización, compilación y pruebas de seguridad.
