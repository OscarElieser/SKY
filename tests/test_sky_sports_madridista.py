"""Tests para el motor SKY Sports Madridista y sus endpoints."""
import pytest
from neural_core.sky_sports_madridista import (
    consultar_partido_actual_madrid,
    generar_prediccion_deportiva,
    es_orden_ver_partido_madrid,
    instrucciones_madridista,
    CANALES_OFICIALES,
    AGENDA_REAL_MADRID,
)


def test_consultar_partido_actual():
    info = consultar_partido_actual_madrid()
    assert "partido" in info
    assert "esta_en_vivo" in info
    assert "canales_autorizados" in info
    assert info["partido"]["rival"] == "RB Leipzig"
    assert info["partido"]["local"] is False
    assert len(info["canales_autorizados"]) > 0


def test_generar_prediccion():
    pred = generar_prediccion_deportiva("Real Madrid", "FC Barcelona", "LaLiga")
    assert pred["partido"] == "Real Madrid vs FC Barcelona"
    assert "probabilidades" in pred
    assert pred["probabilidades"]["victoria_local_pct"] > 0
    assert pred["probabilidades"]["victoria_visitante_pct"] > 0
    assert pred["probabilidades"]["empate_pct"] > 0
    total = (
        pred["probabilidades"]["victoria_local_pct"]
        + pred["probabilidades"]["victoria_visitante_pct"]
        + pred["probabilidades"]["empate_pct"]
    )
    assert round(total) == 100
    assert "marcador_probable" in pred
    assert "jugadores_clave" in pred
    assert len(pred["jugadores_clave"]) > 0


def test_deteccion_orden_ver_partido():
    positivos = [
        "SKY, muéstrame el partido en vivo del Real Madrid",
        "muestrame el partido en vivo del real madrid por favor",
        "quiero ver el partido del madrid en directo",
        "pon el partido del real madrid en vivo",
        "ver el clásico real madrid barcelona en vivo",
    ]
    for frase in positivos:
        assert es_orden_ver_partido_madrid(frase) is True, f"Fallo al detectar: {frase}"

    negativos = [
        "¿Quién ganó el balón de oro?",
        "Escribe un código en Python",
        "Calcula la derivada de x^2",
        "Cuéntame la historia del Real Madrid",
    ]
    for frase in negativos:
        assert es_orden_ver_partido_madrid(frase) is False, f"Falso positivo en: {frase}"


def test_instrucciones_madridista():
    inst_deporte = instrucciones_madridista("deportes", "Qué opinas del partido?")
    assert "Hala Madrid y nada más" in inst_deporte

    inst_madrid = instrucciones_madridista("deportes", "¡Hala Madrid! Qué opinas de la Champions?")
    assert "Hala Madrid y nada más" in inst_madrid
    assert "15 Copas de Europa" in inst_madrid


def test_catalogo_canales_autorizados():
    assert len(CANALES_OFICIALES) >= 4
    nombres = [c["nombre"] for c in CANALES_OFICIALES]
    assert "Real Madrid TV Oficial" in nombres
    assert any("ViX" in n for n in nombres)
    assert any("ESPN" in n for n in nombres)
    assert any("Fútbol Libre" in n for n in nombres)
    urls = [c["url_oficial"] for c in CANALES_OFICIALES]
    assert "https://futbollibrefullhd.org/" in urls
