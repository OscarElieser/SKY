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
