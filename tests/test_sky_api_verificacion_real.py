"""Pruebas de regresión: una orden enviada NO significa ejecución verificada."""
import json
import threading
from http.server import ThreadingHTTPServer

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import agente_dispositivo as agent
from metaverse import asistente_api
from neural_core import dispositivos
from neural_core import action_verifier


@pytest.mark.parametrize('reported,ok,expected', [
    ('SENT', True, 'SENT'),
    ('PENDING', True, 'PENDING'),
    ('RUNNING', True, 'RUNNING'),
    ('VERIFIED', True, 'VERIFIED'),
    ('FAILED', False, 'FAILED'),
])
def test_agent_ledger_distingue_entregado_de_verificado(tmp_path, monkeypatch, reported, ok, expected):
    verifier = action_verifier.ActionVerifier(tmp_path / 'ledger.jsonl')
    monkeypatch.setattr(agent, 'verificador_acciones', verifier)
    monkeypatch.setattr(agent, '_ejecutar', lambda *a: {'ok': ok, 'status': reported, 'message': 'prueba'})
    politica = {
        'perfil': 'basico', 'enabled': ['status', 'media', 'volume'],
        'auto_confirm': [], 'allowed_folders': [], 'custom_apps': {},
    }
    res = agent.execute_action('media_key', {'key': 'play_pause'}, politica)
    assert res['status'] == reported
    assert verifier.get_action(res['command_id']).status == expected
    historial = [json.loads(line) for line in (tmp_path / 'ledger.jsonl').read_text().splitlines()]
    assert historial[-1]['status'] == expected
    if expected != 'VERIFIED':
        assert historial[-1]['status'] != 'VERIFIED'


def test_recibo_persiste_tras_reinicio(tmp_path):
    ledger = tmp_path / 'acciones.jsonl'
    primero = action_verifier.ActionVerifier(ledger)
    rec = primero.start_action('media_key', 'next_track')
    primero.mark_dispatched(rec.command_id, 'SENT', {'status': 'SENT'})
    segundo = action_verifier.ActionVerifier(ledger)
    recuperado = segundo.get_action(rec.command_id)
    assert recuperado is not None
    assert recuperado.status == 'SENT'
    assert recuperado.result['status'] == 'SENT'


def test_agent_http_verification_read_only(tmp_path, monkeypatch):
    verifier = action_verifier.ActionVerifier(tmp_path / 'ledger.jsonl')
    monkeypatch.setattr(agent, 'verificador_acciones', verifier)
    server = ThreadingHTTPServer(('127.0.0.1', 0), agent.Handler)
    server.secret = 'sky-test-' + 'x' * 40
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_address[1]}'
    try:
        rec = verifier.start_action('media_key', 'play_pause')
        verifier.mark_dispatched(rec.command_id, 'SENT', {'status': 'SENT'})
        data = dispositivos.verify_device_action(url, server.secret, rec.command_id)
        assert data['ok'] is True
        assert data['status'] == 'SENT'
        assert data['verified'] is False
        assert data['command_id'] == rec.command_id

        verifier.mark_verified(rec.command_id, {'status': 'VERIFIED'})
        done = dispositivos.verify_device_action(url, server.secret, rec.command_id)
        assert done['verified'] is True
        assert done['status'] == 'VERIFIED'
        with pytest.raises(LookupError):
            dispositivos.verify_device_action(url, server.secret, 'cmd_nonexistent')
        with pytest.raises(ValueError):
            dispositivos.verify_device_action(url, server.secret, '../status')
        with pytest.raises(ValueError):
            dispositivos.verify_device_action(url, 'short', rec.command_id)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_assistant_route_verification_requires_owner_key(monkeypatch):
    # La ruta hereda la dependencia de autenticación del router completo.
    monkeypatch.setenv('SKY_API_KEY', 'a' * 32)
    app = FastAPI()
    app.include_router(asistente_api.router)
    client = TestClient(app)
    response = client.get('/api/asistente/verificar/cmd_test')
    assert response.status_code == 401


def test_assistant_route_verification_preserves_receipt(monkeypatch):
    app = FastAPI()
    app.include_router(asistente_api.router)
    app.dependency_overrides[asistente_api.require_key] = lambda: True
    monkeypatch.setattr(asistente_api, '_destino', lambda dispositivo, request: ('http://127.0.0.1:8766', 'x' * 40))
    receipts = []
    def fake_verify(url, token, command_id, timeout=7):
        receipts.append((url, token, command_id))
        return {'ok': True, 'command_id': command_id, 'status': 'PENDING', 'verified': False, 'record': {}}
    monkeypatch.setattr(dispositivos, 'verify_device_action', fake_verify)
    client = TestClient(app)
    res = client.get('/api/asistente/verificar/cmd_123')
    assert res.status_code == 200
    assert res.json()['status'] == 'PENDING' and res.json()['verified'] is False
    assert receipts == [('http://127.0.0.1:8766', 'x' * 40, 'cmd_123')]
