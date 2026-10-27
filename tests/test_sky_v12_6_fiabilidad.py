"""SKY v12.6 — fiabilidad verificable: sesión con PIN hablado, supervisor de una sola instancia, recuperación con
límites, registro de módulos bajo demanda, persistencia atómica y resultados honestos.

Lo que estas pruebas NO validan: hardware real (micrófono, altavoces), Windows (CTRL+BREAK, pythonw, inicio con la
sesión), Ollama, faster-whisper ni Vosk reales. Para eso está la lista de pruebas pendientes en docs/AUDITORIA_V12_6.md.
"""
import inspect
import json
import os
import socket
import subprocess
import sys
import textwrap
import threading
import time
import types
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import agente_dispositivo as agent
import iniciar_sky_autonomo as launcher
from neural_core import sentinel_identidad as ident, sky_capacidades as caps, sky_asistente_personal as asis
from neural_core import sky_modulos, sky_rutinas as rut, storage, voz_inbox
from neural_core.sky_archivo_seguro import actualizar_json, escribir_json, leer_json
from neural_core.sky_voz_sesion import PuertaVoz, es_orden_bloqueo

RAIZ = Path(__file__).resolve().parents[1]
KEY = 'llave-del-dueno-de-sky-' + 'y' * 20
PIN = '583920'


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'neuralt.sqlite3')
    monkeypatch.setattr(voz_inbox, 'INBOX', tmp_path / 'inbox.json')
    monkeypatch.setattr(rut, 'AGENDA_PATH', tmp_path / 'agenda.json')
    monkeypatch.setattr(rut, 'AVISOS_PATH', tmp_path / 'avisos.json')
    monkeypatch.setenv('SKY_SUPERVISOR_DIR', str(tmp_path / 'sup'))
    monkeypatch.setenv('SKY_LOG_DIR', str(tmp_path / 'logs'))
    monkeypatch.delenv('SKY_SESION_MAX_HORAS', raising=False)
    caps.POLICY_PATH.write_text(json.dumps({'perfil': 'test', 'enabled': ['status', 'notify', 'volume', 'lock'],
                                            'auto_confirm': ['notify', 'volume'], 'allowed_folders': [],
                                            'custom_apps': {}}), encoding='utf-8')
    from metaverse import sentinel
    sentinel._FALLOS.clear()


class _Reloj:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def _con_pin(bloqueada=True):
    ident.establecer_pin(PIN)
    if bloqueada:
        ident.bloquear_sesion('prueba', 'test')


def _cliente(monkeypatch):
    pytest.importorskip('fastapi')
    from fastapi.testclient import TestClient
    from metaverse import api as api_mod
    monkeypatch.setattr(api_mod, 'api_token', lambda: KEY)
    return TestClient(api_mod.app), {'X-SKY-KEY': KEY}


# ================================================================== PIN y sesión del dueño

def test_pin_hablado_digito_por_digito_y_escrito():
    assert ident.pin_desde_voz('cinco ocho tres nueve dos cero') == '583920'
    assert ident.pin_desde_voz('SKY, mi PIN es cinco, ocho, tres, nueve, dos, cero') == '583920'
    assert ident.pin_desde_voz('5 8 3 9 2 0') == '583920'
    assert ident.pin_desde_voz('Cínco ócho tres nueve dós céro') == '583920'      # tildes de la transcripción
    assert ident.pin_desde_voz('cincuenta y ocho treinta y nueve veinte') is None  # sólo dígitos de a uno
    assert ident.pin_desde_voz('uno dos tres') is None                             # muy corto
    assert ident.pin_desde_voz('abrí word') is None


def test_rechaza_pin_incorrecto_y_desbloquea_con_el_correcto(monkeypatch):
    _con_pin()
    assert ident.sesion_bloqueada()
    r = ident.desbloquear_sesion('111222', 'test')
    assert r['ok'] is False and r['restantes'] == 4 and ident.sesion_bloqueada()
    r = ident.desbloquear_sesion(PIN, 'test')
    assert r['ok'] is True and not ident.sesion_bloqueada()
    datos = json.loads(ident.ruta().read_text())
    assert PIN not in json.dumps(datos) and PIN not in ident.ruta_sesion().read_text()   # sólo verificador scrypt


