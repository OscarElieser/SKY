"""SKY v12.1 — cerebro con herramientas, voz por frases, agenda, correo, WhatsApp, Piper,
diagnóstico e instalador."""
import io
import json
import os
import stat
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from neural_core import sky_rutinas as rut, sky_correo as correo, sky_contactos as contactos
from neural_core import sky_cerebro as cerebro, sky_tts, sky_diagnostico, sky_home_assistant as casa
from neural_core import sky_asistente_personal as asis

AHORA = datetime(2026, 10, 23, 10, 0)
_DISPONIBLE_REAL = cerebro.disponible


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    monkeypatch.setattr(rut, 'AGENDA_PATH', tmp_path / 'agenda.json')
    monkeypatch.setattr(rut, 'AVISOS_PATH', tmp_path / 'avisos.json')
    monkeypatch.setattr(contactos, 'CONTACTOS_PATH', tmp_path / 'contactos.json')
    monkeypatch.setattr(sky_tts, 'BASE', tmp_path / 'piper')
    for v in ('SKY_MAIL_USER', 'SKY_MAIL_APP_PASSWORD', 'SKY_MAIL_APP_PASSWORD_FILE', 'SKY_HA_URL', 'SKY_HA_TOKEN',
              'SKY_HA_NOTIFY', 'SKY_PIPER_BIN', 'SKY_PIPER_VOICE', 'SKY_CEREBRO', 'SKY_LOCAL_ONLY'):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(cerebro, 'disponible', lambda: False)
    correo._ULTIMOS.clear()


# ------------------------------------------------------------------ agenda

@pytest.mark.parametrize('frase,cuando,texto', [
    ('recuérdame en 10 minutos sacar la ropa', '2026-10-23T10:10:00', 'sacar la ropa'),
    ('recordame a las 5 llamar a mamá', '2026-10-23T17:00', 'llamar a mamá'),
    ('recuérdame mañana a las 8 la reunión con Pedro', '2026-10-24T08:00', 'la reunión con Pedro'),
    ('recuérdame en una hora que tomo la pastilla', '2026-10-23T11:00:00', 'tomo la pastilla'),
    ('recuérdame en media hora apagar el horno', '2026-10-23T10:30:00', 'apagar el horno'),
    ('recuérdame a las 3 pm ir al banco', '2026-10-23T15:00', 'ir al banco'),
    ('pon una alarma a las 6:30', '2026-10-24T06:30', 'Alarma'),
    ('despiértame a las 7', '2026-10-24T07:00', 'Alarma'),
    ('pon una alarma a las 6 pm', '2026-10-23T18:00', 'Alarma'),
])
def test_interpreta_recordatorios(frase, cuando, texto):
    r = rut.interpretar(frase, AHORA)
    assert r['tipo'] == 'recordatorio' and r['cuando'] == cuando and r['texto'] == texto


@pytest.mark.parametrize('frase', ['recuérdame algo raro', 'qué hora es', 'avísame que tengo reunión', ''])
def test_no_inventa_recordatorios(frase):
    assert rut.interpretar(frase, AHORA) is None


def test_ciclo_de_recordatorios_y_avisos():
    a = rut.crear('sacar la ropa', (AHORA + timedelta(minutes=10)).isoformat())
    b = rut.crear('reunión', (AHORA + timedelta(days=1)).isoformat(), 'alarma')
    assert [x['id'] for x in rut.pendientes()] == [a['id'], b['id']]
    assert rut.vencidos(AHORA) == []
    vencidos = rut.vencidos(AHORA + timedelta(minutes=11))
    assert [v['id'] for v in vencidos] == [a['id']] and rut.vencidos(AHORA + timedelta(minutes=12)) == []
    assert rut.borrar(b['id']) and rut.pendientes() == []
    rut.avisar('🔔 sacar la ropa')
    assert rut.avisos_nuevos()[0]['texto'] == '🔔 sacar la ropa' and rut.avisos_nuevos() == []
    with pytest.raises(ValueError):
        rut.crear('x', AHORA.isoformat(), 'bomba')


