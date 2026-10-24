"""Pruebas de aprobaciones vinculadas a la propuesta y KPIs reales de SKY."""
import time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from metaverse import api as _sky_main_api  # cargar la app antes de sus routers (evita dependencia circular)
from metaverse import asistente_api
from neural_core import sky_approvals, sky_execution_metrics


def request(key='x' * 32, session=''):
    return SimpleNamespace(headers={'X-SKY-KEY': key, 'X-SKY-SESSION': session})


def test_approval_one_use_payload_identity_and_expiry(monkeypatch):
    vault = sky_approvals.ApprovalVault(ttl=180)
    req = request()
    original = {'action': 'note_create', 'params': {'name': 'agenda', 'content': 'texto'}, 'dispositivo': 'local'}
    token = vault.issue('accion', original, req)
    assert vault.consume(token, 'accion', {'action': 'note_trash', 'params': original['params'],
                                           'dispositivo': 'local'}, req) is False
    assert vault.consume(token, 'accion', original, request(key='y' * 32)) is False
    assert vault.consume(token, 'accion', original, req) is True
    assert vault.consume(token, 'accion', original, req) is False
    expired = sky_approvals.ApprovalVault(ttl=-1)
    short = expired.issue('accion', original, req)
    assert not expired.consume(short, 'accion', original, req)


def api_client(monkeypatch):
    app = FastAPI()
    app.include_router(asistente_api.router)
    app.dependency_overrides[asistente_api.require_key] = lambda: True
    monkeypatch.setattr(asistente_api, 'approvals', sky_approvals.ApprovalVault())
    return TestClient(app)


def test_api_confirmation_exact_parameters_no_replay(monkeypatch):
    client = api_client(monkeypatch)
    calls = []

    def fake_call(device, request, action, params):
        calls.append((action, dict(params)))
        if action == 'status':
            return {'ok': True, 'enabled': ['status', 'notes'], 'auto_confirm': []}
        return {'ok': True, 'status': 'VERIFIED'}

    monkeypatch.setattr(asistente_api, '_llamar', fake_call)
    monkeypatch.setattr(asistente_api, 'atender', lambda *args: {
        'tipo': 'accion',
        'propuesta': {'action': 'note_create', 'params': {'name': 'agenda', 'content': 'hola'},
                     'description': 'Crear nota agenda'},
        'mensaje': 'Crear nota agenda'})

    proposal = client.post('/api/asistente/mensaje', json={'texto': 'crea nota agenda'}).json()
    assert proposal['requiere_confirmacion']
    approval = proposal['approval_token']
    assert approval and 'confirmed' not in proposal['propuesta']['params']
    assert client.post('/api/asistente/ejecutar', json={
        'action': 'note_create', 'params': {'name': 'agenda', 'content': 'adulterado'},
        'approval_token': approval}).status_code == 403
    assert len(calls) == 1  # solo consulta status; no se ejecuta nada

    command = {'action': 'note_create', 'params': {'name': 'agenda', 'content': 'hola'},
               'approval_token': approval}
    assert client.post('/api/asistente/ejecutar', json=command).status_code == 200
    assert calls[-1] == ('note_create', {'name': 'agenda', 'content': 'hola', 'confirmed': True})
    assert client.post('/api/asistente/ejecutar', json=command).status_code == 403


def test_email_approval_required_and_exact(monkeypatch):
    client = api_client(monkeypatch)
    from neural_core import sky_correo
    sent = []
    monkeypatch.setattr(sky_correo, 'enviar', lambda *args: sent.append(args) or {'ok': True})
    monkeypatch.setattr(asistente_api, 'atender', lambda *args: {
        'tipo': 'correo', 'mensaje': 'Revisá borrador',
        'borrador': {'para': 'ana@example.com', 'asunto': 'Hola', 'cuerpo': 'Buen día'}})
    proposal = client.post('/api/asistente/mensaje', json={'texto': 'escribí a Ana'}).json()
    token = proposal['approval_token']
    base = {'para': 'ana@example.com', 'asunto': 'Hola', 'cuerpo': 'Buen día'}
    assert client.post('/api/asistente/correo', json=base).status_code == 403
    assert client.post('/api/asistente/correo', json={**base, 'cuerpo': 'otro',
                                                     'approval_token': token}).status_code == 403
    assert sent == []
    assert client.post('/api/asistente/correo', json={**base, 'approval_token': token}).status_code == 200
    assert len(sent) == 1
    assert client.post('/api/asistente/correo', json={**base, 'approval_token': token}).status_code == 403


def test_home_quick_requires_preparation(monkeypatch):
    client = api_client(monkeypatch)
    from neural_core import sky_home_assistant as casa
    calls = []
    monkeypatch.setattr(casa, 'ejecutar', lambda service, ids, data: calls.append((service, ids, data)) or {'ok': True})
    body = {'service': 'light.toggle', 'entity_ids': ['light.sala'], 'data': {}}
    assert client.post('/api/asistente/casa', json=body).status_code == 403
    ticket = client.post('/api/asistente/casa/preparar', json=body).json()['approval_token']
    assert client.post('/api/asistente/casa', json={**body, 'approval_token': ticket}).status_code == 200
    assert calls == [('light.toggle', ['light.sala'], {})]
    assert client.post('/api/asistente/casa/preparar', json={
        'service': 'lock.unlock', 'entity_ids': ['lock.puerta']}).status_code == 403


def test_kpis_count_last_status_only_and_not_fake_success():
    stats = sky_execution_metrics.summarize_action_receipts([
        {'command_id': 'a', 'status': 'RECEIVED'},
        {'command_id': 'a', 'status': 'SENT'},
        {'command_id': 'b', 'status': 'VERIFIED', 'execution_time_ms': 100},
        {'command_id': 'c', 'status': 'FAILED', 'execution_time_ms': 200},
        {'command_id': 'd', 'status': 'PENDING'},
        {'command_id': 'e', 'status': 'RUNNING'},
    ])
    assert stats['total_actions'] == 5
    assert stats['sent'] == 1 and stats['pending'] == 1 and stats['running'] == 1
    assert stats['verified'] == 1 and stats['failed'] == 1
    assert stats['completion_success_pct'] == 50.0
    assert stats['average_finished_ms'] == 150
    assert sky_execution_metrics.summarize_action_receipts([])['completion_success_pct'] is None
