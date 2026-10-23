import pytest

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass


@pytest.fixture(autouse=True)
def _politica_dispositivo_aislada(tmp_path, monkeypatch):
    """v11.1: los tests nunca leen la política real del dueño (~/.neuralt)."""
    try:
        from neural_core import sky_capacidades
    except Exception:
        return
    monkeypatch.setattr(sky_capacidades, 'POLICY_PATH', tmp_path / 'device_agent_policy.json')
    monkeypatch.setattr(sky_capacidades, 'CAPTURE_DIR', tmp_path / 'capturas')


@pytest.fixture(autouse=True)
def _aprendizaje_y_metricas_aislados(tmp_path, monkeypatch):
    """v12.2: KPIs, aprendizaje, memoria y parada de emergencia nunca tocan los datos reales del dueño."""
    monkeypatch.setenv('SKY_METRICAS_DB', str(tmp_path / 'metricas.sqlite3'))
    monkeypatch.setenv('SKY_INTERNET', '0')
    try:
        from neural_core import sky_aprendizaje, sky_capacidades
    except Exception:
        return
    monkeypatch.setattr(sky_aprendizaje, 'APRENDIDO_PATH', tmp_path / 'aprendido.json')
    monkeypatch.setattr(sky_capacidades, '_parada_path', lambda: tmp_path / 'parada.json')