def test_rutina_buenos_dias_y_programadas(monkeypatch):
    rut.crear('dentista', (AHORA + timedelta(hours=2)).isoformat())
    r = rut.rutina_por_frase('Buenos días, SKY')
    res = rut.ejecutar_rutina(r, AHORA)
    assert 'Buenos días, Oscar' in res['mensaje'] and 'dentista' in res['mensaje']
    item = rut.guardar_rutina({'nombre': 'Trabajo', 'frases': ['modo trabajo'], 'hora': '10:00',
                               'pasos': [{'tipo': 'decir', 'texto': 'A trabajar'},
                                         {'tipo': 'accion', 'action': 'launch_app', 'params': {'app': 'vscode'}},
                                         {'tipo': 'accion', 'action': 'rm_rf', 'params': {}}]})
    assert [p['tipo'] for p in item['pasos']] == ['decir', 'accion']
    assert [x['nombre'] for x in rut.rutinas_programadas(AHORA + timedelta(minutes=5))] == ['Trabajo']
    assert rut.rutinas_programadas(AHORA + timedelta(minutes=6)) == []          # una vez por día
    pendientes = []
    monkeypatch.setattr(asis, 'ejecutar_local_si_autorizado', lambda a: None)
    from neural_core import voz_inbox
    monkeypatch.setattr(voz_inbox, 'add_inbox', lambda t, a: pendientes.append(a['action']))
    res = rut.ejecutar_rutina(rut.rutina_por_frase('modo trabajo'))
    assert pendientes == ['launch_app'] and 'confirmación' in res['mensaje']
    with pytest.raises(ValueError):
        rut.guardar_rutina({'nombre': 'x', 'pasos': [{'tipo': 'accion', 'action': 'run_shell'}]})


def test_asistente_crea_recordatorio_y_lo_lista():
    r = asis.atender('recuérdame en 10 minutos llamar a Pedro')
    assert r['tipo'] == 'respuesta' and r['recordatorio']['texto'] == 'llamar a Pedro'
    assert 'llamar a Pedro' in asis.atender('qué recordatorios tengo')['mensaje']


# ------------------------------------------------------------------ correo

def test_correo_no_configurado_y_borrador_valido(monkeypatch):
    assert not correo.configurado()
    with pytest.raises(RuntimeError):
        correo.no_leidos()
    with pytest.raises(ValueError):
        correo.borrador('no-es-correo', 'a', 'b')
    with pytest.raises(ValueError):
        correo.borrador('ana@gmail.com', 'a', '')
    monkeypatch.setenv('SKY_MAIL_USER', 'oscar@gmail.com')
    monkeypatch.setenv('SKY_MAIL_APP_PASSWORD', 'abcd efgh ijkl mnop')
    assert correo.configurado() and correo.servidores() == ('imap.gmail.com', 'smtp.gmail.com')


def test_correo_lee_sin_marcar_y_responde(monkeypatch):
    monkeypatch.setenv('SKY_MAIL_USER', 'oscar@gmail.com')
    monkeypatch.setenv('SKY_MAIL_APP_PASSWORD', 'abcd efgh ijkl mnop')
    vistos = {}

    class FakeIMAP:
        def __init__(self, host, port, ssl_context=None, timeout=None): vistos['host'] = host
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, u, p): vistos['login'] = u
        def select(self, box, readonly=False): vistos['readonly'] = readonly; return ('OK', [b'1'])
        def uid(self, cmd, *args):
            if cmd == 'search':
                return 'OK', [b'7']
            vistos['fetch'] = args[-1]
            cab = (b'From: =?utf-8?q?Ana_P=C3=A9rez?= <ana@empresa.com>\r\nSubject: Propuesta\r\n'
                   b'Message-ID: <abc@empresa.com>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n')
            return 'OK', [(b'7 (BODY[HEADER]', cab), (b' BODY[TEXT]<0>', 'Hola Oscar, ¿revisás la propuesta?'.encode())]
    monkeypatch.setattr(correo.imaplib, 'IMAP4_SSL', FakeIMAP)
    lista = correo.no_leidos()
    assert vistos['readonly'] is True and 'PEEK' in vistos['fetch']
    assert lista[0]['de'] == 'Ana Pérez' and lista[0]['asunto'] == 'Propuesta' and 'propuesta' in lista[0]['resumen']
    r = correo.interpretar('responde al último correo diciendo Gracias, la reviso hoy')
    assert r['tipo'] == 'correo_enviar' and r['borrador']['para'] == 'ana@empresa.com'
    assert r['borrador']['asunto'] == 'Re: Propuesta' and r['borrador']['cuerpo'] == 'Gracias, la reviso hoy'
    enviados = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None): enviados.append(host)
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, context=None): enviados.append('tls')
        def login(self, u, p): enviados.append(u)
        def send_message(self, msg): enviados.append(msg['To'] + '|' + msg['In-Reply-To'])
    monkeypatch.setattr(correo.smtplib, 'SMTP', FakeSMTP)
    assert correo.enviar(**r['borrador'])['ok']
    assert enviados == ['smtp.gmail.com', 'tls', 'oscar@gmail.com', 'ana@empresa.com|<abc@empresa.com>']


