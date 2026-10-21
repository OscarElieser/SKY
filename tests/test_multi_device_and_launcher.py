"""Pruebas unitarias para enrutamiento multidispositivo, protocolo seguro y lanzador autónomo."""
import json
import pytest
from pathlib import Path
from neural_core import dispositivos
from neural_core.holographic_ui import generate_holographic_scene_html
import iniciar_sky_autonomo as launcher


def test_device_targeting_in_commands():
    # 1. Aplicación en laptop
    cmd1 = dispositivos.interpret_command("SKY, abrí Word en mi laptop")
    assert cmd1 is not None
    assert cmd1["action"] == "launch_app"
    assert cmd1["params"]["app"] == "word"
    assert cmd1.get("target_device") == "laptop"

    # 2. YouTube en celular
    cmd2 = dispositivos.interpret_command("SKY, abrí YouTube en mi celular")
    assert cmd2 is not None
    assert cmd2["action"] == "open_url"
    assert cmd2.get("target_device") == "celular"

    # 3. Música en computadora
    cmd3 = dispositivos.interpret_command("SKY, reproducí Queen en mi computadora")
    assert cmd3 is not None
    assert cmd3["action"] == "open_url"
    assert "queen" in cmd3["params"]["query"].lower()
    assert cmd3.get("target_device") == "computadora"

    # 4. Documentos en laptop
    cmd4 = dispositivos.interpret_command("SKY, abrí mis documentos en la laptop")
    assert cmd4 is not None
    assert cmd4["action"] == "open_file"
    assert cmd4["params"]["target"] == "documentos"
    assert cmd4.get("target_device") == "laptop"

    # 5. Comando general sin dispositivo explícito
    cmd5 = dispositivos.interpret_command("consulta el estado de mi computadora")
    assert cmd5 is not None
    assert cmd5["action"] == "status"
    assert "target_device" not in cmd5


def test_device_platform_capabilities():
    assert "windows" in dispositivos.DEVICE_PLATFORMS
    assert "android" in dispositivos.DEVICE_PLATFORMS
    assert "ios" in dispositivos.DEVICE_PLATFORMS

    win_caps = dispositivos.DEVICE_PLATFORMS["windows"]["capabilities"]
    android_caps = dispositivos.DEVICE_PLATFORMS["android"]["capabilities"]
    ios_caps = dispositivos.DEVICE_PLATFORMS["ios"]["capabilities"]

    # Windows soporta automatización de ventanas y tecleo
    assert "window_action" in win_caps
    assert "type_text" in win_caps
    assert "launch_app" in win_caps

    # Android e iOS tienen restricciones de sandbox
    assert "window_action" not in android_caps
    assert "window_action" not in ios_caps
    assert "open_url" in android_caps
    assert "open_url" in ios_caps


def test_device_pairing_and_revocation(tmp_path, monkeypatch):
    test_db = tmp_path / "paired_devices.json"
    monkeypatch.setattr(dispositivos, "_REGISTRY", test_db)

    # Emparejar dispositivo
    dev = dispositivos.pair_device("Mi Teléfono Android", "https://telefono.tailscale.net", platform="android")
    assert dev["name"] == "Mi Teléfono Android"
    assert dev["platform"] == "android"
    assert dev["revoked"] is False

    paired = dispositivos.paired_devices(active_only=True)
    assert len(paired) == 1
    assert paired[0]["name"] == "Mi Teléfono Android"

    # Revocar dispositivo
    ok = dispositivos.revoke_device("Mi Teléfono Android")
    assert ok is True

    # Comprobar que active_only=True lo omite
    paired_active = dispositivos.paired_devices(active_only=True)
    assert len(paired_active) == 0

    # Comprobar que active_only=False lo mantiene con revoked=True
    all_devs = dispositivos.paired_devices(active_only=False)
    assert len(all_devs) == 1
    assert all_devs[0]["revoked"] is True


def test_route_and_execute_capability_enforcement(tmp_path, monkeypatch):
    test_db = tmp_path / "paired_devices.json"
    monkeypatch.setattr(dispositivos, "_REGISTRY", test_db)

    # Registrar un iPhone
    dispositivos.pair_device("Mi iPhone", "https://iphone.tailscale.net", platform="ios")

    # Intentar ejecutar acción no permitida en iOS (window_action)
    intent = {
        "action": "window_action",
        "params": {"subaction": "minimize"},
        "target_device": "Mi iPhone"
    }
    res = dispositivos.route_and_execute_device_command(intent, token="x" * 32)
    assert res["ok"] is False
    assert "no admite la acción 'window_action'" in res["message"]
    assert res["verified"] is False


def test_device_audit_logging(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    entry = dispositivos.log_device_operation("laptop-test", "launch_app", {"app": "word"}, "SUCCESS")
    assert entry["device"] == "laptop-test"
    assert entry["action"] == "launch_app"
    assert entry["status"] == "SUCCESS"

    audit_file = tmp_path / ".neuralt" / "device_audit_log.jsonl"
    assert audit_file.exists()
    lines = audit_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 1
    logged = json.loads(lines[-1])
    assert logged["device"] == "laptop-test"


def test_holographic_backend_states():
    # Estados oficiales requeridos: IDLE, LISTENING, THINKING, SPEAKING, EXECUTING, SUCCESS, ERROR
    states = ["IDLE", "LISTENING", "THINKING", "SPEAKING", "EXECUTING", "SUCCESS", "ERROR"]
    for st in states:
        html = generate_holographic_scene_html(voice_state=st)
        assert "hologram-viewport" in html
        assert "core-canvas" in html


def test_launcher_status_diagnostics():
    status = launcher.check_system_status()
    assert "agent" in status
    assert "api" in status
    assert "streamlit" in status
    assert "voice" in status
    assert status["agent"]["port"] == 8766
    assert status["api"]["port"] == 8765
    assert status["streamlit"]["port"] == 8501
