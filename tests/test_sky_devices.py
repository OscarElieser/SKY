import json
import threading
from http.server import ThreadingHTTPServer
import pytest
import agente_dispositivo as agent
from neural_core import dispositivos, voz_inbox
from sky_manos_libres import text_after_wake

@pytest.mark.parametrize('text,action,params',[
    ('SKY, abre la calculadora','launch_app',{'app':'calculator'}),
    ('Abre el bloc de notas','launch_app',{'app':'text_editor'}),
    ('SKY abrí YouTube','open_url',{'url':'https://www.youtube.com'}),
    ('abre Baqueano','open_url',{'url':'https://baqueanonicaragua.com'}),
    ('consulta el estado de mi computadora','status',{}),
])
def test_interpretar_ordenes(text,action,params):
    r=dispositivos.interpret_command(text)
    assert r['action']==action
    assert r['params']==params

@pytest.mark.parametrize('text', ['cómo está el clima','qué es el bitcoin','redacta un correo','abre la puerta'])
def test_no_inventa_acciones(text):
    assert dispositivos.interpret_command(text) is None

@pytest.mark.parametrize('url',[
    'http://192.168.1.5:8765','http://ejemplo.com','file:///etc/passwd',
    'https://usuario:pass@ejemplo.com','https://ejemplo.com/?token=abcd',
    'https://ejemplo.com/otra/ruta',
])
def test_rechaza_endpoints(url):
    with pytest.raises(ValueError): dispositivos.validate_endpoint(url)

def test_acepta_tls_y_loopback():
    assert dispositivos.validate_endpoint('https://mi-pc.mytailnet.ts.net/')=='https://mi-pc.mytailnet.ts.net'
    assert dispositivos.validate_endpoint('http://127.0.0.1:8765')=='http://127.0.0.1:8765'

def test_agente_permisos(monkeypatch):
    with pytest.raises(ValueError): agent.execute_action('execute_command',{'cmd':'whoami'})
    with pytest.raises(ValueError): agent.execute_action('open_url',{'url':'javascript:alert(1)'})
    with pytest.raises(ValueError): agent.execute_action('launch_app',{'app':'terminal'})
    with pytest.raises(ValueError): agent.execute_action('open_url',{'url':'http://ejemplo.com'})
    monkeypatch.setattr(agent.webbrowser,'open',lambda *args,**kwargs:True)
    assert agent.execute_action('open_url',{'url':'https://baqueanonicaragua.com'})['ok']

def test_servidor_autorizacion_aislado():
    server=ThreadingHTTPServer(('127.0.0.1',0),agent.Handler)
    server.secret='testing-secure-key-'+('x'*40)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    url=f'http://127.0.0.1:{server.server_address[1]}'
    try:
        with pytest.raises(RuntimeError): dispositivos.call_device(url,'z'*48,'status')
        response=dispositivos.call_device(url,server.secret,'status')
        assert response['ok'] and 'device' in response
        assert set(response['capabilities']) == {'status','open_url','launch_app','media_key'}
    finally:
        server.shutdown();server.server_close();thread.join(2)

def test_registro_sin_guardar_token(tmp_path,monkeypatch):
    db=tmp_path/'paired_devices.json'
    monkeypatch.setattr(dispositivos,'_REGISTRY',db)
    dispositivos.save_device('Mi PC','https://pc.test.ts.net')
    assert dispositivos.paired_devices()[0]['name']=='Mi PC'
    assert 'token' not in db.read_text()
    dispositivos.remove_device('Mi PC')
    assert dispositivos.paired_devices()==[]

def test_voz_activacion():
    assert text_after_wake('quiero saber la hora') is None
    assert text_after_wake('sky abre youtube') == 'abre youtube'
    assert text_after_wake('SKY, busca información') == 'busca información'

def test_voz_inbox(tmp_path,monkeypatch):
    monkeypatch.setattr(voz_inbox,'INBOX',tmp_path/'voice_inbox.json')
    item=voz_inbox.add_inbox('abre google',dispositivos.interpret_command('abre google'))
    assert voz_inbox.read_inbox()[0]['id']==item['id']
    voz_inbox.dismiss_inbox(item['id'])
    assert voz_inbox.read_inbox()==[]


def test_transcripcion_gemini_simulada(monkeypatch):
    from neural_core import voz
    historial=[]
    class Models:
        def generate_content(self,**kw):
            historial.append(kw)
            return type('R',(),{'text':'SKY abre BAQUEANO'})()
    class Client:
        models=Models()
        def close(self): historial.append('closed')
    import sys, types
    fake_genai=types.ModuleType('google.genai')
    fake_genai.types=types.SimpleNamespace(
        Part=types.SimpleNamespace(from_bytes=lambda data,mime_type: types.SimpleNamespace(
            inline_data=types.SimpleNamespace(data=data), mime_type=mime_type)))
    monkeypatch.setitem(sys.modules,'google.genai',fake_genai)
    monkeypatch.setattr(voz,'_cliente',lambda:Client())
    result=voz.transcribir_audio(b'RIFF' + b'0'*48)
    assert result=='SKY abre BAQUEANO'
    assert 'closed' in historial
    assert historial[0]['contents'][0].inline_data.data.startswith(b'RIFF')