def test_espera_progresiva_y_bloqueo_tras_cinco_fallos(monkeypatch):
    _con_pin()
    reloj = _Reloj()
    monkeypatch.setattr(ident.time, 'time', reloj)
    assert ident.desbloquear_sesion('000111', 't')['ok'] is False
    reloj.t += 1
    assert ident.desbloquear_sesion('000112', 't')['ok'] is False
    reloj.t += 1
    r = ident.desbloquear_sesion(PIN, 't')                     # ni el correcto pasa durante la espera
    assert r['ok'] is False and 0 < r['espera_s'] <= 4
    for i in range(3):
        reloj.t += 40
        ident.desbloquear_sesion(f'00011{3 + i}', 't')
    r = ident.desbloquear_sesion(PIN, 't')
    assert r['ok'] is False and r['espera_s'] > 600              # 15 minutos de bloqueo
    reloj.t += 16 * 60
    assert ident.desbloquear_sesion(PIN, 't')['ok'] is True


def test_sesion_falla_cerrado_y_caduca(monkeypatch):
    _con_pin(bloqueada=False)
    assert not ident.sesion_bloqueada()
    ident.ruta_sesion().write_text('{roto', encoding='utf-8')
    assert ident.sesion_bloqueada()                              # archivo ilegible → bloqueada
    ident.ruta_sesion().unlink()
    assert ident.sesion_bloqueada()                              # sin archivo (arranque) → bloqueada
    ident.desbloquear_sesion(PIN, 't')
    monkeypatch.setenv('SKY_SESION_MAX_HORAS', '1')
    datos = json.loads(ident.ruta_sesion().read_text())
    datos['desde'] -= 2 * 3600
    ident.ruta_sesion().write_text(json.dumps(datos))
    assert ident.estado_sesion()['bloqueada'] and 'caducó' in ident.estado_sesion()['motivo']


def test_sin_pin_no_hay_bloqueo_pero_se_informa():
    assert ident.sesion_bloqueada() is False
    assert ident.bloquear_sesion('x') is False
    assert ident.estado_sesion()['motivo'] == 'sin PIN configurado'


def test_recuperacion_local_conserva_memoria_y_permisos():
    _con_pin()
    politica = caps.POLICY_PATH.read_text()
    ident.restablecer_local()
    assert not ident.pin_configurado() and not ident.sesion_bloqueada()
    assert caps.POLICY_PATH.read_text() == politica


def test_desbloquear_conserva_permisos_por_dispositivo_y_herramienta():
    _con_pin()
    antes = caps.POLICY_PATH.read_text()
    ident.desbloquear_sesion(PIN, 't')
    ident.bloquear_sesion('x', 't')
    ident.desbloquear_sesion(PIN, 't')
    assert caps.POLICY_PATH.read_text() == antes


# ================================================================== no se puede eludir el bloqueo

def test_api_bloqueada_responde_423_salvo_desbloqueo_y_emergencia(monkeypatch):
    c, h = _cliente(monkeypatch)
    _con_pin()
    assert c.get('/api/hud/estado', headers=h).status_code == 423
    assert c.post('/api/asistente/mensaje', headers=h, json={'texto': 'abre Word'}).status_code == 423
    assert c.get('/api/hud/modulos', headers=h).status_code == 423
    assert c.get('/api/sentinel/sesion').json()['bloqueada'] is True            # pública: sólo el booleano
    assert c.get('/api/client/bootstrap').json()['sesion_bloqueada'] is True
    assert c.get('/api/asistente/emergencia', headers=h).status_code == 200      # la parada siempre funciona
    assert c.post('/api/sentinel/desbloquear', json={'pin': '999888'}).status_code == 401
    assert c.get('/api/hud/estado', headers=h).status_code == 423
    r = c.post('/api/sentinel/desbloquear', json={'pin': PIN})
    assert r.status_code == 200 and r.json()['key'] == KEY
    assert c.get('/api/hud/estado', headers=h).status_code == 200
    assert c.post('/api/sentinel/bloquear', headers=h).json() == {'bloqueada': True}
    assert c.get('/api/hud/estado', headers=h).status_code == 423


