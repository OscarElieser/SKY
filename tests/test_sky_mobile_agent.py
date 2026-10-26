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
