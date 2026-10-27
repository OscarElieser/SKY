"""SKY v12.4 — catálogo de habilidades, SKY Skill Builder (revisión estática + proceso aislado + aprobación),
centro de integraciones y creación multimedia. Todas las APIs externas están simuladas."""
import base64
import io
import json
import os
import urllib.error
from datetime import date

import pytest

from neural_core import sky_skill_builder as sb, sky_habilidades as hab, sky_integraciones as integ, sky_creativo as cre
from neural_core import hab_proyectos as proy, hab_viajes as viajes, sky_asistente_personal as asis, sky_cerebro as cerebro
from neural_core import sky_capacidades as caps, sky_metricas as kpi, storage, voz_inbox, sky_rutinas as rut

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64


@pytest.fixture(autouse=True)
def _base(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'neuralt.sqlite3')
    monkeypatch.setattr(voz_inbox, 'INBOX', tmp_path / 'inbox.json')
    monkeypatch.setattr(rut, 'AGENDA_PATH', tmp_path / 'agenda.json')
    monkeypatch.setattr(rut, 'AVISOS_PATH', tmp_path / 'avisos.json')
    monkeypatch.setattr(sb, 'base', lambda: tmp_path / 'builder')
    monkeypatch.setattr(hab, '_ruta', lambda: tmp_path / 'habilidades.json')
    monkeypatch.setattr(proy, 'ruta', lambda: tmp_path / 'proyectos.json')
    monkeypatch.setattr(cre, 'carpeta', lambda tipo: (tmp_path / 'creaciones' / tipo).mkdir(parents=True, exist_ok=True) or tmp_path / 'creaciones' / tipo
                        if tipo in ('imagenes', 'musica', 'presentaciones') else (_ for _ in ()).throw(ValueError('Tipo de creación inválido.')))
    monkeypatch.setattr(cerebro, '_ollama_ok', lambda: False)
    monkeypatch.setattr(asis, 'ejecutar_local_si_autorizado', lambda p, **k: None)
    for v in ('OPENAI_API_KEY', 'FIREFLY_CLIENT_ID', 'FIREFLY_CLIENT_SECRET', 'GAMMA_API_KEY', 'SKY_LOCAL_ONLY', 'SKY_CEREBRO',
              'ANTHROPIC_API_KEY', 'GEMINI_API_KEY', 'SKY_HA_URL', 'SKY_HA_TOKEN'):
        monkeypatch.delenv(v, raising=False)


def _r(texto):
    return asis.reglas(asis.preparar(texto))


# ------------------------------------------------------------------ integraciones

def test_integraciones_honestas(monkeypatch):
    por_id = {i['id']: i for i in integ.listar()}
    assert por_id['suno']['via'] == 'sin_api' and 'no tiene API pública' in por_id['suno']['nota']
    assert por_id['canva']['via'] == 'oauth' and por_id['canva']['estado'] == 'pendiente (OAuth)'
    assert 'no incluye la API' in por_id['openai']['nota'] and not por_id['openai']['lista']
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-x')
    assert integ.lista('openai') and integ.lista('openai_imagenes')
    r = _r('qué integraciones tengo')
    assert r['modulo'] == 'habilidades' and 'OpenAI (GPT)' in r['mensaje'] and 'Suno' in r['mensaje']


# ------------------------------------------------------------------ creación multimedia