def test_agente_rechaza_acciones_con_la_sesion_bloqueada(monkeypatch):
    _con_pin()
    hechas = []
    monkeypatch.setattr(agent, 'execute_action', lambda a, p, politica=None: hechas.append(a) or {'ok': True, 'status': 'VERIFIED'})
    srv = ThreadingHTTPServer(('127.0.0.1', 0), agent.Handler)
    srv.secret = 's' * 48
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    base = f'http://127.0.0.1:{srv.server_address[1]}'

    def pedir(ruta, cuerpo=None, origen=''):
        import urllib.request
        h = {'Authorization': 'Bearer ' + 's' * 48, 'Content-Type': 'application/json'}
        if origen:
            h['X-SKY-ORIGEN'] = origen
        req = urllib.request.Request(base + ruta, data=json.dumps(cuerpo).encode() if cuerpo else None, headers=h,
                                     method='POST' if cuerpo else 'GET')
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
    try:
        assert pedir('/action', {'action': 'volume', 'params': {'command': 'up'}}) == 423       # voz/HUD/WhatsApp
        assert pedir('/action', {'action': 'lock_screen', 'params': {}}, 'programada') == 423    # requiere confirmar
        assert pedir('/action', {'action': 'volume', 'params': {'command': 'up'}}, 'falso') == 423
        assert pedir('/actions_history') == 423
        assert pedir('/status') == 200                                                         # salud del supervisor
        assert pedir('/action', {'action': 'notify', 'params': {'message': 'hola'}}, 'programada') == 200
        assert hechas == ['notify']
        ident.desbloquear_sesion(PIN, 't')
        assert pedir('/action', {'action': 'volume', 'params': {'command': 'up'}}) == 200
    finally:
        srv.shutdown(); srv.server_close(); hilo.join(2)


def test_voz_local_no_llama_al_agente_con_la_sesion_bloqueada(monkeypatch):
    from neural_core import dispositivos
    _con_pin()
    monkeypatch.setenv('SKY_DEVICE_TOKEN', 't' * 40)
    llamadas = []
    monkeypatch.setattr(dispositivos, 'call_device', lambda *a, **k: llamadas.append(a) or {'ok': True})
    r = asis.ejecutar_local_si_autorizado({'action': 'volume', 'params': {'command': 'up'}})
    assert r['status'] == 'LOCKED' and llamadas == []
    r = asis.ejecutar_local_si_autorizado({'action': 'notify', 'params': {'message': 'x'}}, origen='programada')
    assert llamadas and r == {'ok': True}                       # aviso programado de nivel 1 ya autorizado


def test_whatsapp_no_ejecuta_con_la_sesion_bloqueada(monkeypatch):
    from neural_core import sky_whatsapp
    _con_pin()
    monkeypatch.setattr(asis, 'atender', lambda *a, **k: pytest.fail('no debe procesar la orden'))
    r = sky_whatsapp.atender_texto('abrí word')
    assert 'bloqueada' in r and 'PIN' in r
    r = sky_whatsapp.atender_texto('para todo')                  # la parada de emergencia sí funciona
    assert caps.parada_activa() and 'detuve' in r.lower()


def test_puerta_de_voz_pregunta_el_pin_y_no_registra_nada(monkeypatch, capsys):
    reloj = _Reloj(0.0)
    puerta = PuertaVoz(reloj=reloj)
    assert puerta.evaluar('abrí word', None) is None             # sin PIN: camino normal
    _con_pin()
    assert puerta.saludo_inicial() == '¿Cuál es tu PIN?'
    r = puerta.evaluar('hablaban de la tele', None)              # charla ambiente: silencio
    assert r['decir'] is None and r['bloqueada']
    r = puerta.evaluar('sky abrí word', 'abrí word')             # te dirigís a SKY: recuerda el PIN
    assert '¿Cuál es tu PIN?' in r['decir']
    assert puerta.evaluar('sky abrí word', 'abrí word')['decir'] is None   # sin insistir cada frase
    r = puerta.evaluar('sky uno uno uno dos dos dos', 'uno uno uno dos dos dos')
    assert r['decir'].startswith('PIN incorrecto') and not r['desbloqueada']
    r = puerta.evaluar('cinco ocho tres nueve dos cero', None)
    assert r['desbloqueada'] and r['decir'] == 'PIN correcto. SKY desbloqueada.'
    assert puerta.evaluar('abrí word', None) is None
    assert puerta.bloquear_por_voz('bloquéate')['decir'].startswith('SKY bloqueada')
    assert ident.sesion_bloqueada()
    salida = capsys.readouterr()
    assert PIN not in salida.out + salida.err and 'cinco ocho' not in salida.out + salida.err
    assert es_orden_bloqueo('SKY, bloquéate') and not es_orden_bloqueo('bloquea la pantalla')


def test_orden_bloqueate_por_texto_bloquea_todo_el_servidor(monkeypatch):
    _con_pin(bloqueada=False)
    r = asis.reglas('SKY, bloquéate')
    assert r['bloquear_hud'] is True and ident.sesion_bloqueada()


