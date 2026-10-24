"""Regresión de memoria verificada y defensa por acceso denegado."""
import json
import sqlite3
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_NEURAL_MEMORY_DB", str(tmp_path / "memory.sqlite3"))
    monkeypatch.setenv("SKY_NEURAL_MEMORY_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("SKY_API_KEY", "sky-neural-owner-key-very-long-2026")
    monkeypatch.setenv("SKY_WORKFLOWS_DB", str(tmp_path / "workflows.sqlite3"))
    monkeypatch.setenv("SKY_WORKBENCH_DB", str(tmp_path / "workbench.sqlite3"))
    monkeypatch.setenv("SKY_SUPERVISOR_DB", str(tmp_path / "supervisor.sqlite3"))
    monkeypatch.setenv("SKY_OWNER_LOCAL_SHUTDOWN", "0")
    monkeypatch.delenv("SKY_OWNER_MFA_SECRET", raising=False)
    from neural_core import sky_sentinel_guard as sentinel
    sentinel._EVENTS.clear()
    sentinel._PENDING.clear()
    yield
    if sentinel._SHUTDOWN_TIMER:
        sentinel._SHUTDOWN_TIMER.cancel()
        sentinel._SHUTDOWN_TIMER = None


def test_explicit_memory_is_encrypted_and_owner_only(tmp_path):
    from neural_core import sky_neural_memory as neural
    secret = "Me gustan las presentaciones limpias con pocos controles"
    entry = neural.save_fact("owner", "preferencia", secret)
    assert entry["stored"] is True
    assert neural.facts()[0]["text"] == secret
    raw = Path(neural._db_path()).read_bytes()
    assert secret.encode("utf-8") not in raw
    assert neural.delete_fact(entry["id"])
    assert neural.facts() == []
    with pytest.raises(ValueError):
        neural.save_fact("other_person", "preferencia", secret)
    with pytest.raises(ValueError):
        neural.save_fact("owner", "preferencia", secret, source="untrusted_web")


def test_private_memory_requires_encryption_key(monkeypatch):
    from neural_core import sky_neural_memory as neural
    monkeypatch.delenv("SKY_NEURAL_MEMORY_KEY")
    with pytest.raises(RuntimeError):
        neural.save_fact("owner", "preferencia", "No guardés mi información en texto plano")


def test_learn_success_only_from_verified_completion():
    from neural_core import sky_neural_memory as neural
    assert not neural.record_verified_outcome("flow-unverified", ["planificador"], "completed", verified=False)
    assert not neural.record_verified_outcome("flow-pending", ["planificador"], "scheduled", verified=True)
    assert neural.record_verified_outcome("flow-real-done", ["planificador", "documentalista"], "completed", verified=True)
    assert not neural.record_verified_outcome("flow-real-done", ["planificador", "documentalista"], "completed", verified=True)
    assert neural.record_verified_outcome("flow-real-error", ["planificador"], "failed", verified=False)
    data = neural.execution_report()
    assert data["total_observations"] == 2
    assert data["completed"] == 1 and data["failed"] == 1
    assert data["by_role"]["documentalista"]["completed"] == 1
    assert data["model_weights_updated"] is False
    dbtext = Path(neural._db_path()).read_bytes()
    assert b"flow-real-done" not in dbtext  # only its SHA256 is saved


def test_api_protects_memories_from_guests_and_allows_delete():
    from metaverse.api import app
    with TestClient(app) as client:
        assert client.get("/api/sky/neural-memory/facts").status_code == 401
        auth = {"X-SKY-KEY": "sky-neural-owner-key-very-long-2026"}
        result = client.post("/api/sky/neural-memory/facts", headers=auth, json={
            "category": "correccion", "text": "Para tareas críticas pedime aprobación"
        })
        assert result.status_code == 201, result.text
        ident = result.json()["id"]
        mem = client.get("/api/sky/neural-memory/facts", headers=auth)
        assert mem.status_code == 200 and len(mem.json()["facts"]) == 1
        assert client.delete(f"/api/sky/neural-memory/facts/{ident}", headers=auth).json()["deleted"]


def test_wrong_credentials_access_denied_and_no_auto_shutdown():
    from metaverse.api import app
    from neural_core import sky_sentinel_guard as sentinel
    with TestClient(app) as client:
        answer = client.get("/api/sky/neural-memory/facts", headers={"X-SKY-KEY": "wrong-key"})
        assert answer.status_code == 401
        assert answer.json()["detail"] == "Acceso denegado"
        data=sentinel.status()
        assert data["recent_denied"] >= 1
        assert not data["shutdown_on_failed_login"]
        assert answer.headers.get("X-SKY-Access") == "denied"


def test_sentinel_rejects_unauthorized_local_shutdown():
    from neural_core import sky_sentinel_guard as sentinel
    with pytest.raises(PermissionError):
        sentinel.prepare_shutdown("203.0.113.8")
    with pytest.raises((PermissionError, RuntimeError)):
        sentinel.prepare_shutdown("127.0.0.1")


def test_shutdown_requires_explicit_owner_mfa_local_and_cancellable(monkeypatch):
    from neural_core import sky_sentinel_guard as sentinel
    monkeypatch.setenv("SKY_OWNER_LOCAL_SHUTDOWN", "1")
    monkeypatch.setattr(sentinel.platform, "system", lambda: "Windows")
    from metaverse import owner_mfa
    monkeypatch.setattr(owner_mfa, "required", lambda: True)
    started = []

    class FakeTimer:
        def __init__(self, seconds, callback):
            self.seconds = seconds
            self.callback = callback
            self.cancelled = False
            started.append(self)
        def start(self): pass
        def cancel(self): self.cancelled = True
    monkeypatch.setattr(sentinel.threading, "Timer", FakeTimer)
    ticket = sentinel.prepare_shutdown("127.0.0.1")
    assert not ticket["initiated"]
    assert ticket["expires_in"] == 60
    with pytest.raises(PermissionError):
        sentinel.shutdown_confirmed("127.0.0.1", ticket["confirmation_token"], "apagar")
    assert sentinel.shutdown_confirmed(
        "127.0.0.1", ticket["confirmation_token"], "AUTORIZO APAGAR MI EQUIPO"
    )["shutdown_scheduled"]
    assert started[0].seconds == 120
    with pytest.raises(PermissionError):
        sentinel.shutdown_confirmed(
            "127.0.0.1", ticket["confirmation_token"], "AUTORIZO APAGAR MI EQUIPO"
        )
    assert sentinel.abort_shutdown("127.0.0.1")["shutdown_aborted"]
    assert started[0].cancelled


def test_sentinel_endpoints_reject_remote_without_shutdown(monkeypatch):
    from metaverse.api import app
    from neural_core import sky_sentinel_guard as sentinel
    monkeypatch.setattr(sentinel.platform, "system", lambda: "Windows")
    monkeypatch.setenv("SKY_OWNER_LOCAL_SHUTDOWN", "1")
    from metaverse import owner_mfa
    monkeypatch.setattr(owner_mfa, "required", lambda: False)
    auth={"X-SKY-KEY":"sky-neural-owner-key-very-long-2026"}
    with TestClient(app) as client:
        status=client.get("/api/security/sentinel/status",headers=auth)
        assert status.status_code == 200
        denied=client.post("/api/security/sentinel/shutdown/prepare",headers=auth)
        assert denied.status_code == 403
        assert not sentinel._PENDING