def test_imagen_con_openai(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-x')
    capt = {}
    def falso(url, cuerpo=None, cabeceras=None, datos=None, timeout=120):
        capt.update(url=url, cuerpo=cuerpo, cab=cabeceras)
        return {'data': [{'b64_json': base64.b64encode(PNG).decode()}]}
    monkeypatch.setattr(cre, '_json', falso)
    r = _r('genera una imagen de un colibrí futurista sobre Managua')
    assert r['imagen'].endswith('.png') and 'OpenAI' in r['mensaje']
    assert capt['url'] == 'https://api.openai.com/v1/images/generations' and capt['cuerpo']['prompt'].startswith('un colibrí')
    assert cre.ruta_creacion('imagenes', r['imagen']).read_bytes() == PNG
    assert kpi.resumen()['acciones']['por_accion'][0]['accion'] == 'generar_imagen'


def test_imagen_con_firefly(monkeypatch):
    monkeypatch.setenv('FIREFLY_CLIENT_ID', 'cid')
    monkeypatch.setenv('FIREFLY_CLIENT_SECRET', 'sec')
    llamadas = []
    def falso(url, cuerpo=None, cabeceras=None, datos=None, timeout=120):
        llamadas.append((url, cabeceras))
        if 'ims' in url:
            assert b'grant_type=client_credentials' in datos
            return {'access_token': 'tok'}
        return {'outputs': [{'image': {'url': 'https://pre-signed.firefly/x.jpg'}}]}
    monkeypatch.setattr(cre, '_json', falso)
    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(cre.urllib.request, 'urlopen', lambda url, timeout=60: R(b'\xff\xd8\xff' + b'\x00' * 40))
    r = cre.generar_imagen('un volcán al amanecer', 'firefly')
    assert r['proveedor'] == 'firefly' and r['archivo'].endswith('.jpg')
    assert llamadas[1][0] == 'https://firefly-api.adobe.io/v3/images/generate' and llamadas[1][1]['X-Api-Key'] == 'cid'


def test_imagen_errores(monkeypatch):
    with pytest.raises(RuntimeError, match='OPENAI_API_KEY'):
        cre.generar_imagen('un gato')
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-x')
    monkeypatch.setenv('SKY_LOCAL_ONLY', '1')
    with pytest.raises(RuntimeError, match='100 % local'):
        cre.generar_imagen('un gato')
    monkeypatch.delenv('SKY_LOCAL_ONLY')
    monkeypatch.setattr(cre, '_json', lambda *a, **k: {'data': [{'b64_json': base64.b64encode(b'<html>no').decode()}]})
    with pytest.raises(RuntimeError, match='no es una imagen'):
        cre.generar_imagen('un gato')
    def http(*a, **k):
        raise urllib.error.HTTPError('u', 402, 'pago', {}, None)
    monkeypatch.setattr(cre, '_json', http)
    with pytest.raises(RuntimeError, match='HTTP 402'):
        cre.generar_imagen('un gato')
    caps.activar_parada('x')
    with pytest.raises(RuntimeError, match='parada'):
        cre.generar_imagen('un gato')
    caps.levantar_parada()
    for malo in ('../x.png', 'a/b.png', '.env', 'x.exe'):
        with pytest.raises(ValueError):
            cre.ruta_creacion('imagenes', malo)


def test_presentacion_gamma(monkeypatch):
    monkeypatch.setenv('GAMMA_API_KEY', 'sk-gamma')
    estados = iter([{'status': 'pending'}, {'status': 'completed', 'gammaUrl': 'https://gamma.app/docs/abc', 'exportUrl': 'https://x/abc.pptx'}])
    def falso(url, cuerpo=None, cabeceras=None, datos=None, timeout=120):
        assert cabeceras['X-API-KEY'] == 'sk-gamma'
        if cuerpo is not None:
            assert url.endswith('/v1.0/generations') and cuerpo['inputText'] == 'energía solar'
            return {'generationId': 'gen123'}
        return next(estados)
    monkeypatch.setattr(cre, '_json', falso)
    monkeypatch.setattr(cre.time, 'sleep', lambda s: None)
    r = cre.crear_presentacion_gamma('energía solar', esperar=True)
    assert r == {'generationId': 'gen123', 'estado': 'lista', 'url': 'https://gamma.app/docs/abc', 'exportar': 'https://x/abc.pptx'}
    assert cre.listar('presentaciones')


def test_cancion(monkeypatch):
    from neural_core import providers
    respuesta = json.dumps({'titulo': 'Managua de noche', 'estilo': 'bachata, 128 BPM, guitarra requinto, voz masculina',
                            'estructura': ['Verso 1', 'Coro'], 'letra': '[Verso 1]\nLas luces del malecón...\n[Coro]\nManagua...',
                            'acordes': {'Verso': 'Am - G - F - E'}})
    monkeypatch.setattr(providers, 'reply', lambda m, p, max_output_tokens=1500: 'Aquí va:\n' + respuesta)
    r = _r('escribe una canción sobre Managua de noche estilo bachata')
    assert r['cancion']['titulo'] == 'Managua de noche' and 'Suno no tiene API pública' in r['mensaje']
    md = cre.ruta_creacion('musica', r['cancion']['archivo']).read_text(encoding='utf-8')
    assert '## Letra' in md and 'Am - G - F - E' in md


# ------------------------------------------------------------------ sky-business-manager

def test_proyectos(monkeypatch):
    hoy = date(2026, 10, 23)                                                  # viernes
    assert 'Creé el proyecto «Tienda online»' in proy.interpretar('crea el proyecto Tienda online', hoy)['mensaje']
    assert 'Ya existe' in proy.interpretar('crea el proyecto tienda online', hoy)['mensaje']
    r = proy.interpretar('agrega la tarea diseñar el logo al proyecto tienda online para el viernes a cargo de Ana', hoy)
    assert '«diseñar el logo»' in r['mensaje'] and '2026-10-30' in r['mensaje']
    proy.interpretar('agrega la tarea abrir la cuenta al proyecto tienda online para el 1/10', hoy)
    assert 'No tengo un proyecto' in proy.interpretar('agrega la tarea revisar al proyecto inventado', hoy)['mensaje']
    estado = proy.interpretar('cómo va el proyecto tienda online', hoy)['mensaje']
    assert '0 %' in estado and 'Atrasadas: abrir la cuenta' in estado
    assert 'Hecho' in proy.interpretar('marca hecha la tarea diseñar el logo', hoy)['mensaje']
    assert '50 %' in proy.interpretar('qué proyectos tengo', hoy)['mensaje']
    assert 'abrir la cuenta' in proy.interpretar('qué tareas están atrasadas', hoy)['mensaje']
    assert 'Archivé' in proy.interpretar('archiva el proyecto tienda online', hoy)['mensaje']
    assert 'No tenés proyectos' in proy.interpretar('qué proyectos tengo', hoy)['mensaje']
    assert proy.interpretar('abre el proyecto de la escuela', hoy) is None    # abrir carpetas sigue siendo del agente


# ------------------------------------------------------------------ sky-travel

def test_viaje(monkeypatch):
    monkeypatch.setenv('SKY_INTERNET', '1')
    def get(url, timeout=10):
        if 'geocoding' in url:
            return {'results': [{'name': 'Granada', 'country': 'Nicaragua', 'latitude': 11.93, 'longitude': -85.95}]}
        if 'forecast' in url:
            return {'daily': {'time': ['2026-10-24'], 'weather_code': [61], 'temperature_2m_max': [31.2],
                              'temperature_2m_min': [23.0], 'precipitation_probability_max': [70]}}
        return {'result': 'success', 'rates': {'NIO': 36.6}}
    monkeypatch.setattr(viajes, '_get', get)
    from neural_core import providers
    monkeypatch.setattr(providers, 'reply', lambda *a, **k: 'Día 1: Catedral y Calzada.')
    r = _r('planifica un viaje a Granada de 3 días con 200 dólares')
    p = r['viaje']
    assert [x['total'] for x in p['presupuesto']] == [80, 50, 40, 20, 10] and p['presupuesto'][0]['por_dia'] == 26.67
    assert p['clima']['dias'][0]['cielo'] == 'lluvia ligera' and p['equivalente']['total'] == 7320
    assert 'Catedral' in r['mensaje'] and 'Open-Meteo' in r['mensaje']
    assert storage.buscar_documentos('viaje Granada')
    assert '¿Con qué presupuesto' in _r('planifica un viaje a León')['mensaje']
    monkeypatch.setenv('SKY_INTERNET', '0')
    assert viajes.planificar('León', 2, 100)['clima'] is None


# ------------------------------------------------------------------ catálogo, seguridad y automonitoreo

def test_catalogo_activar_desactivar():
    assert 'Viajes' in _r('qué habilidades tienes')['mensaje']
    assert 'Desactivé' in _r('desactiva la habilidad viajes')['mensaje']
    assert _r('planifica un viaje a León de 2 días con 100 dólares') is None
    assert 'Activé' in _r('activa la habilidad viajes')['mensaje']
    assert 'no se puede desactivar' in _r('desactiva la habilidad seguridad')['mensaje']
    c = hab.catalogo()
    assert {h['id'] for h in c['nativas']} >= {'sky-travel', 'sky-business-manager', 'sky-smart-home', 'sky-self-monitor',
                                               'sky-security', 'sky-music', 'sky-creative'}


def test_auditoria_de_seguridad(monkeypatch):
    pol = caps.aplicar_perfil('completo', [])
    pol['auto_confirm'] = sorted(set(pol['auto_confirm']) | {'clipboard'})
    caps.guardar_politica(pol)
    kpi.registrar('api', 'GET /api/hud/estado', True, 5, codigo=401)
    r = _r('haz una auditoría de seguridad')
    niveles = [x['nivel'] for x in r['auditoria']['hallazgos']]
    assert niveles[0] == 'alta' and 'clipboard' in r['mensaje'] and 'intentos de acceso sin llave' in r['mensaje']


def test_recomendaciones_usan_evidencia():
    sb.registrar_necesidad('convierte 20 dólares a córdobas')
    sb.registrar_necesidad('convierte 20 dólares a córdobas')
    sb.registrar_necesidad('hola qué tal')                                     # no es un pedido: no cuenta
    assert [n['frase'] for n in sb.necesidades()] == ['convierte 20 dolares a cordobas']
    r = _r('recomiéndame mejoras')
    assert 'convierte 20 dolares a cordobas' in r['mensaje'] and 'diseña una habilidad' in r['mensaje']
    assert 'convierte 20 dolares' in _r('qué habilidades me faltan')['mensaje']


def test_necesidad_se_registra_cuando_no_hay_herramienta(monkeypatch):
    from neural_core import providers
    monkeypatch.setattr(providers, 'reply', lambda *a, **k: 'No sé hacer eso todavía.')
    asis.atender('calcula mi índice de masa corporal con 70 kilos', [], 'auto', 'voz')
    assert sb.necesidades()[0]['frase'].startswith('calcula mi indice')


# ------------------------------------------------------------------ SKY Skill Builder

CODIGO = '''
import re
def ejecutar(entrada, contexto):
    m = re.search(r"([0-9.]+)", entrada)
    if not m:
        return {"decir": "Decime cuántos dólares."}
    tasa = ((contexto.get("fuentes") or {}).get("tasas") or {}).get("rates", {}).get("NIO", 36.6)
    return {"decir": "%s dólares son %.2f córdobas." % (m.group(1), float(m.group(1)) * tasa),
            "acciones": [{"orden": "abre la calculadora"}]}
'''
MANIFIESTO = {'nombre': 'Dólares a córdobas', 'descripcion': 'Convierte USD a NIO', 'disparadores': ['cuantos cordobas son'],
              'permisos': ['internet:open.er-api.com', 'acciones'],
              'fuentes': [{'nombre': 'tasas', 'url': 'https://open.er-api.com/v6/latest/USD'}],
              'pruebas': [{'entrada': '10 dolares', 'contexto': {'fuentes': {'tasas': {'rates': {'NIO': 36.5}}}}, 'espera': ['365.00 córdobas']}]}


@pytest.mark.parametrize('codigo,problema', [
    ('import os\ndef ejecutar(e, c): return {"decir": os.getcwd()}', 'os'),
    ('import socket\ndef ejecutar(e, c): return {}', 'socket'),
    ('from subprocess import run\ndef ejecutar(e, c): return {}', 'subprocess'),
    ('def ejecutar(e, c): return {"decir": open("x").read()}', 'open'),
    ('def ejecutar(e, c): return {"decir": str(().__class__.__bases__)}', '__class__'),
    ('def ejecutar(e, c): return {"decir": "{0.__class__}".format(1)}', 'atributos internos'),
    ('def ejecutar(e, c): return {"decir": eval("1+1")}', 'eval'),
    ('def ejecutar(e, c): return {"decir": getattr(e, "upper")()}', 'getattr'),
    ('def otra(e, c): return {}', 'ejecutar'),
    ('def ejecutar(e, c) return', 'sintaxis'),
])
def test_revision_estatica_rechaza(codigo, problema):
    assert any(problema in p for p in sb.validar_codigo(codigo))


def test_proceso_aislado_contiene_abusos():
    assert 'tiempo máximo' in sb.ejecutar_aislado('def ejecutar(e, c):\n    while True: pass', [{'entrada': ''}], timeout=3)['error']
    r = sb.ejecutar_aislado('import os\ndef ejecutar(e, c): return {"decir": "x"}', [{'entrada': ''}])
    assert not r['ok'] and 'no permitido' in r['error']                       # aunque se saltara la revisión estática
    r = sb.ejecutar_aislado('def ejecutar(e, c): return {"decir": 5}', [{'entrada': ''}])
    assert r['resultados'][0]['ok'] is False
    r = sb.ejecutar_aislado('def ejecutar(e, c): return {"decir": "x", "acciones": [{"orden": "a"}] * 6}', [{'entrada': ''}])
    assert 'hasta 5' in r['resultados'][0]['error']


def test_manifiesto_validado():
    m, problemas = sb.validar_manifiesto({**MANIFIESTO, 'permisos': ['acciones']})
    assert any('internet:open.er-api.com' in p for p in problemas)
    m, problemas = sb.validar_manifiesto({**MANIFIESTO, 'disparadores': ['para todo']})
    assert any('reservada' in p for p in problemas)
    m, problemas = sb.validar_manifiesto({**MANIFIESTO, 'fuentes': [{'nombre': 'x', 'url': 'http://inseguro.com'}]})
    assert any('sólo https' in p for p in problemas)
    m, problemas = sb.validar_manifiesto({**MANIFIESTO, 'permisos': ['root', 'acciones', 'internet:open.er-api.com']})
    assert any('no válidos' in p for p in problemas) and 'root' not in m['permisos']


def test_ciclo_completo_proponer_aprobar_usar(monkeypatch):
    p = sb.guardar_propuesta(MANIFIESTO, CODIGO)
    assert p['reporte']['aprobada'] and p['id'] == 'dolares-a-cordobas'
    assert _r('cuántos córdobas son 20 dólares') is None                     # propuesta: todavía no instalada
    with pytest.raises(ValueError, match='declaró'):
        sb.aprobar(p['id'], 1, ['internet:evil.com'])
    sb.aprobar(p['id'], 1, ['internet:open.er-api.com'])                      # sin «acciones»
    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    pedidas = []
    monkeypatch.setenv('SKY_INTERNET', '1')
    monkeypatch.setattr(sb.urllib.request, 'urlopen', lambda req, timeout=10: pedidas.append(req.full_url) or R(b'{"rates": {"NIO": 36.0}}'))
    r = _r('SKY, cuántos córdobas son 20 dólares')
    assert r['mensaje'] == '20 dólares son 720.00 córdobas.' and r['acciones'] == []   # sin permiso, no hay órdenes
    assert pedidas == ['https://open.er-api.com/v6/latest/USD']
    sb.aprobar(p['id'], 1, ['internet:open.er-api.com', 'acciones'])
    r = _r('cuántos córdobas son 5')
    assert r['acciones'][0]['estado'] == 'pendiente' and voz_inbox.read_inbox()   # la orden pasa por tus permisos
    assert kpi.resumen()['acciones']['por_accion'][0]['accion'].startswith('habilidad:')
    # Alguien edita el archivo instalado: SKY se niega a ejecutarlo.
    (sb.base() / p['id'] / 'v1' / 'skill.py').write_text('import os\ndef ejecutar(e, c): return {"decir": "x"}', encoding='utf-8')
    assert 'modificada fuera de SKY' in _r('cuántos córdobas son 5')['mensaje']
    assert 'Desactivé' in _r('desactiva la habilidad dólares a córdobas')['mensaje']
    assert _r('cuántos córdobas son 5') is None
    assert sb.eliminar(p['id']) and sb.listar() == []
    auditoria = (sb.base() / 'auditoria.jsonl').read_text(encoding='utf-8')
    assert '"evento": "aprobada"' in auditoria and '"evento": "eliminada"' in auditoria


def test_no_aprueba_si_falla_y_guarda_versiones():
    malo = sb.guardar_propuesta({**MANIFIESTO, 'pruebas': [{'entrada': '10', 'espera': ['999']}]}, CODIGO)
    assert not malo['reporte']['aprobada']
    with pytest.raises(ValueError, match='no pasa sus pruebas'):
        sb.aprobar(malo['id'], 1, [])
    bueno = sb.guardar_propuesta(MANIFIESTO, CODIGO)
    assert bueno['version'] == 2 and sb.aprobar(bueno['id'], 2, [])['estado'] == 'instalada'
    assert sb.cargar(bueno['id'], 1)[2]['aprobada'] is False                 # la versión 1 queda para auditar


def test_proponer_con_ia_reintenta(monkeypatch):
    respuestas = iter([{'manifiesto': MANIFIESTO, 'codigo': 'import os\ndef ejecutar(e, c): return {}'},
                       {'manifiesto': MANIFIESTO, 'codigo': CODIGO}])
    consignas = []
    monkeypatch.setattr(sb, '_redactar', lambda pedido, proveedor='auto': consignas.append(pedido) or next(respuestas))
    sb.registrar_necesidad('convierte dólares a córdobas')
    r = _r('diseña una habilidad para convertir dólares a córdobas')
    assert 'pasó sus 1 pruebas' in r['mensaje'] and 'no está instalada' in r['mensaje']
    assert 'falló' in consignas[1] and sb.listar()[0]['estado'] == 'propuesta'
    assert 'sólo se aprueban en Módulos' in _r('aprueba la habilidad dólares a córdobas')['mensaje']


def test_plantilla_exige_reglas():
    texto = sb.PLANTILLA.format(pedido='x', modulos=', '.join(sb.MODULOS_PERMITIDOS))
    assert 'Nada de archivos, red' in texto and 'internet:<dominio>' in texto and 'acciones' in texto


# ------------------------------------------------------------------ API y HUD

def _cliente(monkeypatch):
    pytest.importorskip('fastapi')
    from fastapi.testclient import TestClient
    from metaverse import api as api_mod
    monkeypatch.setattr(api_mod, 'api_token', lambda: 'k' * 32)
    return TestClient(api_mod.app), {'X-SKY-KEY': 'k' * 32}


def test_api_habilidades_y_builder(monkeypatch):
    client, h = _cliente(monkeypatch)
    c = client.get('/api/hud/habilidades', headers=h).json()
    assert len(c['nativas']) == 7 and c['integraciones'] and c['builder'] == []
    assert client.patch('/api/hud/habilidades/sky-security', headers=h, json={'activa': False}).status_code == 400
    assert client.patch('/api/hud/habilidades/sky-music', headers=h, json={'activa': False}).json()['activa'] is False
    v = client.post('/api/hud/builder/version', headers=h, json={'manifiesto': MANIFIESTO, 'codigo': CODIGO}).json()
    assert v['reporte']['aprobada']
    assert 'def ejecutar' in client.get('/api/hud/builder/' + v['id'], headers=h).json()['codigo']
    assert client.post(f"/api/hud/builder/{v['id']}/aprobar", headers=h, json={'version': 1, 'permisos': ['root']}).status_code == 400
    assert client.post(f"/api/hud/builder/{v['id']}/aprobar", headers=h, json={'version': 1, 'permisos': []}).json()['estado'] == 'instalada'
    assert client.post(f"/api/hud/builder/{v['id']}/aprobar", json={'version': 1, 'permisos': []}).status_code == 401
    assert client.post(f"/api/hud/builder/{v['id']}/desactivar", headers=h).json() == {'ok': True}
    assert client.delete(f"/api/hud/builder/{v['id']}", headers=h).json() == {'ok': True}
    assert client.get('/api/hud/builder/nada', headers=h).status_code == 404
    malo = client.post('/api/hud/builder/version', headers=h, json={'manifiesto': MANIFIESTO, 'codigo': 'import os\ndef ejecutar(e, c): pass'}).json()
    assert not malo['reporte']['aprobada'] and malo['reporte']['estatica']


def test_api_creaciones(monkeypatch):
    client, h = _cliente(monkeypatch)
    (cre.carpeta('imagenes') / '20261023-gato.png').write_bytes(PNG)
    assert client.get('/api/hud/creaciones/imagenes', headers=h).json()['archivos'][0]['nombre'] == '20261023-gato.png'
    r = client.get('/api/hud/creaciones/imagenes/20261023-gato.png', headers=h)
    assert r.status_code == 200 and r.headers['content-type'] == 'image/png' and r.content == PNG
    assert client.get('/api/hud/creaciones/imagenes/..%2F..%2F.env', headers=h).status_code in (400, 404)
    assert client.get('/api/hud/creaciones/sistema/x.png', headers=h).status_code == 400
    assert client.get('/api/hud/creaciones/imagenes/20261023-gato.png').status_code == 401


def test_hud_modulo_habilidades():
    from pathlib import Path
    js = (Path(__file__).resolve().parent.parent / 'metaverse' / 'static' / 'hud.js').read_text(encoding='utf-8')
    assert "id: 'habilidades'" in js and 'function abrirHabilidades' in js and '/aprobar' in js and 'function mostrarImagen' in js