def test_streamlit_y_manos_libres_usan_la_misma_puerta():
    app = (RAIZ / 'app.py').read_text(encoding='utf-8')
    assert '_puerta_sesion_sky()' in app and 'desbloquear_sesion(pin, "streamlit")' in app
    ml = (RAIZ / 'sky_manos_libres.py').read_text(encoding='utf-8')
    assert 'puerta.evaluar(result, text_after_wake(result))' in ml
    # La puerta va antes de imprimir o guardar la frase reconocida.
    assert ml.index('puerta.evaluar(') < ml.index("print('Escuchado:'")
    assert "'last_command': command" not in ml


# ================================================================== resultados honestos

def test_distingue_verificada_enviada_pendiente_y_bloqueada():
    d = asis.describir_resultado
    assert d({'ok': True, 'status': 'VERIFIED', 'message': 'Abrí Word.'}) == ('verificada', 'Abrí Word.')
    estado, frase = d({'ok': True, 'status': 'SENT', 'message': 'Envié la orden'})
    assert estado == 'enviada' and 'No pude comprobar' in frase
    assert d({'ok': True})[0] == 'enviada'                         # antes se decía «Listo» sin evidencia
    assert d(None)[0] == 'pendiente'
    assert d({'ok': False, 'status': 'LOCKED', 'message': 'x'})[0] == 'bloqueada'
    assert d({'ok': False, 'message': 'falló'}) == ('fallida', 'falló')


# ================================================================== arranque: nada externo por arrancar

def test_recordatorios_vencidos_con_sky_apagada_no_salen_por_whatsapp(monkeypatch):
    pytest.importorskip('fastapi')
    from datetime import datetime, timedelta
    from metaverse import api as api_mod
    externos = []
    monkeypatch.setattr(api_mod, '_avisar_fuera', lambda t: externos.append(t))
    monkeypatch.setattr(api_mod, '_vigilancia', lambda: None)
    ahora = datetime.now()
    rut.AGENDA_PATH.write_text(json.dumps({'recordatorios': [
        {'id': 'a', 'texto': 'de ayer', 'cuando': (ahora - timedelta(days=1)).isoformat(timespec='seconds'), 'hecho': False},
        {'id': 'b', 'texto': 'de recién', 'cuando': (ahora - timedelta(minutes=1)).isoformat(timespec='seconds'), 'hecho': False},
    ], 'rutinas': []}), encoding='utf-8')
    api_mod._ciclo_agenda()
    assert externos == ['de recién']
    avisos = [a['texto'] for a in json.loads(rut.AVISOS_PATH.read_text())]
    assert any('Perdido mientras SKY estaba apagada' in a and 'de ayer' in a for a in avisos)


def test_la_api_no_carga_motores_pesados_al_importarse():
    env = {**os.environ, 'HOME': str(Path(os.environ.get('HOME', '/tmp'))), 'SKY_AGENDA_ENABLED': '0'}
    codigo = ('import sys, metaverse.api; pesados=[m for m in ("trimesh","torch","faster_whisper","diffusers","vosk",'
              '"transformers") if m in sys.modules]; print(",".join(pesados))')
    r = subprocess.run([sys.executable, '-c', codigo], cwd=RAIZ, env=env, capture_output=True, text=True, timeout=120)
    if r.returncode != 0 and 'No module named' in r.stderr:
        pytest.skip('dependencias de la API no instaladas en este entorno')
    assert r.returncode == 0, r.stderr[-500:]
    assert r.stdout.strip() == ''


def test_salud_asincrona_y_preparacion(monkeypatch):
    c, _ = _cliente(monkeypatch)
    from metaverse import api as api_mod
    assert inspect.iscoroutinefunction(api_mod.health)            # responde aunque el modelo ocupe los hilos
    assert c.get('/api/health').status_code == 200
    r = c.get('/api/health/listo')
    assert r.status_code == 200 and r.json()['listo'] is True
    assert set(r.json()['componentes']) == {'memoria', 'seguridad', 'metricas'}


def test_cerrar_el_hud_no_detiene_el_nucleo():
    hud = (RAIZ / 'metaverse' / 'static' / 'hud.js').read_text(encoding='utf-8')
    assert 'beforeunload' not in hud and 'pagehide' not in hud and 'sendBeacon' not in hud
    from metaverse import api as api_mod
    rutas = ' '.join(getattr(r, 'path', '') for r in api_mod.app.routes).lower()
    assert '/api/shutdown' not in rutas and '/api/apagar' not in rutas