def test_asistente_correo_pide_confirmacion(monkeypatch):
    monkeypatch.setenv('SKY_MAIL_USER', 'oscar@gmail.com')
    monkeypatch.setenv('SKY_MAIL_APP_PASSWORD', 'abcd efgh ijkl mnop')
    contactos.CONTACTOS_PATH.write_text(json.dumps({'Ana': {'email': 'ana@empresa.com'}}), encoding='utf-8')
    r = asis.atender('mándale un correo a Ana diciendo nos vemos mañana')
    assert r['tipo'] == 'correo' and r['requiere_confirmacion'] and r['borrador']['para'] == 'ana@empresa.com'
    assert 'No tengo el correo' in asis.atender('mándale un correo a Zoe diciendo hola')['mensaje']


# ------------------------------------------------------------------ WhatsApp y contactos

def test_whatsapp_abre_con_mensaje_y_no_envia_solo():
    contactos.CONTACTOS_PATH.write_text(json.dumps({'mamá': {'whatsapp': '+505 8888-7777'}}), encoding='utf-8')
    r = asis.atender('mándale un whatsapp a mamá que llego tarde')
    assert r['tipo'] == 'accion' and r['propuesta']['action'] == 'open_url'
    assert r['propuesta']['params']['url'] == 'https://wa.me/50588887777?text=llego%20tarde'
    assert 'Enviar' in r['propuesta']['description']
    assert 'No tengo el WhatsApp' in asis.atender('mándale un whatsapp a Pedro que hola')['mensaje']
    with pytest.raises(ValueError):
        contactos.enlace_whatsapp('123', 'x')


# ------------------------------------------------------------------ cerebro con herramientas

@pytest.mark.parametrize('nombre,args,accion,params', [
    ('abrir_app', {'app': 'spotify'}, 'launch_app', {'app': 'spotify'}),
    ('reproducir', {'consulta': 'música tranquila para trabajar'}, 'play_media', {'query': 'música tranquila para trabajar', 'service': 'youtube'}),
    ('volumen', {'comando': 'set', 'nivel': 140}, 'volume', {'command': 'set', 'level': 100}),
    ('volumen', {'comando': 'up'}, 'volume', {'command': 'up'}),
    ('multimedia', {'comando': 'next'}, 'media_control', {'command': 'next'}),
    ('reproductor_sky', {'accion': 'mode_mini'}, 'player_control', {'subaction': 'mode_mini'}),
    ('ventanas', {'accion': 'close', 'objetivo': 'Excel'}, 'window_action', {'subaction': 'close', 'target': 'Excel'}),
    ('nota', {'operacion': 'crear', 'nombre': 'compras lista', 'contenido': 'pan'}, 'note_create', {'name': 'compraslista', 'content': 'pan'}),
    ('tarea', {'tipo': 'presentacion', 'tema': 'café'}, 'task_action', {'subaction': 'create_presentation', 'topic': 'café'}),
    ('abrir_carpeta_o_documento', {'objetivo': 'descargas'}, 'open_file', {'target': 'descargas'}),
    ('estado_equipo', {}, 'status', {}),
])
def test_cerebro_convierte_herramientas(nombre, args, accion, params):
    r = cerebro.convertir(nombre, args)
    assert r['tipo'] == 'accion' and r['propuesta']['action'] == accion and r['propuesta']['params'] == params


@pytest.mark.parametrize('nombre,args', [
    ('abrir_app', {'app': 'cmd.exe'}), ('volumen', {'comando': 'formatear'}), ('volumen', {'comando': 'set'}),
    ('abrir_web', {'url': 'javascript:alert(1)'}), ('abrir_web', {'url': 'http://x.com'}), ('nota', {'operacion': 'crear', 'nombre': '../x'}),
    ('reproducir', {'consulta': 'x', 'servicio': 'napster'}), ('herramienta_inventada', {}), ('ventanas', {'accion': 'destruir'}),
])
def test_cerebro_rechaza_argumentos_invalidos(nombre, args):
    assert cerebro.convertir(nombre, args) is None


