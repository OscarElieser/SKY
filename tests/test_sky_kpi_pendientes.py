"""Regresión: SKY no debe etiquetar como error una orden pendiente ni alertar con datos obsoletos."""
from datetime import datetime, timedelta

from neural_core import dispositivos, sky_metricas as kpi


def test_open_url_enviado_no_es_fallo(tmp_path, monkeypatch):
    monkeypatch.setenv('SKY_METRICAS_DB', str(tmp_path / 'metricas.sqlite3'))
    monkeypatch.setattr(dispositivos, '_call_device',
                        lambda *args, **kwargs: {'ok': True, 'status': 'SENT'})
    for _ in range(4):
        dispositivos.call_device('http://127.0.0.1:8766', 't' * 40,
                                 'open_url', {'url': 'https://ejemplo.org'})
    r = kpi.resumen('hoy')
    assert r['acciones']['pendientes'] == 4
    assert r['acciones']['fallidas'] == 0
    assert 'repite:open_url' not in {p['id'] for p in r['problemas']}
    assert 'acciones_fallidas' not in {p['id'] for p in r['problemas']}


def test_error_real_sigue_alertando(tmp_path, monkeypatch):
    monkeypatch.setenv('SKY_METRICAS_DB', str(tmp_path / 'metricas.sqlite3'))
    monkeypatch.setattr(dispositivos, '_call_device',
                        lambda *args, **kwargs: {'ok': False, 'status': 'FAILED', 'error': 'rechazado'})
    for _ in range(4):
        dispositivos.call_device('http://127.0.0.1:8766', 't' * 40,
                                 'open_url', {'url': 'https://ejemplo.org'})
    ids = {p['id'] for p in kpi.detectar()}
    assert 'repite:open_url' in ids and 'acciones_fallidas' in ids


def test_eventos_antiguos_no_disparan_alerta_actual(tmp_path, monkeypatch):
    monkeypatch.setenv('SKY_METRICAS_DB', str(tmp_path / 'metricas.sqlite3'))
    ahora = datetime(2026, 10, 26, 16, 0)
    hace_dos_horas = (ahora - timedelta(hours=2)).timestamp()
    for _ in range(4):
        kpi.registrar('accion', 'open_url', False, ts=hace_dos_horas,
                      detalle='fallo comprobado', origen='FAILED')
    for _ in range(3):
        kpi.registrar('servicio', 'reinicio', False, ts=hace_dos_horas,
                      detalle='agent se detuvo')
    assert not kpi.detectar(ahora)
    r = kpi.resumen('hoy', ahora)
    assert r['acciones']['fallidas'] == 4 and r['servicio']['reinicios'] == 3
    assert r['problemas'] == []


def test_metrica_historica_de_enviado_es_pendiente(tmp_path, monkeypatch):
    monkeypatch.setenv('SKY_METRICAS_DB', str(tmp_path / 'metricas.sqlite3'))
    for _ in range(4):
        kpi.registrar('accion', 'open_url', False,
                      detalle='Acción enviada o iniciada, aún no verificada.', origen='SENT')
    r = kpi.resumen('hoy')
    assert r['acciones']['pendientes'] == 4
    assert r['acciones']['fallidas'] == 0
    assert not r['problemas']
