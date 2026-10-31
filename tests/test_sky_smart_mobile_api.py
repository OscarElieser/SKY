"""End-to-end mobile scope + smart router dispatch, no cloud or real GPU."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mobile_sky_auto_requires_scoped_auth_and_respects_consent():
    code = r"""
import os, sys, types, tempfile
from pathlib import Path
from fastapi import HTTPException

tmp = tempfile.TemporaryDirectory()
os.environ["SKY_MOBILE_AGENT_DB"] = str(Path(tmp.name) / "agent.db")
os.environ["SKY_MOBILE_CHAT_DB"] = str(Path(tmp.name) / "chat.db")
api = types.ModuleType("metaverse.api")
api.require_key = lambda: True
sys.modules["metaverse.api"] = api

from metaverse import mobile_chat_api as endpoint
from neural_core import sky_mobile_agent as agent
phone = agent.pair(agent.pairing_code()["code"], "SKY Android test")
did, agent_token = phone["device_id"], phone["token"]
invite = endpoint.create_invitation(endpoint.Device(device_id=did))["code"]
chat_token = endpoint.exchange_invitation(
    endpoint.ChatPair(device_id=did, code=invite),
    x_sky_mobile_token=agent_token)["token"]
calls = []
def fake_smart(messages, **kwargs):
    calls.append(kwargs)
    assert messages[-1]["content"] == "explica las variables"
    return {"respuesta": "Motor real simulado", "proveedor": "ollama",
            "nube": False, "acciones_ejecutadas": False}
endpoint.smart.generate = fake_smart

payload = endpoint.MobileChatRequest(
    device_id=did, texto="explica las variables", proveedor="sky_auto")
try:
    endpoint.mobile_chat_text(payload, x_sky_chat_token=agent_token)
except HTTPException as exc:
    assert exc.status_code == 401
else:
    raise AssertionError("Agent token cannot call SKY Automatic")

result = endpoint.mobile_chat_text(payload, x_sky_chat_token=chat_token)
assert result["nube"] is False
assert calls[-1]["cloud_consent"] is False
assert calls[-1]["private_cloud_consent"] is False
payload = endpoint.MobileChatRequest(
    device_id=did, texto="explica las variables", proveedor="sky_auto",
    autorizar_nube=True, autorizar_datos_privados=True)
result = endpoint.mobile_chat_text(payload, x_sky_chat_token=chat_token)
assert calls[-1]["cloud_consent"] is True
assert calls[-1]["private_cloud_consent"] is True
assert result["acciones_ejecutadas"] is False

endpoint.revoke_mobile_chat(endpoint.Device(device_id=did))
try:
    endpoint.mobile_chat_text(payload, x_sky_chat_token=chat_token)
except HTTPException as exc:
    assert exc.status_code == 401
else:
    raise AssertionError("Revoked mobile session must not route automatically")
"""
    completed = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                               capture_output=True, text=True, timeout=25)
    assert completed.returncode == 0, completed.stderr[-3000:]