def test_transcripcion_rechaza_formatos(monkeypatch):
    from neural_core import voz
    with pytest.raises(ValueError): voz.transcribir_audio(b'', 'audio/wav')
    with pytest.raises(ValueError): voz.transcribir_audio(b'datos','audio/mpeg')


def test_resolve_youtube_queen_embeddable():
    from neural_core.multimedia import resolve_youtube_video, KNOWN_EMBEDDING_BLOCKED
    res = resolve_youtube_video("Queen")
    assert res["video_id"] not in KNOWN_EMBEDDING_BLOCKED
    assert res["embeddable"] is True
    assert len(res["candidates"]) >= 2
    assert "vbvyNnw8Qjg" in [c["id"] for c in res["candidates"]]


def test_interpret_player_control_modes():
    from neural_core.dispositivos import interpret_command
    m1 = interpret_command("SKY, mostrá el video en mini")
    assert m1["action"] == "player_control"
    assert m1["params"]["subaction"] == "mode_mini"

    m2 = interpret_command("SKY, ampliá la ventana")
    assert m2["action"] == "player_control"
    assert m2["params"]["subaction"] == "mode_expanded"

    m3 = interpret_command("SKY, ponelo en pantalla completa")
    assert m3["action"] == "player_control"
    assert m3["params"]["subaction"] == "mode_fullscreen"

    m4 = interpret_command("SKY, volvé al tamaño normal")
    assert m4["action"] == "player_control"
    assert m4["params"]["subaction"] == "mode_normal"

    m5 = interpret_command("SKY, cerrá el reproductor")
    assert m5["action"] == "player_control"
    assert m5["params"]["subaction"] == "close"

    m6 = interpret_command("SKY, siguiente video")
    assert m6["action"] == "player_control"
    assert m6["params"]["subaction"] == "next"

    m7 = interpret_command("SKY, poné música de Queen")
    assert m7["action"] == "open_url"
    assert "queen" in m7["params"]["query"].lower()

    m8 = interpret_command("SKY, poné Bohemian Rhapsody")
    assert m8["action"] == "open_url"
    assert "bohemian rhapsody" in m8["params"]["query"].lower()

    m9 = interpret_command("SKY, buscá videos de Queen")
    assert m9["action"] == "open_url"
    assert "queen" in m9["params"]["query"].lower()


def test_close_window_command():
    from neural_core.dispositivos import interpret_command
    c1 = interpret_command("SKY, cerrá Word")
    assert c1["action"] == "window_action"
    assert c1["params"]["subaction"] == "close"
    assert "word" in c1["params"]["target"].lower()

    c2 = interpret_command("SKY, cerrá la ventana")
    assert c2["action"] == "window_action"
    assert c2["params"]["subaction"] == "close"


def test_task_action_presentation_and_append():
    from neural_core.dispositivos import interpret_command
    t1 = interpret_command("SKY, prepará una presentación sobre los volcanes de Nicaragua")
    assert t1["action"] == "task_action"
    assert t1["params"]["subaction"] == "create_presentation"
    assert "volcanes de nicaragua" in t1["params"]["topic"].lower()

    t2 = interpret_command("SKY, agregá fotografías de los volcanes")
    assert t2["action"] == "task_action"
    assert t2["params"]["subaction"] == "append"
    assert "volcanes" in t2["params"]["modification"].lower()

    t3 = interpret_command("SKY, creá un documento sobre fauna silvestre")
    assert t3["action"] == "task_action"
    assert t3["params"]["subaction"] == "create_document"
    assert "fauna silvestre" in t3["params"]["topic"].lower()

    txt = interpret_command("SKY, quiero escribir")
    assert txt["action"] == "player_control"
    assert txt["params"]["subaction"] == "text_mode"


def test_task_manager_execution():
    from neural_core.task_manager import TaskManager
    tm = TaskManager()
    t = tm.create_task('presentation', "Presentación Volcanes", "Preparando...")
    assert t.status == 'pending'
    assert tm.get_active_task().id == t.id

    tm.update_progress(t.id, 50, 'running', "Estructurando diapositivas...")
    assert tm.get_task(t.id).progress == 50
    assert tm.get_task(t.id).status == 'running'

    t_mod = tm.append_to_active_task("Agregar fotos del volcán Masaya")
    assert t_mod is not None
    assert len(t_mod.params['modifications']) == 1
    assert "Masaya" in t_mod.params['modifications'][0]['text']

    tm.complete_task(t.id, {'ok': True, 'path': 'test.pptx'})
    assert tm.get_task(t.id).status == 'completed'
    assert tm.get_task(t.id).progress == 100



