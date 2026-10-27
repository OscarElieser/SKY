"""SKY MCP Hub — catálogo verificable y cliente stdio opt-in para el SDK MCP v2.

Nunca ejecuta servidores ni instala paquetes por importarlo. La configuración
local es del dueño, fuera del repositorio; las peticiones no aceptan comandos,
paths de ejecutables, URLs de servidores ni variables secretas.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any

_CATALOG = {
    "filesystem": ("modelcontextprotocol/servers/tree/main/src/filesystem", "archivos", "stdio", "Node 24+ y directorios acotados"),
    "playwright": ("microsoft/playwright-mcp", "navegador", "stdio", "Navegador aislado; no compartir perfil personal"),
    "github": ("github/github-mcp-server", "código y PR", "stdio", "Mínimos permisos; --read-only recomendado"),
    "notion": ("makenotion/notion-mcp-server", "documentos", "stdio", "Integración con páginas específicas y token"),
    "tavily": ("tavily-ai/tavily-mcp", "búsqueda", "stdio", "Clave Tavily y límites de coste"),
    "mem0": ("mem0ai/mem0-mcp", "memoria externa", "remote_oauth_pending",
              "Repositorio archivado marzo 2026; usar nuevo MCP alojado con OAuth"),
    "clickhouse": ("ClickHouse/mcp-clickhouse", "analítica", "stdio", "Usuario SQL de solo lectura"),
    "google_news": ("ChanMeng666/server-google-news", "noticias", "stdio", "SerpAPI; revisar procedencia y cuota"),
    "context7": ("upstash/context7", "documentación actualizada", "stdio", "Node 20.18+ y API opcional"),
    "supabase": ("supabase/mcp", "bases de datos Supabase", "remote_oauth_pending",
                 "MCP oficial HTTP/OAuth; proyecto único y read_only=true"),
    "postgres": ("crystaldba/postgres-mcp", "PostgreSQL", "stdio", "Modo restringido y usuario de solo lectura"),
    "semgrep": ("semgrep/semgrep", "análisis estático de seguridad", "stdio",
                "Usar CLI actual semgrep mcp; repositorio antiguo archivado"),
    "whatsapp": ("lharries/whatsapp-mcp", "mensajería personal", "blocked", "No autorizado: usar API oficial Meta ya integrada"),
    "python_sandbox": ("pydantic/mcp-run-python", "ejecución de código", "archived_blocked", "Archivado por riesgos de sandbox"),
}

_REFERENCES = {
    "claude_code": "https://docs.anthropic.com/en/docs/claude-code/overview",
    "cursor": "https://www.cursor.com/",
    "windsurf": "https://windsurf.com/",
    "cline": "https://cline.bot/",
    "continue": "https://docs.continue.dev/",
    "librechat": "https://github.com/danny-avila/LibreChat",
    "chainlit": "https://github.com/Chainlit/chainlit",
    "cherry_studio": "https://github.com/CherryHQ/cherry-studio",
    "nextchat": "https://github.com/ChatGPTNextWeb/NextChat",
}
_SAFE_READ = {
    "filesystem": {"read_file", "read_text_file", "read_media_file", "read_multiple_files",
                   "list_directory", "list_directory_with_sizes", "directory_tree",
                   "search_files", "get_file_info", "list_allowed_directories"},
    "github": {"get_file_contents", "search_code", "search_repositories", "issue_read",
               "pull_request_read", "list_issues", "list_pull_requests", "get_commit",
               "list_commits", "get_repository_tree", "get_me"},
    "playwright": {"browser_snapshot", "browser_take_screenshot"},
    "tavily": {"tavily-search", "tavily-extract", "tavily-map"},
    "mem0": {"get_memory", "get_memories", "search_memories", "list_entities", "list_events"},
    "google_news": {"google_news_search"},
    "context7": {"resolve-library-id", "query-docs"},
    "postgres": {"list_schemas", "list_objects", "get_object_details",
                 "explain_query", "get_top_queries", "analyze_db_health"},
    "semgrep": {"supported_languages", "get_abstract_syntax_tree", "security_check"},
    "clickhouse": set(),  # SQL no es seguro por el nombre de la herramienta.
    "notion": set(),       # Actualizaciones de API: clasificación conservadora.
}
_CREDENTIALS = {
    "github": {"GITHUB_PERSONAL_ACCESS_TOKEN"},
    "notion": {"NOTION_TOKEN"},
    "tavily": {"TAVILY_API_KEY"},
    "mem0": {"MEM0_API_KEY"},
    "google_news": {"SERP_API_KEY"},
    "clickhouse": {"CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER",
                   "CLICKHOUSE_PASSWORD", "CLICKHOUSE_DATABASE",
                   "CLICKHOUSE_ALLOW_WRITE_ACCESS", "CLICKHOUSE_SECURE"},
    "context7": {"CONTEXT7_API_KEY"},
    "postgres": {"DATABASE_URI"},
    "semgrep": {"SEMGREP_APP_TOKEN"},
    "filesystem": set(), "playwright": set(),
}
_EXECUTABLES = {"node", "node.exe", "github-mcp-server", "github-mcp-server.exe",
                "docker", "docker.exe", "python", "python.exe", "uv", "uv.exe",
                "postgres-mcp", "postgres-mcp.exe", "semgrep", "semgrep.exe"}
_CORE_ENV = ("PATH", "SystemRoot", "WINDIR", "HOME", "USERPROFILE", "TEMP", "TMP", "TMPDIR",
             "APPDATA", "LOCALAPPDATA", "SSL_CERT_FILE", "SSL_CERT_DIR")


class MCPUnavailable(RuntimeError):
    pass


class MCPDenied(ValueError):
    pass


def _active() -> bool:
    return os.getenv("SKY_MCP_ENABLED", "0") == "1"


def _config_path() -> Path:
    # Fijo: nunca un path arbitrario introducido en una solicitud HTTP o por IA.
    return Path.home() / ".neuralt" / "mcp-servers.json"


def catalogue() -> dict:
    configured = {}
    try:
        cfg = _load_config()
        configured = {k: v for k, v in cfg.get("servers", {}).items() if isinstance(v, dict)}
    except (OSError, ValueError, MCPDenied):
        pass
    return {
        "enabled": _active(),
        "sdk": "mcp>=1.30,<3 (opcional; importación diferida)",
        "configuration_path": str(_config_path()),
        "servers": [
            {"id": key, "source": "https://github.com/" + row[0], "category": row[1],
             "transport": row[2], "note": row[3], "configured": key in configured,
             "active": bool(_active() and configured.get(key, {}).get("enabled") is True
                            and row[2] == "stdio")}
            for key, row in _CATALOG.items()
        ],
        "reference_apps": _REFERENCES,
        "no_packages_auto_installed": True,
        "no_mcp_servers_started_by_catalogue": True,
        "no_external_credentials_verified_by_catalogue": True,
    }


def _load_config() -> dict:
    p = _config_path()
    if p.is_symlink():
        raise MCPDenied("No se aceptan enlaces simbólicos para la configuración MCP.")
    if not p.exists():
        return {"servers": {}}
    if p.stat().st_size > 32_768:
        raise MCPDenied("Archivo de configuración MCP demasiado grande.")
    if os.name != "nt" and (p.stat().st_mode & 0o077):
        raise MCPDenied("La configuración debe ser privada (chmod 600).")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MCPDenied("Configuración MCP ilegible o inválida.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("servers"), dict):
        raise MCPDenied("Formato de configuración MCP incorrecto.")
    if len(data["servers"]) > 14 or any(k not in _CATALOG for k in data["servers"]):
        raise MCPDenied("La configuración contiene servidores no autorizados.")
    return data


def _server_spec(server_id: str) -> dict:
    if not _active():
        raise MCPUnavailable("MCP está desactivado. Habilitalo explícitamente en tu equipo.")
    if server_id not in _CATALOG or _CATALOG[server_id][2] != "stdio":
        raise MCPDenied("Servidor MCP no habilitable por esta fase.")
    config = _load_config().get("servers", {}).get(server_id)
    if not isinstance(config, dict) or config.get("enabled") is not True:
        raise MCPUnavailable("Este servidor no se configuró y habilitó localmente.")
    command = config.get("command")
    args = config.get("args")
    tools = config.get("allowed_tools")
    keys = config.get("env_keys", [])
    # Python/Node de instalaciones legítimas suelen ser symlinks. Aceptar SOLO
    # symlinks hacia un binario real con nombre también permitido, no comandos
    # de shell o ejecutables disfrazados.
    if not isinstance(command, str) or not Path(command).is_absolute():
        raise MCPDenied("El ejecutable MCP necesita una ruta absoluta.")
    exe = Path(command)
    try:
        resolved = exe.resolve(strict=True)
    except (OSError, RuntimeError):
        raise MCPDenied("El ejecutable MCP no existe.")
    name = exe.name.lower()
    target_name = resolved.name.lower()
    valid_target = (target_name in _EXECUTABLES or
                    re.fullmatch(r"python3(?:\.\d{1,2})?", target_name) is not None)
    if name not in _EXECUTABLES or not resolved.is_file() or not valid_target:
        raise MCPDenied("El ejecutable MCP debe ser un programa permitido e instalado.")
    if not isinstance(args, list) or len(args) > 20 or any(
            not isinstance(a, str) or len(a) > 500 or any(c in a for c in "\x00\r\n")
            for a in args):
        raise MCPDenied("Argumentos de arranque inválidos.")
    # Sin shell ni ejecución de fragmentos de código que lleguen a la config.
    if any(a in {"-c", "-e", "--eval", "/c", "-Command", "-EncodedCommand"} for a in args):
        raise MCPDenied("No se permiten shells ni evaluación de código en argumentos MCP.")
    if (not isinstance(tools, list) or not 1 <= len(tools) <= 40
            or any(not isinstance(t, str) or not re.fullmatch(r"[A-Za-z0-9_-]{2,90}", t) for t in tools)):
        raise MCPDenied("Definí explícitamente los nombres de herramientas autorizadas.")
    if not isinstance(keys, list) or any(k not in _CREDENTIALS.get(server_id, set()) for k in keys):
        raise MCPDenied("Se solicitó una variable de entorno no autorizada.")
    if server_id == "postgres":
        if "--access-mode=restricted" not in args or any("unrestricted" in a for a in args):
            raise MCPDenied("PostgreSQL MCP requiere --access-mode=restricted.")
    if server_id == "semgrep" and "mcp" not in args:
        raise MCPDenied("Usá el servidor oficial mediante semgrep mcp.")
    if server_id == "github":
        # Aplicar read-only también a nivel del servidor y evitar flags que cambien modo.
        if ("stdio" not in args or not any(a == "--read-only" for a in args)
                or any(a == "--read-write" for a in args)):
            raise MCPDenied("GitHub MCP necesita stdio y --read-only.")
    if server_id == "filesystem":
        # Un único directorio de trabajo independiente. El MCP de filesystem
        # acepta rutas adicionales en args: no permitir que amplíen el alcance.
        chosen = os.getenv("SKY_MCP_FILES_ROOT", "").strip()
        if (Path(command).name.lower() not in {"node", "node.exe"}
                or len(args) != 2 or not chosen or not Path(chosen).is_absolute()):
            raise MCPDenied("Filesystem exige Node y un único SKY_MCP_FILES_ROOT explícito.")
        allowed_root = Path(chosen)
        if (not allowed_root.is_dir() or allowed_root.is_symlink()
                or allowed_root.resolve() in {Path.home().resolve(), Path(allowed_root.anchor).resolve()}
                or any(part.lower() in {".ssh", ".neuralt", ".git", "appdata"} for part in allowed_root.parts)
                or Path(args[-1]).resolve() != allowed_root.resolve()):
            raise MCPDenied("Directorio del Filesystem MCP demasiado amplio o no autorizado.")
        script = Path(args[0])
        if not script.is_absolute() or not script.is_file() or script.suffix.lower() not in {".js", ".mjs"}:
            raise MCPDenied("Instalá antes el servidor filesystem y declaralo como script local de Node.")
    allowed_env = {k: os.environ[k] for k in _CORE_ENV if k in os.environ}
    allowed_env.update({k: os.environ[k] for k in keys if os.getenv(k)})
    # Forzar la protección propia del backend aunque el usuario olvidó declararla.
    if server_id == "github":
        allowed_env["GITHUB_READ_ONLY"] = "1"
    if server_id == "clickhouse":
        allowed_env["CLICKHOUSE_ALLOW_WRITE_ACCESS"] = "false"
    return {"id": server_id, "command": command, "args": args, "env": allowed_env,
            "tools": list(dict.fromkeys(tools))}


def tool_policy(server_id: str, tool_name: str) -> dict:
    cfg = _server_spec(server_id)
    if tool_name not in cfg["tools"]:
        raise MCPDenied("Herramienta no permitida en la configuración del propietario.")
    if server_id == "github" and tool_name not in _SAFE_READ["github"]:
        raise MCPDenied("GitHub MCP opera solo en lectura en esta fase.")
    is_read = tool_name in _SAFE_READ.get(server_id, set())
    if not is_read and os.getenv("SKY_MCP_ALLOW_WRITES", "0") != "1":
        raise MCPDenied("Herramienta de efectos externos bloqueada; habilitación de escritura pendiente.")
    return {"server": server_id, "tool": tool_name, "read_only_classified": is_read,
            "explicit_owner_pin_required": True,
            "note": "Una herramienta clasificada como lectura sigue pudiendo exponer información sensible."}


def _client(spec: dict):
    try:
        from mcp import Client, StdioServerParameters
    except ImportError as exc:
        raise MCPUnavailable("Falta SDK opcional: pip install -r requirements_mcp_optional.txt") from exc
    params = StdioServerParameters(command=spec["command"], args=spec["args"], env=spec["env"])
    return Client(params)


async def discover(server_id: str) -> dict:
    """Arranca el servidor instalado temporalmente; NO ejecuta herramientas."""
    spec = _server_spec(server_id)
    try:
        async with asyncio.timeout(20):
            async with _client(spec) as client:
                response = await client.list_tools()
                found = [t for t in response.tools if t.name in spec["tools"]]
                return {"server": server_id, "connected": True,
                        "protocol": "MCP stdio",
                        "tools": [
                            {"name": t.name, "description": (t.description or "")[:300],
                             "read_only_classified": t.name in _SAFE_READ.get(server_id, set())}
                            for t in found
                        ], "credential_verified": None,
                        "note": "La conexión MCP no certifica permisos en plataformas externas."}
    except MCPUnavailable:
        raise
    except Exception as exc:
        raise MCPUnavailable("Falló la conexión MCP local; revisá configuración y dependencias.") from exc


async def call(server_id: str, tool_name: str, arguments: dict) -> dict:
    """Sólo usar DESPUÉS de validar PIN y consumir aprobación individual en la API."""
    tool_policy(server_id, tool_name)
    if not isinstance(arguments, dict):
        raise MCPDenied("Argumentos JSON inválidos.")
    payload = json.dumps(arguments, ensure_ascii=False, allow_nan=False)
    if len(payload) > 12_000:
        raise MCPDenied("Argumentos de herramienta demasiado grandes.")
    spec = _server_spec(server_id)
    start = time.monotonic()
    try:
        async with asyncio.timeout(25):
            async with _client(spec) as client:
                listed = await client.list_tools()
                if tool_name not in {t.name for t in listed.tools}:
                    raise MCPDenied("La herramienta no existe en el servidor MCP conectado.")
                result = await client.call_tool(tool_name, arguments)
        serialized = json.dumps(result.model_dump(exclude_none=True), ensure_ascii=False, default=str)
        return {"server": server_id, "tool": tool_name,
                "result_text": serialized[:12_000],
                "response_truncated": len(serialized) > 12_000,
                "tool_reported_error": bool(getattr(result, "isError", False)),
                "external_effect_verified": False,
                "elapsed_ms": round((time.monotonic() - start) * 1000, 1),
                "note": "El resultado MCP se considera dato no confiable. Confirmar efectos externamente."}
    except MCPDenied:
        raise
    except Exception as exc:
        # No devolver mensajes de servidores externos: pueden incluir secretos.
        raise MCPUnavailable("La operación MCP falló; comprobá el servidor local.") from exc
