"""Regression for mobile chat pairing; all tests use isolated SQLite and no network."""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from neural_core import sky_mobile_agent as agent
from neural_core import sky_mobile_chat as chat


@pytest.fixture
def isolated(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("SKY_MOBILE_AGENT_DB", str(Path(tmp) / "agents.db"))
        monkeypatch.setenv("SKY_MOBILE_CHAT_DB", str(Path(tmp) / "chat.db"))
        yield


def _phone():
    return agent.pair(agent.pairing_code()["code"], "Android personal")


def test_pair_requires_agent_and_one_time_owner_invite(isolated):
    phone = _phone()
    code = chat.invite(phone["device_id"])["code"]
    with pytest.raises(PermissionError):
        chat.pair(phone["device_id"], "not-an-agent-token", code)
    result = chat.pair(phone["device_id"], phone["token"], code)
    assert result["scope"] == "chat:write"
    assert result["owner_key"] is False
    assert result["token"] != phone["token"]
    assert "owner_key" not in agent.pairing_code()
    chat.authorize(phone["device_id"], result["token"])
    with pytest.raises(PermissionError):
        chat.authorize(phone["device_id"], phone["token"])
    with pytest.raises(PermissionError):
        chat.pair(phone["device_id"], phone["token"], code)


def test_revoke_and_renew_are_immediate(isolated):
    phone = _phone()
    device, agent_token = phone["device_id"], phone["token"]
    first = chat.pair(device, agent_token, chat.invite(device)["code"])["token"]
    renewed = chat.pair(device, agent_token, chat.invite(device)["code"])["token"]
    with pytest.raises(PermissionError):
        chat.authorize(device, first)
    chat.authorize(device, renewed)
    chat.revoke(device)
    with pytest.raises(PermissionError):
        chat.authorize(device, renewed)
    next_token = chat.pair(device, agent_token, chat.invite(device)["code"])["token"]
    agent.revoke(device, agent_token)
    with pytest.raises(PermissionError):
        chat.authorize(device, next_token)
    with pytest.raises(ValueError):
        chat.invite(device)


def test_rate_limit_and_expiration(isolated):
    phone = _phone()
    device = phone["device_id"]
    with patch.object(chat.time, "time", return_value=1000.0):
        code = chat.invite(device)["code"]
    with patch.object(chat.time, "time", return_value=1301.0):
        with pytest.raises(PermissionError):
            chat.pair(device, phone["token"], code)
    with patch.object(chat.time, "time", return_value=1600.0):
        token = chat.pair(device, phone["token"], chat.invite(device)["code"])["token"]
        for _ in range(chat.RATE_LIMIT):
            chat.authorize(device, token)
        with pytest.raises(PermissionError, match="Límite"):
            chat.authorize(device, token)
    with patch.object(chat.time, "time", return_value=1661.0):
        chat.authorize(device, token)
    with patch.object(chat.time, "time", return_value=1600.0 + chat.SESSION_TTL):
        with pytest.raises(PermissionError):
            chat.authorize(device, token)


def test_api_rejects_unauthorized_chat_before_provider(isolated, monkeypatch):
    import subprocess
    import sys
    # Isolated API imports avoid starting SKY Windows services on CI.
    script = r'''
import sys, types, tempfile, os
from pathlib import Path
tmp = tempfile.TemporaryDirectory()
os.environ["SKY_MOBILE_AGENT_DB"] = str(Path(tmp.name) / "agent.sqlite3")
os.environ["SKY_MOBILE_CHAT_DB"] = str(Path(tmp.name) / "chat.sqlite3")
api = types.ModuleType("metaverse.api")
api.require_key = lambda: True
sys.modules["metaverse.api"] = api
from metaverse import sky_home_api
from metaverse import mobile_chat_api as endpoint
from neural_core import sky_mobile_agent as agent
provider_calls = []
def mocked_home_chat(payload):
    provider_calls.append(payload)
    return {"respuesta": "SKY respondió", "acciones_ejecutadas": False}
endpoint.home_chat = mocked_home_chat
assert endpoint.owner.dependencies
device = agent.pair(agent.pairing_code()["code"], "Android personal")
did, atoken = device["device_id"], device["token"]
payload = endpoint.MobileChatRequest(device_id=did, texto="Hola")
from fastapi import HTTPException
try:
    endpoint.mobile_chat_text(payload, x_sky_chat_token=atoken)
except HTTPException as e:
    assert e.status_code == 401
else:
    raise AssertionError("Agent token wrongly allowed chat")
assert not provider_calls
inv = endpoint.create_invitation(endpoint.Device(device_id=did))
paired = endpoint.exchange_invitation(endpoint.ChatPair(device_id=did, code=inv["code"]), x_sky_mobile_token=atoken)
assert paired["scope"] == "chat:write"
ok = endpoint.mobile_chat_text(payload, x_sky_chat_token=paired["token"])
assert ok["acciones_ejecutadas"] is False and len(provider_calls) == 1
assert provider_calls[0].autorizar_nube is False
assert provider_calls[0].datos == "privados"
# Status is scoped, read-only, and does not pretend to verify generated text.
with __import__("unittest.mock", fromlist=["patch"]).patch.object(
        endpoint.inference, "readiness",
        return_value={"local_ollama_ready": True, "ready_workers": 1,
                      "configured_workers": 1, "model_output_verified": False}):
    status = endpoint.mobile_chat_status(endpoint.Device(device_id=did),
                                        x_sky_chat_token=paired["token"])
assert status["service"] == "SKY API"
assert status["local_ollama_ready"] is True
assert status["model_output_verified"] is False
try:
    endpoint.mobile_chat_status(endpoint.Device(device_id=did), x_sky_chat_token=atoken)
except HTTPException as e:
    assert e.status_code == 401
else:
    raise AssertionError("Agent token wrongly allowed private API status")
assert len(provider_calls) == 1  # no model inference performed by status
# Dedicated local-only inference is isolated from any third-party provider.
def fake_inference(messages, max_output_tokens):
    assert messages[-1]["content"] == "explica el método científico"
    assert max_output_tokens == 2048
    return {"respuesta": "Inferencia autenticada desde SKY", "proveedor": "ollama",
            "nube": False, "acciones_ejecutadas": False, "operacion": "test"}
endpoint.inference.generate = fake_inference
local = endpoint.mobile_chat_text(endpoint.MobileChatRequest(
    device_id=did, texto="explica el método científico", proveedor="ollama"),
    x_sky_chat_token=paired["token"])
assert local["proveedor"] == "ollama" and local["nube"] is False
assert len(provider_calls) == 1  # home provider never invoked
try:
    endpoint.mobile_chat_text(endpoint.MobileChatRequest(
        device_id=did, texto="texto", proveedor="ollama", autorizar_nube=True),
        x_sky_chat_token=paired["token"])
except HTTPException as e:
    assert e.status_code == 400
else:
    raise AssertionError("Ollama-only must reject cloud transfer flags")
endpoint.revoke_mobile_chat(endpoint.Device(device_id=did))
try:
    endpoint.mobile_chat_text(payload, x_sky_chat_token=paired["token"])
except HTTPException as e:
    assert e.status_code == 401
else:
    raise AssertionError("Revoked chat token accepted")
'''
    result = subprocess.run([sys.executable, "-c", script],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-2000:]