def test_cerebro_recordatorio():
    r = cerebro.convertir('recordatorio', {'mensaje': 'regar las plantas', 'en_minutos': 30})
    assert r['tipo'] == 'recordatorio' and r['texto'] == 'regar las plantas'
    assert cerebro.convertir('recordatorio', {'mensaje': 'x'}) is None


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _ollama_falso(monkeypatch, lineas):
    capturado = {}
    def urlopen(req, timeout=None):
        capturado['cuerpo'] = json.loads(req.data)
        return _Resp(b'\n'.join(json.dumps(l).encode() for l in lineas))
    monkeypatch.setattr(cerebro.urllib.request, 'urlopen', urlopen)
    return capturado


def test_cerebro_elige_herramienta_con_contexto(monkeypatch):
    cap = _ollama_falso(monkeypatch, [{'message': {'role': 'assistant', 'content': '', 'tool_calls': [
        {'function': {'name': 'volumen', 'arguments': {'comando': 'up'}}}]}, 'done': True}])
    hist = [{'role': 'user', 'content': 'pon música'}, {'role': 'assistant', 'content': 'Reproducir música en YouTube'}]
    d = cerebro.decidir('más fuerte', hist, 'voz')
    assert d['tipo'] == 'herramienta' and d['resultado']['propuesta']['params'] == {'command': 'up'}
    roles = [m['role'] for m in cap['cuerpo']['messages']]
    assert roles == ['system', 'user', 'assistant', 'user'] and cap['cuerpo']['tools']
    assert any(t['function']['name'] == 'volumen' for t in cap['cuerpo']['tools'])


def test_cerebro_transmite_texto(monkeypatch):
    _ollama_falso(monkeypatch, [{'message': {'content': 'Managua '}}, {'message': {'content': 'es la capital.'}}, {'done': True}])
    eventos = list(cerebro.decidir_eventos('¿capital de Nicaragua?', [], 'voz'))
    assert eventos == [('delta', 'Managua '), ('delta', 'es la capital.'), ('fin', 'Managua es la capital.')]


def test_cerebro_sin_ollama(monkeypatch):
    def caido(*a, **k):
        raise cerebro.urllib.error.URLError('down')
    monkeypatch.setattr(cerebro.urllib.request, 'urlopen', caido)
    assert cerebro.decidir('hola')['tipo'] == 'error'


def test_reglas_primero_y_cerebro_despues(monkeypatch):
    llamado = []
    monkeypatch.setattr(asis, 'usar_cerebro', lambda p: True)
    monkeypatch.setattr(cerebro, 'decidir', lambda t, h, m: llamado.append(t) or {
        'tipo': 'herramienta', 'resultado': cerebro.convertir('reproducir', {'consulta': 'jazz suave'})})
    assert asis.atender('sube el volumen')['propuesta']['action'] == 'volume' and llamado == []
    r = asis.atender('quiero algo relajante de fondo mientras trabajo', modo='voz')
    assert llamado == ['quiero algo relajante de fondo mientras trabajo'] and r['propuesta']['params']['query'] == 'jazz suave'


def test_desactivar_cerebro(monkeypatch):
    monkeypatch.setenv('SKY_CEREBRO', 'reglas')
    assert _DISPONIBLE_REAL() is False


# ------------------------------------------------------------------ Piper, celular y diagnóstico

def test_piper_ausente_y_presente(tmp_path, monkeypatch):
    assert not sky_tts.disponible()
    with pytest.raises(RuntimeError):
        sky_tts.sintetizar('hola')
    if os.name == 'nt':
        pytest.skip('binario de prueba POSIX')
    voces = tmp_path / 'piper' / 'voces'; voces.mkdir(parents=True)
    (voces / 'es.onnx').write_bytes(b'x'); (voces / 'es.onnx.json').write_text('{}')
    binario = tmp_path / 'piper' / 'piper'
    binario.write_text('#!/bin/sh\nout=""\nwhile [ $# -gt 0 ]; do [ "$1" = "--output_file" ] && out="$2"; shift; done\n'
                       'cat > /dev/null\nprintf RIFFfake > "$out"\n')
    binario.chmod(binario.stat().st_mode | stat.S_IEXEC)
    assert sky_tts.disponible()
    assert sky_tts.sintetizar('Hola, Oscar.') == b'RIFFfake'
    with pytest.raises(ValueError):
        sky_tts.sintetizar('   ')


