"""Regresiones del control local seguro. No se abre ninguna aplicación real."""
import pytest

from neural_core import sky_voice_actions as actions


def test_abre_youtube_local(monkeypatch):
    seen = {}
    monkeypatch.setattr(actions, "local_agent_credentials", lambda: ("http://127.0.0.1:8765", "x" * 48))
    def fake_call(url, token, action, params):
        seen.update(url=url, action=action, params=params)
        return {"ok": True}
    monkeypatch.setattr(actions, "call_device", fake_call)
    msg = actions.execute_safe_local({"action": "open_url", "params": {"url": "https://www.youtube.com"}})
    assert seen == {"url": "http://127.0.0.1:8765", "action": "open_url",
                    "params": {"url": "https://www.youtube.com"}}
    assert "abierto" in msg


@pytest.mark.parametrize("intent", [
    {"action": "execute_command", "params": {"cmd": "whoami"}},
    {"action": "delete_file", "params": {"path": "test"}},
    {"action": "launch_app", "params": {"app": "powershell"}},
    {"action": "open_url", "params": {"url": "file:///etc/passwd"}},
])
def test_bloquea_acciones_no_autorizadas(intent):
    with pytest.raises(ValueError):
        actions.execute_safe_local(intent)


def test_rechaza_resultado_no_confirmado(monkeypatch):
    monkeypatch.setattr(actions, "local_agent_credentials", lambda: ("http://127.0.0.1:8765", "x"*48))
    monkeypatch.setattr(actions, "call_device", lambda *a, **kw: {"ok": False})
    with pytest.raises(RuntimeError):
        actions.execute_safe_local({"action": "status", "params": {}})