# ================================================================== registro de módulos bajo demanda

def _modulos_falsos(monkeypatch, cargados, falla=False):
    def cargar_a():
        time.sleep(0.05)
        cargados.append('a')
        if falla:
            raise RuntimeError('sin GPU')
        return 'A en memoria'
    falsos = [
        sky_modulos._m('motor_a', 'Motor A', 'motor', ('motor a',), lambda: [], cargar_a, None,
                       lambda: 'a' in cargados and not falla, ram_mb=600),
        sky_modulos._m('motor_b', 'Motor B', 'motor', ('motor b',), lambda: [], lambda: cargados.append('b') or 'B',
                       None, lambda: 'b' in cargados, ram_mb=600),
        sky_modulos._m('cred', 'Con credencial', 'integracion', ('cred',), lambda: ['MI_CLAVE en .env']),
    ]
    monkeypatch.setattr(sky_modulos, 'catalogo', lambda: falsos)
    monkeypatch.setattr(sky_modulos, '_ram_libre_mb', lambda: 16000)
    sky_modulos._VIVO.clear()


def test_activar_un_modulo_no_carga_los_demas(monkeypatch):
    cargados = []
    _modulos_falsos(monkeypatch, cargados)
    assert sky_modulos.estado('motor_a')['estado'] == 'disponible'
    r = sky_modulos.activar('motor_a', esperar=True)
    assert r['estado'] == 'activo' and cargados == ['a']
    assert sky_modulos.estado('motor_b')['estado'] == 'disponible'
    resumen = sky_modulos.listar()['resumen']
    assert set(resumen) == set(sky_modulos.ESTADOS) and resumen['activo'] == 1 and resumen['no_configurado'] == 1


def test_modulo_que_falla_no_detiene_a_los_demas(monkeypatch):
    cargados = []
    _modulos_falsos(monkeypatch, cargados, falla=True)
    r = sky_modulos.activar('motor_a', esperar=True)
    assert r['estado'] == 'error' and 'sin GPU' in r['detalle']
    assert sky_modulos.activar('motor_b', esperar=True)['estado'] == 'activo'
    assert {m['id']: m['estado'] for m in sky_modulos.listar()['modulos']}['motor_a'] == 'error'


def test_limites_de_memoria_y_concurrencia(monkeypatch):
    cargados = []
    _modulos_falsos(monkeypatch, cargados)
    monkeypatch.setattr(sky_modulos, '_ram_libre_mb', lambda: 900)
    r = sky_modulos.activar('motor_a')
    assert r['estado'] == 'degradado' and 'MB libres' in r['mensaje'] and cargados == []
    monkeypatch.setattr(sky_modulos, '_ram_libre_mb', lambda: 16000)
    sem = sky_modulos._semaforo()
    assert sem.acquire(blocking=False)
    try:
        r = sky_modulos.activar('motor_b')
        assert 'Ya estoy cargando' in r['mensaje'] and cargados == []
    finally:
        sem.release()


def test_informa_exactamente_que_falta(monkeypatch):
    cargados = []
    original = sky_modulos.catalogo
    _modulos_falsos(monkeypatch, cargados)
    e = sky_modulos.estado('cred')
    assert e['estado'] == 'no_configurado' and e['falta'] == ['MI_CLAVE en .env']
    monkeypatch.setattr(sky_modulos, 'catalogo', original)
    for v in ('SKY_WA_TOKEN', 'SKY_WA_PHONE_ID', 'SKY_WA_APP_SECRET', 'SKY_WA_VERIFY_TOKEN', 'SKY_WA_OWNER'):
        monkeypatch.delenv(v, raising=False)
    wa = sky_modulos.estado('whatsapp')
    assert wa['estado'] == 'no_configurado' and 'SKY_WA_TOKEN' in ' '.join(wa['falta'])
    falta_voz = launcher.requisitos_voz(Path('/no/existe/vosk'))
    assert any('modelo Vosk' in f for f in falta_voz)


