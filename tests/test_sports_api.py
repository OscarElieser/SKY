"""Tests para los endpoints REST deportivos en metaverse/api.py."""
import pytest
from fastapi.testclient import TestClient
from metaverse.api import app

client = TestClient(app)


def test_api_sports_match():
    res = client.get("/api/sports/madrid/match")
    assert res.status_code == 200
    data = res.json()
    assert data["encontrado"] is True
    assert "partido" in data
    assert "rival" in data["partido"]
    assert "canales_disponibles" in data


def test_api_sports_channels():
    res = client.get("/api/sports/channels")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    channels = data.get("channels") or data.get("canales")
    assert len(channels) >= 4


def test_api_sports_predict():
    res = client.post(
        "/api/sports/predict",
        json={
            "local": "Real Madrid",
            "visitante": "FC Barcelona",
            "competicion": "LaLiga EA Sports"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    pred = data.get("prediccion") or data
    assert "probabilidades" in pred or "probabilidad_local" in pred
    assert "marcador_probable" in pred
    assert "analisis_tactico" in pred
