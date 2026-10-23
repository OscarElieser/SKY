"""Pruebas de aceptación y regresión para SKY JARVIS Fase 1 (Windows Local).

Cubre:
1. Reconocimiento de nuevas aplicaciones autorizadas (Word, Excel, PowerPoint, VS Code, Chrome, Edge, Firefox).
2. Interpretación de órdenes de gestión de ventanas (listar, cambiar/enfocar, minimizar, restaurar).
3. Resolución real y lanzamiento seguro de aplicaciones verificando existencia en el sistema.
4. Rechazo garantizado de aplicaciones y comandos no autorizados (cmd, powershell, rutas arbitrarias).
5. Ejecución segura en el agente local y formato de respuesta para el usuario.
"""
import pytest
from neural_core import dispositivos
from neural_core.sky_voice_actions import execute_safe_local, SAFE_ACTIONS
from neural_core.windows_controller import (
    find_installed_app, launch_authorized_app, AUTHORIZED_APPS,
    list_user_windows, focus_user_window, minimize_user_window, restore_user_window
)
import agente_dispositivo as agent


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



@pytest.mark.parametrize('text,expected_app', [
    ('SKY, abre Word', 'word'),
    ('SKY abrí Microsoft Word', 'word'),
    ('SKY, abre Excel', 'excel'),
    ('abrí hoja de calculo', 'excel'),
    ('SKY, abre PowerPoint', 'powerpoint'),
    ('inicia presentaciones', 'powerpoint'),
    ('SKY, abre Visual Studio Code', 'vscode'),
    ('abrí vs code', 'vscode'),
    ('SKY, abre vscode', 'vscode'),
    ('SKY, abre Chrome', 'chrome'),
    ('abrí Google Chrome', 'chrome'),
    ('SKY, abre Edge', 'edge'),
    ('abrí Microsoft Edge', 'edge'),
    ('SKY, abre Firefox', 'firefox'),
    ('abrí Mozilla Firefox', 'firefox'),
    ('SKY, abre la calculadora', 'calculator'),
    ('abrí el bloc de notas', 'text_editor'),
    ('abrí el explorador de archivos', 'file_manager'),
    ('abrí el navegador', 'browser'),
])
def test_interpretar_nuevas_apps(text, expected_app):
    res = dispositivos.interpret_command(text)
    assert res is not None, f"No reconoció la orden: {text}"
    assert res['action'] == 'launch_app'
    assert res['params']['app'] == expected_app


@pytest.mark.parametrize('text,expected_subaction,expected_target', [
    ('SKY, lista las ventanas', 'list', None),
    ('que ventanas tengo abiertas', 'list', None),
    ('cuales ventanas estan abiertas', 'list', None),
    ('SKY ver ventanas', 'list', None),
    ('SKY, cambia a la ventana de Word', 'focus', 'word'),
    ('pasa a la ventana de Excel', 'focus', 'excel'),
    ('ve a Chrome', 'focus', 'chrome'),
    ('enfoca Spotify', 'focus', 'spotify'),
    ('SKY, minimiza la ventana de Word', 'minimize', 'word'),
    ('minimiza la ventana', 'minimize', ''),
    ('SKY, restaura la ventana de Excel', 'restore', 'excel'),
    ('restaura la ventana', 'restore', ''),
])
def test_interpretar_comandos_ventanas(text, expected_subaction, expected_target):
    res = dispositivos.interpret_command(text)
    assert res is not None, f"No reconoció la orden de ventana: {text}"
    assert res['action'] == 'window_action'
    assert res['params']['subaction'] == expected_subaction
    if expected_target is not None:
        assert res['params'].get('target') == expected_target


def test_rechazo_apps_no_autorizadas_y_peligrosas():
    peligrosas = [
        'SKY, abre cmd',
        'abre cmd.exe',
        'SKY, ejecuta powershell',
        'abrí terminal',
        'inicia regedit',
        'ejecuta format c:',
        'elimina system32',
        'abre bash',
    ]
    for p in peligrosas:
        res = dispositivos.interpret_command(p)
        if res is not None:
            # Nunca debe resolver a una app sensible
            assert res['action'] != 'launch_app' or res['params']['app'] not in [
                'cmd', 'powershell', 'regedit', 'terminal', 'bash'
            ]


def test_windows_controller_catalogo_y_autorizacion():
    assert 'word' in AUTHORIZED_APPS
    assert 'excel' in AUTHORIZED_APPS
    assert 'powerpoint' in AUTHORIZED_APPS
    assert 'vscode' in AUTHORIZED_APPS
    assert 'chrome' in AUTHORIZED_APPS
    assert 'edge' in AUTHORIZED_APPS
    assert 'firefox' in AUTHORIZED_APPS

    with pytest.raises(ValueError, match="no está autorizada"):
        launch_authorized_app('powershell')

    with pytest.raises(ValueError, match="no está autorizada"):
        launch_authorized_app('cmd')


def test_windows_controller_resolucion_existencia(monkeypatch):
    # Probar que una app no instalada levanta RuntimeError explícito
    monkeypatch.setattr("neural_core.windows_controller.find_installed_app", lambda app: None)
    with pytest.raises(RuntimeError, match="no se encuentra instalada"):
        launch_authorized_app('word')


