"""Pruebas sin teléfono: seguridad, expiración, cola y liberación de SQLite."""
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from neural_core import sky_mobile_agent as m


@pytest.fixture
def isolated_db(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        monkeypatch.setenv("SKY_MOBILE_AGENT_DB", str(Path(directory) / "events.db"))
        yield Path(directory) / "events.db"


def test_pair_one_time_and_revocation(isolated_db):
    code = m.pairing_code()["code"]
    device = m.pair(code, "Android Personal")
    with pytest.raises(PermissionError):
        m.pair(code, "Android Personal")
    assert m.devices()[0]["id"] == device["device_id"]
    with pytest.raises(PermissionError):
        m.poll(device["device_id"], "invalid-token")
    cmd = m.queue(device["device_id"], "youtube")
    item = m.poll(device["device_id"], device["token"])["command"]
    assert item["id"] == cmd["command_id"]
    assert m.poll(device["device_id"], device["token"])["command"] is None
    assert m.complete(device["device_id"], device["token"], cmd["command_id"], "REJECTED")["state"] == "REJECTED"
    with pytest.raises(ValueError):
        m.complete(device["device_id"], device["token"], cmd["command_id"], "SENT")
    m.revoke(device["device_id"], device["token"])
    assert m.devices() == []
    with pytest.raises(PermissionError):
        m.poll(device["device_id"], device["token"])


def test_home_status_is_readonly_and_respects_revocation(isolated_db):
    code = m.pairing_code()["code"]
    paired = m.pair(code, "Android Personal")
    device_id, token = paired["device_id"], paired["token"]
    assert m.device_status(device_id, token) == {"authorized": True}
    with pytest.raises(PermissionError):
        m.device_status(device_id, "incorrect")
    # A status request must not consume a queued command.
    command = m.queue(device_id, "youtube")
    m.device_status(device_id, token)
    polled = m.poll(device_id, token)["command"]
    assert polled["id"] == command["command_id"]
    m.revoke(device_id, token)
    with pytest.raises(PermissionError):
        m.device_status(device_id, token)


def test_strict_allowlist_and_voice(isolated_db):
    assert m.parse_voice("SKY, abrí WhatsApp en mi teléfono") == "whatsapp"
    assert m.parse_voice("Abre YouTube en el celular") == "youtube"
    assert m.parse_voice("abre configuraciones en mi telefono") is None
    assert m.parse_voice("abre youtube en mi telefono y borra todo") is None
    assert "emparejá" in m.voice_request("abre youtube en mi teléfono")["mensaje"]
    device = m.pair(m.pairing_code()["code"], "Mi Android")
    r = m.voice_request("SKY abre Chrome en mi telefono")
    assert r["mobile_command_id"]
    assert m.poll(device["device_id"], device["token"])["command"]["target"] == "chrome"
    with pytest.raises(ValueError):
        m.queue(device["device_id"], "arbitrary.package")


def test_no_leaked_windows_sqlite_handles(isolated_db):
    m.devices()
    device = m.pair(m.pairing_code()["code"], "Mi Android")
    m.queue(device["device_id"], "gmail")
    m.poll(device["device_id"], device["token"])
    # En Windows falla con WinError 32 si queda abierta alguna conexión.
    isolated_db.unlink()
    assert not isolated_db.exists()


def test_expired_pair_and_commands(isolated_db, monkeypatch):
    orig = m.time.time
    with patch.object(m.time, "time", return_value=1000.0):
        code = m.pairing_code()["code"]
    with patch.object(m.time, "time", return_value=1400.0):
        with pytest.raises(PermissionError):
            m.pair(code, "Mi Android")
    with patch.object(m.time, "time", return_value=1500.0):
        pair = m.pair(m.pairing_code()["code"], "Mi Android")
        cmd = m.queue(pair["device_id"], "youtube")
    with patch.object(m.time, "time", return_value=1700.0):
        assert m.poll(pair["device_id"], pair["token"])["command"] is None
        assert m.command_status(pair["device_id"], cmd["command_id"])["state"] == "EXPIRED"


def test_sentinel_mobile_scopes_are_exact_and_keep_owner_paths_private(monkeypatch):
    """SENTINEL must not demand the Windows owner key for limited mobile tokens.

    This tests routing only; the mobile endpoint independently validates its
    one-use code or device/chat token before allowing any operation.
    """
    from types import SimpleNamespace
    from metaverse import sentinel
    from neural_core import sentinel_identidad as ident

    monkeypatch.setattr(ident, "solo_local", lambda: False)
    device_id = "a" * 32
    command_id = "b" * 32
    allowed = [
        ("POST", "/api/sky/mobile-agent/pair/complete"),
        ("GET", f"/api/sky/mobile-agent/devices/{device_id}/home-status"),
        ("GET", f"/api/sky/mobile-agent/devices/{device_id}/next"),
        ("POST", f"/api/sky/mobile-agent/devices/{device_id}/revoke-self"),
        ("POST", f"/api/sky/mobile-agent/devices/{device_id}/commands/{command_id}/complete"),
        ("POST", "/api/sky/mobile-chat/pair"),
        ("POST", "/api/sky/mobile-chat/chat"),
    ]
    for method, path in allowed:
        request = SimpleNamespace(
            method=method,
            url=SimpleNamespace(path=path),
            client=SimpleNamespace(host="100.115.243.4"),
            headers={},
        )
        assert sentinel.es_movil_con_token(method, path)
        assert sentinel.verificar(request) == (True, 200, "")

    forbidden = [
        ("POST", "/api/sky/mobile-agent/pair/start"),
        ("GET", "/api/sky/mobile-agent/devices"),
        ("POST", f"/api/sky/mobile-agent/devices/{device_id}/commands"),
        ("POST", "/api/sky/mobile-chat/invite"),
        ("POST", "/api/sky/mobile-chat/revoke"),
        ("GET", "/api/sky/mobile-agent/pair/complete"),
        ("DELETE", f"/api/sky/mobile-agent/devices/{device_id}/revoke-self"),
        ("GET", f"/api/sky/mobile-agent/devices/{device_id}/next/admin"),
        ("GET", "/api/sky/mobile-agent/devices/invalid/home-status"),
        ("POST", f"/api/sky/mobile-agent/devices/{device_id}/commands/invalid/complete"),
        ("POST", "/api/developer/repl"),
        ("POST", "/api/sky/mobile-agent/pair/complete/anything"),
    ]
    for method, path in forbidden:
        assert not sentinel.es_movil_con_token(method, path), (method, path)
