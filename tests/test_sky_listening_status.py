"""Verificación de estados del micrófono sin abrir dispositivos."""
from neural_core.sky_listening_status import resumen_escucha


def test_mic_activo():
    estado = dict(hands_free_listening=True, status="ready", last_seen=995,
                  last_audio=998, wordless_active=True)
    res = resumen_escucha(estado, ahora=1000)
    assert res["escucha_continua"]
    assert res["consumiendo_audio"]
    assert res["escucha_natural_sin_sky"]


def test_archivo_viejo_no_equivale_a_servicio_vivo():
    estado = dict(hands_free_listening=True, status="ready", last_seen=900,
                  last_audio=901, wordless_active=True)
    res = resumen_escucha(estado, ahora=1000)
    assert not res["escucha_continua"]
    assert not res["consumiendo_audio"]


def test_late_audio_blocks_false_ready_state():
    estado = dict(hands_free_listening=True, status="ready", last_seen=999,
                  last_audio=900, wordless_active=True)
    res = resumen_escucha(estado, ahora=1000)
    assert res["consumiendo_audio"]
    assert not res["microfono_recibiendo_audio"]


def test_modo_sin_palabra_es_opcional():
    estado = dict(hands_free_listening=True, status="ready", last_seen=999,
                  last_audio=999, wordless_active=False)
    res = resumen_escucha(estado, ahora=1000)
    assert res["escucha_continua"]
    assert not res["escucha_natural_sin_sky"]


def test_senal_de_parada_y_archivo_invalido():
    res = resumen_escucha(dict(hands_free_listening=False, status="stopped",
                               last_seen=999, last_audio=999), ahora=1000)
    assert not res["escucha_continua"]
    assert not resumen_escucha({}, ahora=1000)["escucha_continua"]
    assert not resumen_escucha({"last_seen": "no", "last_audio": None}, ahora=1000)["escucha_continua"]