def test_ordenes_de_modulos_por_voz_o_texto(monkeypatch):
    cargados = []
    _modulos_falsos(monkeypatch, cargados)
    assert 'Módulos:' in sky_modulos.interpretar('SKY, mostrame el estado de los módulos')['mensaje']
    r = sky_modulos.interpretar('activá el motor a')
    assert 'cargando' in r['mensaje'].lower() or 'activo' in r['mensaje'].lower()
    assert sky_modulos.interpretar('activa la escucha continua') is None    # no captura órdenes ajenas
    assert sky_modulos.interpretar('activa la alarma') is None
    assert 'Falta: MI_CLAVE' in sky_modulos.interpretar('qué le falta a cred')['mensaje']


# ================================================================== persistencia atómica

def test_actualizacion_json_entre_procesos_sin_perder_cambios(tmp_path):
    ruta = tmp_path / 'estado.json'
    script = textwrap.dedent(f'''
        import sys; sys.path.insert(0, {str(RAIZ)!r})
        from neural_core.sky_archivo_seguro import actualizar_json
        def sumar(d):
            d = d or {{}}
            d['n'] = d.get('n', 0) + 1
            return d
        for _ in range(150):
            actualizar_json({str(ruta)!r}, sumar, {{}})
    ''')
    procs = [subprocess.Popen([sys.executable, '-c', script]) for _ in range(3)]
    invalidos = 0
    while any(p.poll() is None for p in procs):
        try:
            json.loads(ruta.read_text())
        except FileNotFoundError:
            pass
        except ValueError:
            invalidos += 1
    assert all(p.wait(60) == 0 for p in procs)
    assert leer_json(ruta)['n'] == 450 and invalidos == 0


def test_coordinador_de_voz_no_pisa_el_estado_ni_guarda_frases(tmp_path, monkeypatch):
    from neural_core import voice_coordinator as vc
    destino = tmp_path / 'vc.json'
    c = vc.VoiceCoordinator.__new__(vc.VoiceCoordinator)
    c._lock = threading.Lock()
    c._context = vc.ConversationalContext()
    c._state_file = destino
    assert not destino.exists()
    c.record_turn('mi clave del banco es tal', 'anotado')
    c.set_state(vc.VoiceState.PROCESANDO)
    datos = json.loads(destino.read_text())
    assert 'last_user_utterance' not in datos and 'banco' not in destino.read_text()
    assert datos['current_state'] == vc.VoiceState.PROCESANDO.value
    fuente = (RAIZ / 'neural_core' / 'voice_coordinator.py').read_text(encoding='utf-8')
    assert 'self._persist_state()\n\n    def set_mode' not in fuente      # ya no escribe al importarse


def test_cola_de_voz_no_duplica_ordenes():
    from neural_core.sky_voice_queue import VoiceWorkQueue
    q = VoiceWorkQueue(lambda c: None, capacity=2)
    assert q.submit('abrí Word') and q.submit('Abrí word') and q.duplicates == 1
    assert q._queue.qsize() == 1
    q._last_command = (q._last_command[0], time.monotonic() - 10)
    assert q.submit('abrí Word') and q._queue.qsize() == 2
    assert q.submit('otra cosa') is False                         # cola acotada: no crece sin límite


# ================================================================== supervisor: una instancia, recuperación, cierre

_SERVICIO = textwrap.dedent('''
    import http.server, json, sys, time
    puerto, modo = int(sys.argv[1]), sys.argv[2]
    if modo == 'salir1': sys.exit(1)
    if modo == 'salir2': sys.exit(2)
    if modo == 'dormir':
        time.sleep(120); sys.exit(0)
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if modo == 'mal':
                self.send_response(500); self.end_headers(); return
            cuerpo = json.dumps({'service': 'SKY Engine API', 'status': 'ok', 'listo': True}).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(cuerpo)
        def log_message(self, *a): pass
    http.server.ThreadingHTTPServer(('127.0.0.1', puerto), H).serve_forever()
''')


def _puerto_libre():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture
def servicio_falso(tmp_path, monkeypatch):
    script = tmp_path / 'servicio_falso_sky.py'
    script.write_text(_SERVICIO, encoding='utf-8')
    puerto = _puerto_libre()
    monkeypatch.setitem(launcher.PORTS, 'api', puerto)

    def definir(modo='ok'):
        return [launcher.Servicio('api', [sys.executable, str(script), str(puerto), modo], None, puerto,
                                  sonda=lambda: launcher.sonda_api(puerto), preparado=lambda: launcher.preparacion_api(puerto),
                                  espera_preparacion=20, requerido=True, firma=script.name)]
    return types.SimpleNamespace(script=script, puerto=puerto, definir=definir)


