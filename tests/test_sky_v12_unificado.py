"""SKY v12 — fusión JARVIS + Asistente Personal, HUD, Home Assistant, modo local e Intérprete."""
import json
import socket
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import agente_dispositivo as agent
import iniciar_sky_autonomo as launcher
from neural_core import dispositivos, sky_home_assistant as casa
from neural_core import sky_capacidades as caps
from neural_core import sky_asistente_personal as asis
from neural_core import windows_controller as wc


@pytest.fixture(autouse=True)
def _sin_autorizaciones_por_entorno(monkeypatch):
    for var in ('SKY_WINDOW_ACTIONS', 'SKY_ALL_CAPABILITIES', 'SKY_NOTES_ENABLED', 'SKY_LOCAL_ONLY',
                'SKY_HA_URL', 'SKY_HA_TOKEN', 'SKY_HA_TOKEN_FILE', 'SKY_HA_AUTO', 'YOUTUBE_API_KEY', 'GOOGLE_API_KEY'):
        monkeypatch.delenv(var, raising=False)


# ------------------------------------------------------------------ agente: la política se aplica de verdad

@pytest.mark.parametrize('action,params', [
    ('window_action', {'subaction': 'close', 'target': 'word'}),
    ('organize_windows', {}),
    ('type_text', {'text': 'hola'}),
    ('open_file', {'target': 'documentos'}),
    ('note_create', {'name': 'x', 'content': 'y', 'confirmed': True}),
    ('clipboard_get', {}),
])
def test_capacidades_sensibles_exigen_autorizacion(action, params, monkeypatch):
    llamadas = []
    monkeypatch.setattr(agent, 'close_user_window', lambda t: llamadas.append(t))
    monkeypatch.setattr(agent, 'type_text_in_active_window', lambda t: llamadas.append(t))
    with pytest.raises(agent.Desactivada):
        agent.execute_action(action, params)
    assert llamadas == []


def test_variables_jarvis_siguen_autorizando(monkeypatch):
    monkeypatch.setenv('SKY_WINDOW_ACTIONS', '1')
    monkeypatch.setattr(agent, 'list_user_windows', lambda: [{'hwnd': 1, 'title': 'Word'}])
    res = agent.execute_action('window_action', {'subaction': 'list'})
    assert res['ok'] and res['windows'][0]['title'] == 'Word' and res['command_id']
    with pytest.raises(agent.Desactivada):
        agent.execute_action('type_text', {'text': 'x'})


def test_acciones_de_interfaz_no_se_reportan_verificadas():
    res = agent.execute_action('player_control', {'subaction': 'mode_mini'})
    assert res['ok'] and res['status'] == 'UI'
    assert agent.execute_action('holographic_window', {'message': 'ok'})['status'] == 'UI'


def test_media_key_respeta_volumen_y_multimedia(monkeypatch, tmp_path):
    enviados = []
    monkeypatch.setattr(caps, 'volumen', lambda c, n=None: enviados.append(('vol', c)) or c)
    monkeypatch.setattr(caps, 'control_multimedia', lambda c: enviados.append(('media', c)) or c)
    assert agent.execute_action('media_key', {'key': 'volume_up'})['ok']
    assert agent.execute_action('media_key', {'key': 'next_track'})['ok']
    assert enviados == [('vol', 'up'), ('media', 'next')]
    pol = tmp_path / 'p.json'
    pol.write_text(json.dumps({'enabled': ['status', 'media']}), encoding='utf-8')
    monkeypatch.setattr(caps, 'POLICY_PATH', pol)
    with pytest.raises(agent.Desactivada):
        agent.execute_action('media_key', {'key': 'mute'})      # volumen desactivado


def test_tareas_reales_y_sin_exito_falso(monkeypatch):
    res = agent.execute_action('task_action', {'subaction': 'append', 'modification': 'fotos'})
    assert res['ok'] is False or 'Agregué' in res['message']
    with pytest.raises(ValueError):
        agent.execute_action('task_action', {'subaction': 'formatear_disco'})