def test_windows_controller_lanzamiento_simulado(monkeypatch):
    monkeypatch.setattr("neural_core.windows_controller.find_installed_app", lambda app: "C:\\Fake\\winword.exe")
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: type("FakeProc", (), {"pid": 12345})())

    res = launch_authorized_app('word')
    assert res['ok'] is True
    assert res['app'] == 'word'
    assert res['pid'] == 12345
    assert 'inició' in res['message'] or 'abrió' in res['message']


def test_agente_execute_action_window_list(monkeypatch):
    fake_wins = [{'hwnd': 100, 'title': 'Documento - Word'}, {'hwnd': 200, 'title': 'Datos - Excel'}]
    monkeypatch.setattr("agente_dispositivo.list_user_windows", lambda: fake_wins)

    res = agent.execute_action('window_action', {'subaction': 'list'})
    assert res['ok'] is True
    assert res['windows'] == fake_wins


def test_agente_execute_action_window_focus(monkeypatch):
    monkeypatch.setattr("agente_dispositivo.focus_user_window", lambda target: {'ok': True, 'title': 'Word', 'message': 'Ventana enfocada: «Word».'})

    res = agent.execute_action('window_action', {'subaction': 'focus', 'target': 'word'})
    assert res['ok'] is True
    assert 'enfocada' in res['message']


def test_agente_execute_action_rechaza_subaccion_invalida():
    with pytest.raises(ValueError, match="Subacción de ventana no autorizada"):
        agent.execute_action('window_action', {'subaction': 'destruir_todo'})


def test_voice_actions_window_list(monkeypatch):
    fake_wins = [{'hwnd': 100, 'title': 'Documento 1'}, {'hwnd': 200, 'title': 'Navegador'}]
    monkeypatch.setattr("neural_core.sky_voice_actions.local_agent_credentials", lambda: ("http://127.0.0.1:8765", "token123456789012345678901234567890"))
    monkeypatch.setattr("neural_core.sky_voice_actions.call_device", lambda *args: {'ok': True, 'windows': fake_wins})

    msg = execute_safe_local({'action': 'window_action', 'params': {'subaction': 'list'}})
    assert "Ventanas abiertas" in msg
    assert "Documento 1" in msg
    assert "Navegador" in msg


@pytest.mark.parametrize('text,expected_query', [
    ('SKY, abre YouTube y pon Queen Bohemian Rhapsody', 'Queen Bohemian Rhapsody'),
    ('busca en youtube tutoriales de python', 'tutoriales de python'),
    ('pon en youtube shakira', 'shakira'),
    ('pon musica de michael jackson', 'michael jackson'),
    ('reproduce coldplay', 'coldplay'),
])
def test_interpretar_media_youtube(text, expected_query):
    res = dispositivos.interpret_command(text)
    assert res is not None, f"No reconoció orden multimedia: {text}"
    assert res['action'] == 'open_url'
    assert 'youtube.com' in res['params']['url']
    assert res['params'].get('service') == 'youtube'
    assert expected_query.lower() in res['params'].get('query', '').lower()


def test_interpretar_busqueda_google():
    res = dispositivos.interpret_command("busca en google inteligencia artificial")
    assert res is not None
    assert res['action'] == 'open_url'
    assert 'google.com/search' in res['params']['url']
    assert res['params'].get('service') == 'google'
    assert 'inteligencia artificial' in res['params'].get('query', '')


@pytest.mark.parametrize('text,expected_url', [
    ('SKY, abre WhatsApp', 'web.whatsapp.com'),
    ('abre Facebook', 'facebook.com'),
    ('abre Instagram', 'instagram.com'),
    ('abre TikTok', 'tiktok.com'),
    ('abre Twitter', 'x.com'),
    ('abre LinkedIn', 'linkedin.com'),
])
def test_interpretar_redes_sociales_open(text, expected_url):
    res = dispositivos.interpret_command(text)
    assert res is not None
    assert res['action'] == 'open_url'
    assert expected_url in res['params']['url']


@pytest.mark.parametrize('text,expected_subaction,expected_plat', [
    ('publica en facebook un saludo a la comunidad', 'post', 'facebook'),
    ('crea un post para instagram sobre tecnología', 'post', 'instagram'),
    ('sube foto a tiktok', 'post', 'tiktok'),
    ('envia mensaje por whatsapp a Carlos diciendo ya voy', 'message', 'whatsapp'),
    ('comenta en la publicacion diciendo felicitaciones', 'comment', 'redes'),
])
def test_interpretar_social_actions(text, expected_subaction, expected_plat):
    res = dispositivos.interpret_command(text)
    assert res is not None
    assert res['action'] == 'social_action'
    assert res['params']['subaction'] == expected_subaction
    assert res['params']['platform'] == expected_plat


@pytest.mark.parametrize('text,expected_target', [
    ('abre mi carpeta de documentos', 'documentos'),
    ('abre mi carpeta de descargas', 'descargas'),
    ('abre el archivo balance.xlsx', 'balance.xlsx'),
    ('abre el documento reporte.docx', 'reporte.docx'),
    ('abre el pdf manual.pdf', 'manual.pdf'),
])
def test_interpretar_open_file(text, expected_target):
    res = dispositivos.interpret_command(text)
    assert res is not None
    assert res['action'] == 'open_file'
    assert res['params']['target'] == expected_target


def test_windows_controller_open_special_folder(monkeypatch):
    from neural_core import windows_controller
    monkeypatch.setattr("os.startfile", lambda p: None, raising=False)
    res = windows_controller.open_local_file_or_folder("documentos")
    assert res['ok'] is True
    assert res['type'] == 'folder'


