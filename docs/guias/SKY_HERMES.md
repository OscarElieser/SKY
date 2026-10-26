# Hermes Agent como consultor de SKY (PowerShell)

[Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research, licencia MIT) es un agente con memoria propia, habilidades que se mejoran solas e investigación web.

En SKY trabaja como **consultor**: investiga, analiza y planifica cuando se lo pedís. **SKY sigue siendo la única que actúa sobre tus equipos**, con su PIN, sus permisos y su agente.

```
Vos → SKY (PIN, sesión, permisos) → Hermes (sólo tu pregunta) → texto → SKY te lo dice
                                   ✗ Hermes nunca recibe tu memoria ni tu PIN
                                   ✗ SKY nunca ejecuta lo que Hermes escriba
```

## Qué controla SKY por código antes de cada consulta
- Hermes debe estar en `127.0.0.1`. SKY no sigue redirecciones ni usa proxies.
- Pide la lista de herramientas de Hermes (`/v1/toolsets`) y **se niega si hay alguna que actúe sobre tu equipo o en tu nombre**: terminal, archivos, ejecución de código, navegador, uso de la computadora, delegación, tareas programadas, generación de imágenes o video (que gasta créditos) y mensajería.
- Las herramientas permitidas son: `web`, `vision`, `video`, `skills`, `todo`, `memory`, `session_search`, `clarify`, `context_engine`, `x_search`, `tts` y `stt`.
- La API de herramientas de Hermes no muestra los servidores MCP, así que SKY revisa su `config.yaml`: la plataforma API tiene que tener `no_mcp`, o Hermes no debe tener servidores MCP configurados.
- Con `SKY_LOCAL_ONLY=1`, sólo consulta si el modelo de Hermes es local (por ejemplo, tu Ollama).
- Con la sesión de SKY bloqueada, no hay consultas: la API, la voz y WhatsApp esperan el PIN.

## 1. Instalar Hermes
El instalador oficial descarga y ejecuta un script de Nous Research. Si querés revisarlo antes, bajalo primero:

```powershell
irm https://hermes-agent.nousresearch.com/install.ps1 -OutFile "$env:TEMP\hermes-install.ps1"
notepad "$env:TEMP\hermes-install.ps1"          # revisalo
powershell -ExecutionPolicy Bypass -File "$env:TEMP\hermes-install.ps1"
```

En Windows, Hermes se instala en `%LOCALAPPDATA%\hermes`. Cerrá y abrí PowerShell, y comprobá con `hermes doctor`.

## 2. Usar tu modelo local (Ollama) en lugar de la nube

```powershell
hermes config set model.provider custom
hermes config set model.base_url http://127.0.0.1:11434/v1
hermes config set model.default qwen2.5:7b      # el mismo modelo que usa SKY (OLLAMA_MODEL)
```

También podés elegir otro proveedor con `hermes model`. En ese caso tus preguntas a Hermes salen a ese servicio.

## 3. Dejar a Hermes sólo con herramientas de consulta

```powershell
hermes config set platform_toolsets.api_server "['web','memory','skills','session_search','no_mcp']"
```

`no_mcp` impide que la API cargue servidores MCP. Si después activás `terminal`, `file`, `browser` u otra herramienta que actúe, SKY lo detecta y deja de consultarlo hasta que la desactives.

## 4. Encender la API de Hermes con una clave propia

```powershell
$clave = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 40 | ForEach-Object {[char]$_})
Add-Content "$env:LOCALAPPDATA\hermes\.env" "API_SERVER_ENABLED=true"
Add-Content "$env:LOCALAPPDATA\hermes\.env" "API_SERVER_KEY=$clave"
Add-Content "$SKY\.env" "SKY_HERMES_ENABLED=1"
Add-Content "$SKY\.env" "SKY_HERMES_KEY=$clave"
Remove-Variable clave
hermes gateway          # debe mostrar: API server listening on http://127.0.0.1:8642
```

(`$SKY` es la carpeta de SKY, como en `SKY_WINDOWS_V12_6.md`.)

**No configures** en Hermes Telegram, WhatsApp ni otras mensajerías (`hermes gateway setup`). Serían una segunda entrada a tu PC que no pasa por el PIN de SKY.

## 5. Usarlo desde SKY

Reiniciá SKY (`iniciar_sky_autonomo.py --stop` y después iniciala de nuevo). Probá por voz o texto:
- «SKY, ¿cómo está Hermes?» → te dice si está listo o qué falta exactamente.
- «SKY, preguntale a Hermes qué conviene para respaldar mis fotos».
- «Hermes, investigá las novedades de Python 3.14 y resumimelas».
- «SKY, estado de los módulos» → «Hermes Agent (consultor)» aparece con su estado.

Si Hermes propone pasos, SKY te los lee; para ejecutarlos se los pedís a SKY, que aplica sus permisos y su PIN de siempre. Las consultas pueden tardar (hasta `SKY_HERMES_TIMEOUT_S`, 180 s por defecto) porque Hermes investiga.

## Variables de `.env` de SKY
| Variable | Para qué |
|---|---|
| `SKY_HERMES_ENABLED=1` | Activa el consultor |
| `SKY_HERMES_KEY` / `SKY_HERMES_KEY_FILE` | La misma `API_SERVER_KEY` de Hermes |
| `SKY_HERMES_PORT` | Puerto local (8642 por defecto); el host siempre es 127.0.0.1 |
| `SKY_HERMES_MODEL` | Nombre que expone la API de Hermes (`hermes-agent`) |
| `SKY_HERMES_TIMEOUT_S` | Espera máxima por consulta (180) |

## Quitarlo
Borrá `SKY_HERMES_ENABLED` de `.env` (o ponelo en 0) y cerrá `hermes gateway`. SKY no guarda nada de Hermes. Hermes conserva su propia memoria en `%LOCALAPPDATA%\hermes`.
