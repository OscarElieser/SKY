"""Pruebas exhaustivas para el control real del escritorio de Windows y reproductor en SKY IA."""
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
import pytest

import agente_dispositivo as agent
from neural_core import action_verifier, dispositivos, sky_voice_actions, windows_controller


@pytest.fixture(autouse=True)
def _hogar_y_permisos_v12(tmp_path, monkeypatch):
    """v12: perfil de usuario simulado (también en CI Linux) y capacidades
    autorizadas por el dueño, como exige ahora el agente."""
    home = tmp_path / 'home'
    for d in ('Documents', 'Desktop', 'Downloads', 'Pictures', 'Videos', 'Music'):
        (home / d).mkdir(parents=True)
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    monkeypatch.setenv('SKY_ALL_CAPABILITIES', '1')
    from neural_core import windows_controller
    monkeypatch.setattr(windows_controller, '_open_with_system', lambda path: None)



def test_action_verifier_lifecycle(tmp_path):
    ledger = tmp_path / "test_ledger.jsonl"
    verifier = action_verifier.ActionVerifier(ledger_file=ledger)

    rec = verifier.start_action("launch_app", "word")
    assert rec.status == "RECEIVED"
    assert rec.action == "launch_app"
    assert rec.target == "word"

    verifier.mark_running(rec.command_id)
    assert verifier.get_action(rec.command_id).status == "RUNNING"

    verifier.mark_verified(rec.command_id, {"pid": 1234, "hwnd": 999}, duration_ms=150.5)
    rec_v = verifier.get_action(rec.command_id)
    assert rec_v.status == "VERIFIED"
    assert rec_v.result["pid"] == 1234
    assert rec_v.execution_time_ms == 150.5

    # Comprobar persistencia en ledger
    history = verifier.get_recent_actions(limit=5)
    assert len(history) >= 1
    assert history[-1]["command_id"] == rec.command_id
    assert history[-1]["status"] == "VERIFIED"


def test_special_folders_resolution():
    # Comprobar que resuelve documentos reales o carpeta de usuario
    doc_path = windows_controller.resolve_windows_special_folder("documentos")
    assert doc_path is not None
    assert doc_path.exists()
    assert doc_path.is_dir()

    desk_path = windows_controller.resolve_windows_special_folder("escritorio")
    assert desk_path is not None
    assert desk_path.exists()

    dl_path = windows_controller.resolve_windows_special_folder("descargas")
    assert dl_path is not None
    assert dl_path.exists()


@pytest.mark.parametrize("phrase,expected_action,expected_target", [
    ("SKY, abrí mis documentos", "open_file", "documentos"),
    ("abrí mi carpeta de documentos", "open_file", "documentos"),
    ("SKY, abrí descargas", "open_file", "descargas"),
    ("mostrá mis fotos", "open_file", "fotos"),
    ("abrí el escritorio", "open_file", "escritorio"),
    ("SKY, buscá el archivo del proyecto", "open_file", "del proyecto"),
])
def test_nicaraguan_spanish_folders(phrase, expected_action, expected_target):
    cmd = dispositivos.interpret_command(phrase)
    assert cmd is not None, f"Fallo al interpretar: {phrase}"
    assert cmd["action"] == expected_action
    assert expected_target in cmd["params"]["target"]


@pytest.mark.parametrize("phrase,expected_app", [
    ("SKY, abrí Word y escribí una carta", "word"),
    ("SKY, abrí Excel y creá una tabla de gastos", "excel"),
    ("SKY, abrí PowerPoint y prepará cinco diapositivas", "powerpoint"),
    ("abrí la calculadora", "calculator"),
    ("abrí bloc de notas", "text_editor"),
    ("abrí Google Chrome", "chrome"),
    ("abrí Microsoft Edge", "edge"),
    ("abrí Outlook", "outlook"),
])
def test_nicaraguan_spanish_apps(phrase, expected_app):
    cmd = dispositivos.interpret_command(phrase)
    assert cmd is not None, f"Fallo al interpretar app: {phrase}"
    assert cmd["action"] == "launch_app"
    assert cmd["params"]["app"] == expected_app


@pytest.mark.parametrize("phrase,expected_action,expected_sub", [
    ("SKY, pausá el video", "player_control", "pause"),
    ("SKY, seguí reproduciendo", "player_control", "play"),
    ("SKY, poné el siguiente", "player_control", "next"),
    ("siguiente video", "player_control", "next"),
    ("anterior video", "player_control", "previous"),
    ("SKY, silenciá", "media_key", "mute"),
    ("SKY, cerrá el reproductor", "player_control", "close"),
    ("dejá YouTube en mini", "player_control", "mode_mini"),
    ("SKY, organizá las ventanas", "window_action", "organize"),
    ("volvé a Word", "window_action", "focus"),
    ("minimizá Excel", "window_action", "minimize"),
    ("restaurá la ventana", "window_action", "restore"),
])
def test_nicaraguan_multimedia_and_windows_commands(phrase, expected_action, expected_sub):
    cmd = dispositivos.interpret_command(phrase)
    assert cmd is not None, f"Fallo al interpretar comando: {phrase}"
    assert cmd["action"] == expected_action
    if "subaction" in cmd["params"]:
        assert cmd["params"]["subaction"] == expected_sub
    elif "key" in cmd["params"]:
        assert cmd["params"]["key"] == expected_sub


def test_agent_server_verification_endpoints():
    server = ThreadingHTTPServer(("127.0.0.1", 0), agent.Handler)
    server.secret = "test-token-32-chars-long-secret-key-ok"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"

    try:
        # 1. Status
        res_status = dispositivos.call_device(url, server.secret, "status")
        assert res_status["ok"] is True
        assert res_status["agent"] == "SKY Desktop Agent"

        # 2. Open file (documentos) con verificación real
        res_doc = dispositivos.call_device(url, server.secret, "open_file", {"target": "documentos"})
        assert res_doc["ok"] is True
        assert res_doc["status"] == "VERIFIED"
        assert "command_id" in res_doc
        cid = res_doc["command_id"]

        # 3. Consultar /verify_action
        import urllib.request
        req = urllib.request.Request(
            f"{url}/verify_action?command_id={cid}",
            headers={"Authorization": f"Bearer {server.secret}"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            assert data["ok"] is True
            assert data["record"]["command_id"] == cid
            assert data["record"]["status"] == "VERIFIED"

        # 4. Consultar /actions_history
        req_hist = urllib.request.Request(
            f"{url}/actions_history",
            headers={"Authorization": f"Bearer {server.secret}"}
        )
        with urllib.request.urlopen(req_hist, timeout=3) as resp:
            data_hist = json.loads(resp.read())
            assert data_hist["ok"] is True
            assert len(data_hist["actions"]) >= 1

    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_sky_voice_actions_execute_safe_local_verified(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), agent.Handler)
    server.secret = "test-voice-token-32-characters-ok-key"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    monkeypatch.setattr(sky_voice_actions, "local_agent_credentials", lambda: (f"http://127.0.0.1:{port}", server.secret))

    try:
        # Abrir documentos debe devolver confirmación verificada
        ans = sky_voice_actions.execute_safe_local({"action": "open_file", "params": {"target": "documentos"}})
        assert "Listo, ya está abierta" in ans or "abierto" in ans
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
