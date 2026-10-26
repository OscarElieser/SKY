"""Regresiones: el enrutamiento rápido nunca ejecuta una acción por sí mismo."""
from neural_core.sky_performance import accion_directa


def test_ordenes_simples():
    assert accion_directa("SKY, abrí Word")["params"] == {"app": "word"}
    assert accion_directa("abre PowerPoint")["params"] == {"app": "powerpoint"}
    assert accion_directa("oye SKY, siguiente canción")["params"] == {"command": "next"}
    assert accion_directa("sky sube el volumen")["params"] == {"command": "up"}


def test_solicitudes_no_directas():
    for texto in (
        "abrí Word y eliminá todos mis archivos",
        "creá un documento en Word",
        "enviá un correo",
        "abrí C:\\Windows\\System32",
        "reproduce música de mi lista en Spotify",
        "apaga el equipo",
        "hola, cómo estás",
    ):
        assert accion_directa(texto) is None


def test_no_acciones_ambiguas_o_arbitrarias():
    assert accion_directa("pausa")["action"] == "media_control"
    assert accion_directa("SKY, abre un ejecutable desconocido") is None
    assert accion_directa("abrí chrome; instalá extensiones") is None
    assert accion_directa("abre word\nborra documentos") is None