def _supervisor(monkeypatch, definir):
    s = launcher.SkySupervisor(with_voice=False, open_browser=False)
    monkeypatch.setattr(s, '_definir_servicios', definir)
    return s


def test_arrancar_dos_veces_no_duplica_ni_interrumpe(monkeypatch, servicio_falso):
    _con_pin(bloqueada=False)
    a = _supervisor(monkeypatch, servicio_falso.definir)
    assert a.start_all() is True
    try:
        assert ident.sesion_bloqueada()                           # al iniciar SKY pregunta el PIN
        proc = a.servicios['api'].proc
        assert a.servicios['api'].estado == 'activo' and proc.poll() is None
        b = _supervisor(monkeypatch, lambda: pytest.fail('la segunda instancia no debe definir servicios'))
        assert b.start_all() is False
        assert proc.poll() is None and launcher.sonda_api(servicio_falso.puerto)[0]
        assert launcher.check_system_status()['supervisor']['en_marcha'] is True
    finally:
        a.stop_all()
    assert proc.poll() is not None                                # cierre limpio de lo propio


def test_adopta_un_sky_sano_sin_reiniciarlo(monkeypatch, servicio_falso):
    a = _supervisor(monkeypatch, servicio_falso.definir)
    assert a.start_all() is True
    proc = a.servicios['api'].proc
    a._candado.liberar()                                          # el supervisor anterior «murió»; la API sigue
    b = _supervisor(monkeypatch, servicio_falso.definir)
    try:
        assert b.start_all() is True
        assert b.servicios['api'].externo and b.servicios['api'].proc is None and proc.poll() is None
        b.stop_all()
        assert proc.poll() is None                                # lo adoptado no se cierra
    finally:
        proc.terminate(); proc.wait(5)


def _esperar_salida(srv, limite=10):
    fin = time.time() + limite
    while srv.proc is not None and srv.proc.poll() is None and time.time() < fin:
        time.sleep(0.05)


def test_recupera_un_servicio_caido_con_espera_progresiva_y_limite(monkeypatch, servicio_falso):
    reloj = _Reloj(time.time())
    monkeypatch.setattr(launcher, 'time', types.SimpleNamespace(time=reloj, sleep=lambda s: None,
                                                                strftime=time.strftime, monotonic=time.monotonic))
    s = launcher.SkySupervisor(with_voice=False, open_browser=False)
    srv = servicio_falso.definir('salir1')[0]
    s.servicios['api'] = srv
    s._iniciar('api', srv.args)
    esperas = []
    for _ in range(MAX := launcher.MAX_REINICIOS_HORA):
        _esperar_salida(srv)
        s.revisar()
        assert srv.estado == 'error' and srv.proc is None
        esperas.append(round(srv.proximo_intento - reloj.t))
        reloj.t += esperas[-1] + 1
        s.revisar()                                               # reinicia cuando vence la espera
        assert srv.proc is not None
    assert esperas == [2, 4, 8, 16, 32]
    _esperar_salida(srv)
    s.revisar()
    assert 'límite' in srv.causa and round(srv.proximo_intento - reloj.t) == launcher.ESPERA_TRAS_LIMITE
    reloj.t += 600
    s.revisar()
    assert srv.proc is None                                       # respeta el límite
    reloj.t += launcher.ESPERA_TRAS_LIMITE
    s.revisar()
    assert srv.proc is not None                                   # y vuelve a intentar más tarde
    _esperar_salida(srv)
    s.stop_all()
    assert len([l for l in (Path(os.environ['SKY_LOG_DIR']) / 'api.log').read_text().splitlines() if 'inicio de api' in l]) == MAX + 2


def test_falla_permanente_no_se_reintenta_en_bucle(monkeypatch, servicio_falso):
    s = launcher.SkySupervisor(with_voice=False, open_browser=False)
    srv = servicio_falso.definir('salir2')[0]
    s.servicios['api'] = srv
    s._iniciar('api', srv.args)
    _esperar_salida(srv)
    s.revisar()
    assert srv.estado == 'no_configurado' and srv.proximo_intento == 0
    s.revisar(time.time() + 10_000)
    assert srv.proc is None
    s.stop_all()