def test_aviso_al_celular(monkeypatch):
    assert casa.notificar_celular('hola') is False
    monkeypatch.setenv('SKY_HA_URL', 'http://192.168.1.5:8123')
    monkeypatch.setenv('SKY_HA_TOKEN', 't' * 40)
    monkeypatch.setenv('SKY_HA_NOTIFY', 'notify.mobile_app_pixel')
    enviados = []
    monkeypatch.setattr(casa, '_peticion', lambda m, r, c=None, timeout=6: enviados.append((r, c)))
    assert casa.notificar_celular('Reunión en 10 minutos')
    assert enviados == [('/api/services/notify/mobile_app_pixel', {'title': 'SKY', 'message': 'Reunión en 10 minutos'})]
    monkeypatch.setenv('SKY_HA_NOTIFY', 'light.turn_off')
    assert casa.notificar_celular('x') is False


def test_diagnostico_explica_como_arreglar():
    items = sky_diagnostico.revisar()
    ids = {i['id'] for i in items}
    assert {'python', 'agente', 'ollama', 'piper', 'stt', 'casa', 'correo'} <= ids
    for i in items:
        assert set(i) == {'id', 'nombre', 'ok', 'detalle', 'solucion', 'importante'}
        if not i['ok'] and i['importante']:
            assert i['solucion']
    assert sky_diagnostico.resumen([{'ok': True, 'importante': True, 'nombre': 'x'}]) == 'Todo listo.'


def test_instalador_usa_descargas_verificadas():
    raiz = Path(__file__).resolve().parent.parent
    ps = (raiz / 'instalar_sky.ps1').read_text(encoding='ascii')     # ASCII: compatible con PowerShell 5.1
    for url in ('https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip',
                'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claude/high/es_MX-claude-high.onnx',
                'https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip'):
        assert url in ps
    assert 'Ollama.Ollama' in ps and 'sky_diagnostico.py' in ps and 'Set-ExecutionPolicy' not in ps
    bat = (raiz / 'INSTALAR_SKY_WINDOWS.bat').read_text(encoding='utf-8')
    assert 'instalar_sky.ps1' in bat


# ------------------------------------------------------------------ API (requiere FastAPI)

def _cliente(monkeypatch):
    pytest.importorskip('fastapi')
    from fastapi.testclient import TestClient
    from metaverse import api as api_mod
    monkeypatch.setattr(api_mod, 'api_token', lambda: 'k' * 32)
    return TestClient(api_mod.app), {'X-SKY-KEY': 'k' * 32}


def test_api_stream_transmite_y_ejecuta(monkeypatch):
    client, h = _cliente(monkeypatch)
    monkeypatch.setattr(asis, 'usar_cerebro', lambda p: True)
    monkeypatch.setattr(cerebro, 'decidir_eventos', lambda t, hist, m: iter([('delta', 'Hola, '), ('delta', 'Oscar.'), ('fin', 'Hola, Oscar.')]))
    r = client.post('/api/asistente/stream', headers=h, json={'texto': 'saludame', 'modo': 'voz'})
    lineas = [json.loads(x) for x in r.text.strip().split('\n')]
    assert [l.get('delta') for l in lineas[:2]] == ['Hola, ', 'Oscar.']
    assert lineas[-1]['final']['transmitido'] and lineas[-1]['final']['mensaje'] == 'Hola, Oscar.'
    r = client.post('/api/asistente/stream', headers=h, json={'texto': 'recuérdame en 5 minutos estirar', 'modo': 'voz'})
    final = json.loads(r.text.strip().split('\n')[-1])['final']
    assert final['tipo'] == 'respuesta' and final['recordatorio']['texto'] == 'estirar'


def test_api_agenda_avisos_diagnostico_y_tts(monkeypatch):
    client, h = _cliente(monkeypatch)
    item = rut.crear('estirar', (datetime.now() + timedelta(minutes=5)).isoformat())
    assert client.get('/api/hud/agenda', headers=h).json()['recordatorios'][0]['id'] == item['id']
    assert client.delete('/api/hud/agenda/' + item['id'], headers=h).json() == {'ok': True}
    assert client.delete('/api/hud/agenda/../x', headers=h).status_code in (400, 404)
    rut.avisar('hola')
    assert client.get('/api/hud/avisos', headers=h).json()['avisos'][0]['texto'] == 'hola'
    assert 'resumen' in client.get('/api/hud/diagnostico', headers=h).json()
    assert client.post('/api/hud/tts', headers=h, json={'texto': 'hola'}).status_code == 503
    assert client.post('/api/asistente/correo', headers=h, json={'para': 'ana@x.com', 'cuerpo': 'hola'}).status_code == 403
    assert client.get('/api/hud/avisos').status_code == 401
