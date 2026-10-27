"""Contrato MCP: opt-in, PIN, autorización consumible, alcance y sin secretos."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from neural_core import sky_mcp_hub as hub

KEY = "test-owner-api-secret-for-mcp-security-2026"


@pytest.fixture()
def context(tmp_path, monkeypatch):
    from neural_core import sentinel_identidad
    monkeypatch.setenv("SKY_API_KEY", KEY)
    monkeypatch.setenv("SKY_MCP_ENABLED", "1")
    monkeypatch.setenv("SKY_MCP_ALLOW_WRITES", "0")
    monkeypatch.setattr(hub, "_config_path", lambda: tmp_path / "servers.json")
    monkeypatch.setattr(sentinel_identidad, "pin_configurado", lambda: True)
    monkeypatch.setattr(sentinel_identidad, "verificar_pin", lambda p: p == "848484")
    # v12.6: con PIN configurado, la API exige además la sesión del dueño abierta (desbloqueada con el PIN).
    monkeypatch.setattr(sentinel_identidad, "sesion_bloqueada", lambda: False)
    conf = {"servers": {
        "playwright": {"enabled": True, "command": sys.executable,
                       "args": [str(tmp_path / "installed_browser_server.py")],
                       "env_keys": [], "allowed_tools": ["browser_snapshot", "browser_navigate"]},
    }}
    p = hub._config_path()
    p.write_text(json.dumps(conf), encoding="utf-8")
    p.chmod(0o600)
    with TestClient(__import__("metaverse.api", fromlist=["app"]).app) as client:
        yield client, monkeypatch, tmp_path


def headers(pin=None):
    d = {"X-SKY-KEY": KEY}
    if pin is not None:
        d["X-SKY-PIN"] = pin
    return d


def test_catalogue_without_server_start(context, monkeypatch):
    client, _, _ = context
    monkeypatch.setattr(hub, "_client", lambda *_: (_ for _ in ()).throw(AssertionError("launched")))
    assert client.get("/api/sky/mcp/catalogue").status_code in (401, 403)
    obj = client.get("/api/sky/mcp/catalogue", headers=headers()).json()
    assert obj["enabled"] is True
    assert obj["no_packages_auto_installed"]
    assert next(s for s in obj["servers"] if s["id"] == "whatsapp")["transport"] == "blocked"
    assert next(s for s in obj["servers"] if s["id"] == "python_sandbox")["transport"] == "archived_blocked"


def test_disabled_default_is_fail_closed(context, monkeypatch):
    client, _, _ = context
    monkeypatch.setenv("SKY_MCP_ENABLED", "0")
    assert client.get("/api/sky/mcp/servers", headers=headers()).status_code == 503
    payload = {"server": "playwright", "tool": "browser_snapshot", "arguments": {}}
    assert client.post("/api/sky/mcp/prepare", json=payload, headers=headers()).status_code == 503


def test_configuration_never_accepts_shell_or_missing_binary(context):
    _, _, tmp = context
    config = json.loads(hub._config_path().read_text())
    config["servers"]["playwright"]["command"] = "cmd.exe"
    hub._config_path().write_text(json.dumps(config))
    hub._config_path().chmod(0o600)
    with pytest.raises(hub.MCPDenied):
        hub._server_spec("playwright")
    config["servers"]["playwright"]["command"] = sys.executable
    config["servers"]["playwright"]["args"] = ["-c", "print('danger')"]
    hub._config_path().write_text(json.dumps(config))
    with pytest.raises(hub.MCPDenied):
        hub._server_spec("playwright")


def test_unknown_server_and_tool_blocked(context):
    _, _, _ = context
    for server in ("whatsapp", "python_sandbox", "shell", "mem0"):
        with pytest.raises(hub.MCPDenied):
            hub._server_spec(server)
    assert hub.tool_policy("playwright", "browser_snapshot")["read_only_classified"] is True
    with pytest.raises(hub.MCPDenied):
        hub.tool_policy("playwright", "browser_navigate")


def test_discovery_requires_actual_owner_pin(context, monkeypatch):
    client, _, _ = context
    body = {"server": "playwright"}
    assert client.post("/api/sky/mcp/discover", json=body, headers=headers()).status_code == 403
    assert client.post("/api/sky/mcp/discover", json=body, headers=headers("000000")).status_code == 403
    monkeypatch.setattr(__import__("neural_core.sentinel_identidad", fromlist=["pin_configurado"]),
                        "pin_configurado", lambda: False)
    assert client.post("/api/sky/mcp/discover", json=body, headers=headers("848484")).status_code == 409


def test_one_time_owner_approval_prevents_replay(context, monkeypatch):
    client, _, _ = context
    class FakeResult:
        isError = False
        def model_dump(self, **kwargs):
            return {"content": [{"type": "text", "text": "Snapshot MCP recibido"}], "isError": False}
    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def list_tools(self):
            return SimpleNamespace(tools=[SimpleNamespace(name="browser_snapshot",
                                                          description="Estado actual de navegador")])
        async def call_tool(self, tool, args):
            assert tool == "browser_snapshot"
            assert args == {"foo": "bar"}
            return FakeResult()
    monkeypatch.setattr(hub, "_client", lambda spec: FakeClient())
    payload = {"server": "playwright", "tool": "browser_snapshot", "arguments": {"foo": "bar"}}
    prep = client.post("/api/sky/mcp/prepare", json=payload, headers=headers())
    assert prep.status_code == 200, prep.text
    token = prep.json()["approval_token"]
    assert prep.json()["executed"] is False
    confirm = {**payload, "approval_token": token}
    bad_pin = client.post("/api/sky/mcp/execute", json=confirm, headers=headers("000000"))
    assert bad_pin.status_code == 403
    tampered = client.post("/api/sky/mcp/execute",
                           json={**confirm, "arguments": {"foo": "tampered"}},
                           headers=headers("848484"))
    assert tampered.status_code == 403
    accepted = client.post("/api/sky/mcp/execute", json=confirm, headers=headers("848484"))
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["approval_consumed"] is True
    assert accepted.json()["external_effect_verified"] is False
    assert client.post("/api/sky/mcp/execute", json=confirm, headers=headers("848484")).status_code == 403


def test_credentials_never_in_catalogue(context, monkeypatch):
    client, _, tmp = context
    monkeypatch.setenv("TAVILY_API_KEY", "absolutely-secret-tavily-string")
    out = client.get("/api/sky/mcp/catalogue", headers=headers()).json()
    assert "absolutely-secret-tavily-string" not in json.dumps(out)
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" not in json.dumps(out)


def test_git_hub_mcp_requires_server_side_readonly(context):
    _, _, tmp = context
    conf = json.loads(hub._config_path().read_text())
    conf["servers"]["github"] = {
        "enabled": True, "command": sys.executable, "args": ["stdio"],
        "env_keys": [], "allowed_tools": ["get_file_contents", "create_pull_request"]}
    hub._config_path().write_text(json.dumps(conf))
    with pytest.raises(hub.MCPDenied):
        hub._server_spec("github")
    conf["servers"]["github"]["args"] = ["stdio", "--read-only"]
    hub._config_path().write_text(json.dumps(conf))
    assert hub._server_spec("github")["env"]["GITHUB_READ_ONLY"] == "1"
    with pytest.raises(hub.MCPDenied):
        hub.tool_policy("github", "create_pull_request")


def test_filesystem_scoped_directory(context, monkeypatch):
    _, _, tmp = context
    script = tmp / "server.js"
    script.write_text("console.log('only example')")
    allowed = tmp / "workspace"
    allowed.mkdir()
    monkeypatch.setenv("SKY_MCP_FILES_ROOT", str(allowed))
    conf = json.loads(hub._config_path().read_text())
    conf["servers"]["filesystem"] = {
        "enabled": True, "command": sys.executable, "args": [str(script), str(allowed)],
        "env_keys": [], "allowed_tools": ["read_text_file"]}
    hub._config_path().write_text(json.dumps(conf))
    with pytest.raises(hub.MCPDenied):
        hub._server_spec("filesystem")  # solo Node
    # Sin rutas de perfiles completos, ni ampliación de carpetas vía args.
    if sys.platform == "win32":
        pytest.skip("Node executable availability is environment-dependent on Windows")
    node = "/usr/bin/node"
    if not Path(node).is_file():
        pytest.skip("Node is not installed in CI; checked only rejection")
    conf["servers"]["filesystem"]["command"] = node
    conf["servers"]["filesystem"]["args"].append(str(tmp))
    hub._config_path().write_text(json.dumps(conf))
    with pytest.raises(hub.MCPDenied):
        hub._server_spec("filesystem")


def test_mcp_sdk_v2_contract_when_installed():
    pytest.importorskip("mcp")
    from mcp import Client, StdioServerParameters
    assert Client and StdioServerParameters


def test_fazt_context7_supabase_postgres_and_semgrep_catalogued(context):
    client, _, _ = context
    data = client.get("/api/sky/mcp/catalogue", headers=headers()).json()
    items = {row["id"]: row for row in data["servers"]}
    assert items["context7"]["transport"] == "stdio"
    assert items["supabase"]["transport"] == "remote_oauth_pending"
    assert items["postgres"]["transport"] == "stdio"
    assert items["semgrep"]["transport"] == "stdio"
    assert not items["supabase"]["active"]


def test_postgresql_mcp_must_stay_restricted(context):
    _, _, _ = context
    file = hub._config_path()
    data = json.loads(file.read_text())
    data["servers"]["postgres"] = {
        "enabled": True, "command": sys.executable, "args": ["--access-mode=unrestricted"],
        "env_keys": [], "allowed_tools": ["list_schemas", "execute_sql"]
    }
    file.write_text(json.dumps(data))
    with pytest.raises(hub.MCPDenied):
        hub._server_spec("postgres")
    data["servers"]["postgres"]["args"] = ["--access-mode=restricted"]
    file.write_text(json.dumps(data))
    assert hub._server_spec("postgres")["id"] == "postgres"
    with pytest.raises(hub.MCPDenied):
        hub.tool_policy("postgres", "execute_sql")