def test_servidor_expone_tareas_e_historial():
    server = ThreadingHTTPServer(('127.0.0.1', 0), agent.Handler)
    server.secret = 'clave-v12-' + 'q' * 40
    hilo = threading.Thread(target=server.serve_forever, daemon=True)
    hilo.start()
    base = f'http://127.0.0.1:{server.server_address[1]}'
    try:
        import urllib.request
        for ruta in ('/tasks', '/actions_history'):
            req = urllib.request.Request(base + ruta, headers={'Authorization': 'Bearer ' + server.secret})
            with urllib.request.urlopen(req, timeout=3) as r:
                assert json.loads(r.read())['ok'] is True
        assert dispositivos.call_device(base, server.secret, 'status')['agent'] == 'SKY Desktop Agent'
    finally:
        server.shutdown(); server.server_close(); hilo.join(2)


# ------------------------------------------------------------------ windows_controller endurecido

def _hogar(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    (home / 'Documents').mkdir(parents=True)
    (home / 'Documents' / 'informe.pdf').write_bytes(b'%PDF')
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    return home


def test_abrir_documento_rechaza_rutas_y_comodines(tmp_path, monkeypatch):
    home = _hogar(tmp_path, monkeypatch)
    abiertos = []
    monkeypatch.setattr(wc, '_open_with_system', abiertos.append)
    for malo in ('../../etc/passwd', 'a/b.pdf', '*', 'inf?rme.pdf', 'x' * 300):
        with pytest.raises(ValueError):
            wc.open_local_file_or_folder(malo)
    fuera = tmp_path / 'fuera.pdf'; fuera.write_bytes(b'%PDF')
    with pytest.raises((ValueError, FileNotFoundError)):
        wc.open_local_file_or_folder(str(fuera))            # ruta absoluta fuera del perfil
    assert wc.open_local_file_or_folder('informe')['ok']
    assert wc.open_local_file_or_folder(str(home / 'Documents' / 'informe.pdf'))['ok']
    assert abiertos and all(str(home) in a for a in abiertos)


def test_sin_abridor_no_informa_exito(tmp_path, monkeypatch):
    _hogar(tmp_path, monkeypatch)
    monkeypatch.setattr(wc.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(wc.shutil, 'which', lambda name: None)
    with pytest.raises(RuntimeError):
        wc.open_local_file_or_folder('documentos')


# ------------------------------------------------------------------ supervisor

class _Otro(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"service":"otro"}')
    def log_message(self, *a):
        pass


def test_supervisor_no_cierra_programas_ajenos(monkeypatch):
    srv = ThreadingHTTPServer(('127.0.0.1', 0), _Otro)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True); hilo.start()
    puerto = srv.server_address[1]
    matados = []
    monkeypatch.setattr(launcher, 'kill_process_by_pid', lambda pid: matados.append(pid) or True)
    monkeypatch.setattr(launcher, 'get_pid_using_port', lambda p: 999)
    try:
        assert launcher.es_servicio_sky(puerto) is False
        assert launcher.clean_port_conflicts([puerto]) == {puerto: False}
        assert matados == []
    finally:
        srv.shutdown(); srv.server_close(); hilo.join(2)


def test_supervisor_reconoce_agente_sky():
    server = ThreadingHTTPServer(('127.0.0.1', 0), agent.Handler)
    server.secret = 'x' * 48
    hilo = threading.Thread(target=server.serve_forever, daemon=True); hilo.start()
    try:
        assert launcher.es_servicio_sky(server.server_address[1]) is True
    finally:
        server.shutdown(); server.server_close(); hilo.join(2)


def test_inicio_con_windows_usa_argumento_existente(monkeypatch):
    creados = {}
    monkeypatch.setattr(launcher, 'SkySupervisor', lambda **kw: creados.update(kw) or types.SimpleNamespace(
        start_all=lambda: None, monitor=lambda: None, stop_all=lambda: None))
    monkeypatch.setattr(launcher.signal, 'signal', lambda *a: None)
    monkeypatch.setattr(sys, 'argv', ['iniciar_sky_autonomo.py', '--minimized', '--no-voice'])
    launcher.main()
    assert creados['open_browser'] is False and creados['with_voice'] is False


# ------------------------------------------------------------------ IA 100 % local

def test_modo_solo_local_bloquea_la_nube(monkeypatch):
    from neural_core import providers
    monkeypatch.setenv('SKY_LOCAL_ONLY', '1')
    monkeypatch.setenv('GEMINI_API_KEY', 'x' * 30)
    assert providers.choose_provider('auto')[0] == 'ollama'
    with pytest.raises(providers.ProviderError):
        providers.choose_provider('gemini')


def test_respuesta_de_voz_breve_y_de_chat_completa(monkeypatch):
    from neural_core import providers, assistant
    monkeypatch.setattr(providers, 'choose_provider', lambda n='auto', area='General': ('ollama', 'llama3.2'))
    vistos = {}
    monkeypatch.setattr(providers, 'reply', lambda m, p, **k: vistos.update(voz=m, k=k) or 'Hola, Oscar.')
    monkeypatch.setattr(assistant, 'responder', lambda *a, **k: (vistos.update(chat=a) or 'Respuesta completa', []))
    assert asis.atender('¿cómo estás?', modo='voz')['mensaje'] == 'Hola, Oscar.'
    assert 'voz alta' in vistos['voz'][0]['content'] and vistos['k']['max_output_tokens'] <= 800
    assert asis.atender('explícame la relatividad', modo='chat')['mensaje'] == 'Respuesta completa'


# ------------------------------------------------------------------ intérprete combinado

@pytest.mark.parametrize('texto,accion', [
    ('pausa el video', 'player_control'),
    ('pausa la música', 'media_control'),
    ('organiza las ventanas', 'window_action'),
    ('crea una nota agenda que diga hola', 'note_create'),
    ('prepara una presentación sobre café', 'task_action'),
    ('reproduce Bad Bunny en Spotify', 'play_media'),
    ('abre mis descargas', 'open_file'),
    ('qué hay en mis descargas', 'list_path'),
    ('habla más despacio', 'voice_control'),
])
def test_prioridades_del_interprete(texto, accion):
    r = asis.interpretar(texto)
    assert r['action'] == accion and isinstance(r['params'], dict) and r['description']


def test_spotify_no_se_confunde_con_dispositivo():
    r = asis.interpretar('reproduce Bad Bunny en Spotify')
    assert r['params']['service'] == 'spotify' and 'target_device' not in r


# ------------------------------------------------------------------ Home Assistant

ENTIDADES = [
    {'entity_id': 'light.sala', 'domain': 'light', 'state': 'off', 'name': 'Luz Sala'},
    {'entity_id': 'light.cuarto', 'domain': 'light', 'state': 'on', 'name': 'Luz Cuarto'},
    {'entity_id': 'scene.cine', 'domain': 'scene', 'state': 'scening', 'name': 'Cine'},
    {'entity_id': 'lock.puerta_principal', 'domain': 'lock', 'state': 'unlocked', 'name': 'Puerta principal'},
    {'entity_id': 'cover.porton', 'domain': 'cover', 'state': 'closed', 'name': 'Portón'},
    {'entity_id': 'climate.aire', 'domain': 'climate', 'state': 'cool', 'name': 'Aire sala'},
]


@pytest.fixture
def ha(monkeypatch):
    monkeypatch.setenv('SKY_HA_URL', 'http://homeassistant.local:8123')
    monkeypatch.setenv('SKY_HA_TOKEN', 't' * 40)
    monkeypatch.setattr(casa, 'estados', lambda forzar=False: ENTIDADES)
    enviados = []
    monkeypatch.setattr(casa, '_peticion', lambda m, ruta, cuerpo=None, timeout=6: enviados.append((m, ruta, cuerpo)) or [])
    return enviados


def test_ha_url_segura():
    assert casa.validar_url('http://192.168.1.20:8123') == 'http://192.168.1.20:8123'
    assert casa.validar_url('https://casa.example.com') == 'https://casa.example.com'
    for mala in ('http://casa.example.com', 'ftp://x', 'http://u:p@192.168.1.2', 'http://192.168.1.2/api'):
        with pytest.raises(ValueError):
            casa.validar_url(mala)


def test_ha_sin_configurar_no_interfiere():
    assert casa.interpretar('enciende la luz de la sala') is None
    assert casa.resumen() == {'configurado': False}


def test_ha_interpreta_solo_entidades_reales(ha):
    o = casa.interpretar('SKY, enciende la luz de la sala')
    assert o['service'] == 'light.turn_on' and o['entity_ids'] == ['light.sala'] and not o['requiere_confirmacion']
    assert casa.interpretar('apaga las luces del garaje') is None          # no existe
    assert casa.interpretar('activa la escena cine')['service'] == 'scene.turn_on'
    t = casa.interpretar('pon el aire a 22 grados')
    assert t['service'] == 'climate.set_temperature' and t['data'] == {'temperature': 22} and t['requiere_confirmacion']
    assert casa.interpretar('abre el portón')['requiere_confirmacion'] is True
    assert casa.interpretar('cierra la puerta principal')['service'] == 'lock.lock'
    assert casa.interpretar('abre la puerta principal') is None             # nunca se abre una cerradura por voz


def test_ha_ejecuta_solo_lo_permitido(ha):
    assert casa.ejecutar('light.turn_off', ['light.cuarto'])['ok']
    assert ha[-1] == ('POST', '/api/services/light/turn_off', {'entity_id': ['light.cuarto']})
    for servicio, ids in (('light.delete', ['light.sala']), ('alarm_control_panel.alarm_disarm', ['light.sala']),
                          ('light.turn_on', ['light.inexistente']), ('light.turn_on', ['scene.cine']),
                          ('climate.set_temperature', ['climate.aire'])):
        with pytest.raises(ValueError):
            casa.ejecutar(servicio, ids, {'temperature': 99})


def test_ha_en_el_asistente(ha):
    r = asis.atender('apaga la luz del cuarto')
    assert r['tipo'] == 'casa' and r['propuesta']['entity_ids'] == ['light.cuarto']


# ------------------------------------------------------------------ Intérprete de código

def test_interprete_siempre_confirma(monkeypatch):
    import sky_interprete
    falso = types.SimpleNamespace(llm=types.SimpleNamespace(model='', api_base=''), offline=False,
                                  auto_run=True, system_message='base', chat=lambda: None)
    monkeypatch.setitem(sys.modules, 'interpreter', types.SimpleNamespace(interpreter=falso))
    sky_interprete.main([])
    assert falso.auto_run is False and falso.offline is True and falso.llm.model.startswith('ollama/')
    assert 'SKY' in falso.system_message
    monkeypatch.setenv('SKY_LOCAL_ONLY', '1')
    with pytest.raises(SystemExit):
        sky_interprete.main(['--modelo', 'gpt-4o'])


# ------------------------------------------------------------------ cabeceras de seguridad (requiere FastAPI)

def _app_segura():
    pytest.importorskip('fastapi')
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from metaverse.security_v101 import install
    app = FastAPI()
    app.get('/')(lambda: {'ok': True})
    app.get('/office')(lambda: {'ok': True})
    install(app)
    return TestClient(app)


def test_marcos_solo_dentro_de_sky():
    c = _app_segura()
    r = c.get('/office')
    assert r.headers['X-Frame-Options'] == 'DENY' and "frame-ancestors 'none'" in r.headers['Content-Security-Policy']
    r = c.get('/office', headers={'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Site': 'same-origin'})
    assert r.headers['X-Frame-Options'] == 'SAMEORIGIN' and "frame-ancestors 'self'" in r.headers['Content-Security-Policy']
    r = c.get('/office', headers={'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Site': 'cross-site'})
    assert r.headers['X-Frame-Options'] == 'DENY'


def test_youtube_solo_en_el_hud():
    c = _app_segura()
    assert 'youtube-nocookie.com' in c.get('/').headers['Content-Security-Policy']
    assert 'youtube' not in c.get('/office').headers['Content-Security-Policy']
