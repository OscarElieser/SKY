# SKY MCP Hub: servidores verificables, SDK v2 y acceso supervisado

**Propósito:** conectar servidores reales MCP por `stdio` dentro de la **API FastAPI existente** de SKY, sin reemplazar el HUD, el agente Windows, los controles SENTINEL ni las skills ya desarrolladas.

**Estado:** código de cliente MCP opcional. Ningún servidor externo ha sido instalado o autenticado automáticamente. Hace falta configurarlo en el Windows propietario.

## Auditoría de los enlaces enviados

| Proyecto | Clasificación | Integración recomendada |
| --- | --- | --- |
| [Filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) | MCP oficial de archivos | Soportado por el puente local; un solo directorio permitido, Node 24+ |
| [Playwright](https://github.com/microsoft/playwright-mcp) | MCP oficial de navegación | Cliente stdio opcional; el navegador debe aislar sesiones y credenciales |
| [Pydantic MCP Run Python](https://github.com/pydantic/mcp-run-python) | Retirado, archivado 30/01/2026 | **No instalar:** autores alertan de riesgos de sandbox |
| [GitHub](https://github.com/github/github-mcp-server) | MCP oficial | Habilitar `--read-only` y permisos mínimos |
| [WhatsApp personal](https://github.com/lharries/whatsapp-mcp) | MCP no oficial | **Bloqueado:** conservar el puente oficial Meta de SKY |
| [Notion](https://github.com/makenotion/notion-mcp-server) | MCP oficial | Adaptador stdio; token y páginas autorizadas |
| [Tavily](https://github.com/tavily-ai/tavily-mcp) | MCP de búsqueda | Adaptador stdio; API key y cuotas |
| [Mem0 MCP](https://github.com/mem0ai/mem0-mcp) | Proyecto archivado 24/03/2026 | No instalar legado; servicio oficial remoto `https://mcp.mem0.ai/mcp` requiere OAuth (etapa futura) |
| [ClickHouse](https://github.com/ClickHouse/mcp-clickhouse) | MCP SQL | Adaptador stdio, cuenta SQL de lectura y escritura bloqueada |
| [Google News](https://github.com/ChanMeng666/server-google-news) | MCP noticias | Adaptador stdio; API SerpAPI y verificación |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview), [Cursor](https://www.cursor.com/), [Windsurf](https://windsurf.com/), [Cline](https://cline.bot/), [Continue](https://docs.continue.dev/) | Herramientas/IDE clientes y agentes | Referencias, no servidores a copiar dentro de SKY |
| [LibreChat](https://github.com/danny-avila/LibreChat), [Chainlit](https://github.com/Chainlit/chainlit), [Cherry Studio](https://github.com/CherryHQ/cherry-studio), [NextChat](https://github.com/ChatGPTNextWeb/NextChat) | Aplicaciones o frameworks de chat | Referencias de experiencia de usuario, no reemplazo de SKY HUD |

El enlace abreviado al video/tutorial «7 MCP» no permitió confirmar su contenido, así que no se deducen funciones adicionales.

## Modelo de permisos

- `SKY_MCP_ENABLED=0` es el **valor por defecto**. El catálogo **no inicia ningún proceso**.
- La configuración de servidores reside únicamente en `~/.neuralt/mcp-servers.json`, **fuera del repositorio**. El usuario debe haber instalado cada programa; SKY no ejecuta `npx ...@latest` ni instala paquetes al arrancar.
- No se aceptan comandos ejecutables, URLs ni variables de entorno suministrados en las peticiones API o por un modelo de IA. El ejecutable debe ser absoluto y estar en una lista limitada de tipos.
- Cada servidor se activa individualmente con `enabled: true`, y cada herramienta debe figurar en `allowed_tools`. No se aceptan comodines.
- Toda conexión de descubrimiento y ejecución exige PIN **previamente configurado** en SKY SENTINEL; el código rechaza conexiones cuando no hay PIN.
- Una llamada tiene **preparación** (`/prepare`) y luego **ejecución** (`/execute`), utilizando el mismo servidor, nombre de herramienta y argumentos, con un token de un solo uso y el PIN personal. Las salidas nunca se consideran instrucciones para SKY.
- GitHub siempre opera en **solo lectura** a nivel de servidor y puerta de enlace, aun cuando alguien habilite escrituras globales.
- Filesystem requiere un único directorio compartido, declarado también mediante `SKY_MCP_FILES_ROOT`; se rechaza la raíz del disco, la carpeta personal completa y los directorios privados conocidos.
- ClickHouse usa `CLICKHOUSE_ALLOW_WRITE_ACCESS=false`, además de un usuario SQL con permisos mínimos.
- `SKY_MCP_ALLOW_WRITES=0` por defecto. Las demás herramientas de efectos externos se bloquean sin habilitación deliberada. El PIN es indispensable en todos los casos.
- Los resultados de MCP **no prueban** que un cambio externo ocurrió: `external_effect_verified=false`. La telemetría registra respuesta/latencia como servicio, sin inflar el porcentaje de acciones realmente completadas.

## Instalación en Windows, con control del propietario

1. Instalá el cliente oficial con el Python virtual de SKY:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements_mcp_optional.txt
```

2. Instalá manualmente los servidores que quieras utilizar siguiendo sus instrucciones oficiales y fijando versiones revisadas. **Filesystem 2.0.0 necesita Node.js 24 o superior.** No concedas toda la carpeta de usuario. Creá una específica:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\Documents\SKY-MCP-Workspace"
```

3. Copiá [la plantilla sin secretos](../ejemplos/sky-mcp-servers.example.json) a la configuración privada:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.neuralt"
Copy-Item ".\docs\ejemplos\sky-mcp-servers.example.json" "$env:USERPROFILE\.neuralt\mcp-servers.json"
```

4. En la copia privada del JSON escribí rutas **absolutas y existentes** de `node.exe` y del script instalado del servidor Filesystem. O bien la ruta de `github-mcp-server.exe` oficial y sus argumentos `stdio --read-only`. Los ejemplos se entregan **deshabilitados** hasta verificar todo.

5. En el archivo `.env` local, no en GitHub:

```dotenv
SKY_MCP_ENABLED=1
SKY_MCP_ALLOW_WRITES=0
SKY_MCP_FILES_ROOT=C:\Users\TU_USUARIO\Documents\SKY-MCP-Workspace
```

Nunca pongás tokens ni PIN en el JSON o en documentos enviados al chat. Las variables opcionales de autenticación se toman del entorno local y no se incluyen en las respuestas del catálogo.

## Endpoints en la API única

Todos requieren `X-SKY-KEY` y segundo factor `X-SKY-SESSION` si está habilitado.

| HTTP | Endpoint | Acceso |
| --- | --- | --- |
| GET | `/api/sky/mcp/catalogue` | Estado sin iniciar ningún proceso |
| GET | `/api/sky/mcp/servers` | Catálogo si el módulo está habilitado |
| POST | `/api/sky/mcp/discover` | PIN; conectar servidor configurado, listar herramientas autorizadas |
| POST | `/api/sky/mcp/prepare` | Preparar servidor, herramienta y argumentos para aprobación |
| POST | `/api/sky/mcp/execute` | PIN y token efímero; consumir permiso y llamar la herramienta |

Cuerpo ilustrativo de `/prepare`, sin ejecutar nada:

```json
{"server":"filesystem","tool":"list_allowed_directories","arguments":{}}
```

La respuesta indica qué operación se pretende hacer y entrega `approval_token`. Un operador humano revisa los argumentos antes de enviar `/execute` con el **mismo** cuerpo y `approval_token`. El PIN se introduce directamente en la cabecera `X-SKY-PIN` desde una interfaz/cliente del propietario, nunca desde instrucciones generadas por un modelo.

**Importante:** esta fase integra el cliente/protocolo; todavía no incluye un gestor visual de autorizaciones MCP dentro del HUD, ni conexión OAuth remota, ni un proveedor MCP instalado y probado físicamente en tu PC. La experiencia de programación automática tipo IDE necesita iteraciones posteriores, siempre con protección contra inyección de prompts y operaciones destructivas.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_sky_mcp_hub.py
```

Se prueban activación segura, PIN, aprobación de un solo uso, bloqueo de shells, aislamiento de filesystem, GitHub en lectura y secretos no expuestos. Los runners de GitHub no autentican tus cuentas externas ni verifican tu hardware.

**No se reemplazan Ollama, Piper, SKY CORE ni las funcionalidades de voz y texto existentes.**