def test_colgado_se_distingue_de_lento(monkeypatch, servicio_falso):
    s = launcher.SkySupervisor(with_voice=False, open_browser=False)
    s.intervalo_sonda = 0
    srv = servicio_falso.definir('dormir')[0]
    srv.sonda = lambda: (False, 'no responde')
    srv.colgado_tras = 90
    s.servicios['api'] = srv
    s._iniciar('api', srv.args)
    srv.estado = 'activo'
    t0 = time.time()
    s.revisar(t0)
    s.revisar(t0 + 60)                                            # lento: todavía no se reinicia
    assert srv.estado == 'degradado' and srv.proc.poll() is None
    s.revisar(t0 + 95)                                            # 95 s sin responder con el proceso vivo: colgado
    assert srv.estado == 'error' and 'colgado' in srv.causa and srv.proc is None
    assert srv.proximo_intento > 0
    s.stop_all()


def test_estado_no_presenta_la_api_online_si_la_salud_falla(monkeypatch, servicio_falso):
    proc = subprocess.Popen([sys.executable, str(servicio_falso.script), str(servicio_falso.puerto), 'mal'])
    try:
        fin = time.time() + 10
        while not launcher.is_port_in_use(servicio_falso.puerto) and time.time() < fin:
            time.sleep(0.05)
        st = launcher.check_system_status()
        assert st['api']['listening'] is True
        assert not st['api']['status'].startswith('online')        # antes: «online (sin endpoint /sky)»
        assert st['chat_texto']['disponible'] is False
        assert any(p['servicio'] == 'api' for p in st['problemas'])
    finally:
        proc.terminate(); proc.wait(5)


def test_no_cierra_otra_instancia_de_sky_que_no_inicio(monkeypatch, servicio_falso):
    proc = subprocess.Popen([sys.executable, str(servicio_falso.script), str(servicio_falso.puerto), 'ok'])
    matados = []
    monkeypatch.setattr(launcher, 'kill_process_by_pid', lambda pid: matados.append(pid) or True)
    monkeypatch.setattr(launcher, 'get_pid_using_port', lambda p: proc.pid)
    try:
        fin = time.time() + 10
        while not launcher.is_port_in_use(servicio_falso.puerto) and time.time() < fin:
            time.sleep(0.05)
        assert launcher.clean_port_conflicts([servicio_falso.puerto]) == {servicio_falso.puerto: False}
        assert matados == [] and proc.poll() is None
    finally:
        proc.terminate(); proc.wait(5)


def test_detener_sin_instancia_y_registros_sin_tokens(monkeypatch, tmp_path):
    assert launcher.detener_instancia(espera=1) is True
    logs = Path(os.environ['SKY_LOG_DIR'])
    logs.mkdir(parents=True, exist_ok=True)
    (logs / 'agent.log').write_text('Token para emparejar: ' + 'Ab9_' * 12 + '\nerror final\n')
    assert 'Ab9_Ab9_' not in launcher._ultimas_lineas('agent')
    fuente = (RAIZ / 'agente_dispositivo.py').read_text(encoding='utf-8')
    assert "args.mostrar_token or (sys.stdout is not None and sys.stdout.isatty())" in fuente


def test_inicio_con_windows_sin_consola(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, 'os', types.SimpleNamespace(name='nt', environ={'APPDATA': str(tmp_path)}))
    pythonw = tmp_path / 'pythonw.exe'
    pythonw.write_text('')
    monkeypatch.setattr(launcher, 'VENV_PYTHONW', pythonw)
    assert launcher.manage_windows_startup(True) is True
    bat = next(tmp_path.rglob('SKY_IA_Autonomo.bat')).read_text()
    assert 'pythonw.exe' in bat and '--minimized' in bat


def test_artefactos_de_flutter_en_la_plantilla_no_rompen_los_disenos(tmp_path, monkeypatch):
    """Regresión: `flutter test` dentro de la plantilla dejó build/ y .dart_tool/ (45 MB) y todo diseño Flutter fallaba."""
    import shutil
    from neural_core import sky_design_studio as studio
    destino = tmp_path / studio._ALLOWED['flutter']
    shutil.copytree(studio._ROOT / studio._ALLOWED['flutter'], destino)
    (destino / 'build' / 'test_cache').mkdir(parents=True)
    (destino / 'build' / 'test_cache' / 'cache.dill').write_bytes(b'0' * 200_000)
    (destino / '.dart_tool').mkdir()
    (destino / '.dart_tool' / 'package_config.json').write_text('{}')
    monkeypatch.setattr(studio, '_ROOT', tmp_path)
    archivos = studio._file_set('flutter')
    assert 'lib/main.dart' in archivos and not any(f.startswith(('build/', '.dart_tool/')) for f in archivos)
