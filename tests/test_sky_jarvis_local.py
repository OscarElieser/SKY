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


@pytest.mark.parametrize("text,key", [
    ("SKY, pausa la música", "play_pause"),
    ("sky, siguiente canción", "next_track"),
    ("sky baja volumen", "volume_down"),
    ("sky silencia el audio", "mute"),
    ("sky reproduce", "play_pause"),
])
def test_interpreta_teclas_multimedia(text, key):
    from neural_core.dispositivos import interpret_command
    order = interpret_command(text)
    assert order["action"] == "media_key"
    assert order["params"] == {"key": key}


def test_media_no_ejecuta_shell_y_rechaza_teclas_arbitrarias(monkeypatch):
    import agente_dispositivo as agent
    with pytest.raises(ValueError):
        agent.execute_action("media_key", {"key": "cmd.exe"})
    calls = []
    monkeypatch.setattr(agent, "send_media_key", lambda key: calls.append(key))
    assert agent.execute_action("media_key", {"key": "play_pause"})["ok"]
    assert calls == ["play_pause"]


def test_voz_autorizada_envia_tecla_multimedia(monkeypatch):
    monkeypatch.setattr(actions, "local_agent_credentials",
                        lambda: ("http://127.0.0.1:18765", "x" * 48))
    sent = []
    monkeypatch.setattr(actions, "call_device",
                        lambda url, token, action, params: (sent.append((action, params)) or {"ok": True}))
    answer = actions.execute_safe_local({"action": "media_key", "params": {"key": "next_track"}})
    assert sent == [("media_key", {"key": "next_track"})]
    assert "No puedo confirmar" in answer
    with pytest.raises(ValueError):
        actions.execute_safe_local({"action": "media_key", "params": {"key": "delete"}})
