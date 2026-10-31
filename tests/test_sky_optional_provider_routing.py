"""Independent SKY API consent tests: simulated providers, no cloud contact."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_optional_providers_are_server_only_and_explicitly_authorized():
    code = r'''
import sys, types
from fastapi import HTTPException
fake_api = types.ModuleType("metaverse.api")
fake_api.require_key = lambda: True
sys.modules["metaverse.api"] = fake_api
from metaverse import sky_home_api as home
from neural_core import sky_optional_cloud_providers as cloud
home._availability = lambda: (False, ("openrouter", "cloudflare", "mistral", "groq"), False)
used = []
def stub(provider, messages, max_output_tokens):
    used.append((provider, messages[-1]["content"], max_output_tokens))
    return "SKY completó una consulta de texto"
cloud.reply = stub

def blocked(**kwargs):
    try:
        home.home_chat(home.HomeChat(texto="Analiza la práctica docente", **kwargs))
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("External provider accepted without required permission")

for name in cloud.OPTIONAL_PROVIDERS:
    blocked(proveedor=name)
    blocked(proveedor=name, autorizar_nube=True)
    blocked(proveedor=name, autorizar_datos_privados=True)
    response = home.home_chat(home.HomeChat(
        texto="Analiza la práctica docente", proveedor=name,
        datos="privados", autorizar_nube=True, autorizar_datos_privados=True))
    assert response["proveedor"] == name
    assert response["nube"] is True
    assert response["acciones_ejecutadas"] is False

assert [x[0] for x in used] == list(cloud.OPTIONAL_PROVIDERS)
assert all(x[2] == 1200 for x in used)

def quota(provider, messages, max_output_tokens):
    raise cloud.CloudProviderRateLimited("Simulated 429")
cloud.reply = quota
try:
    home.home_chat(home.HomeChat(
        texto="Consulta con cuota agotada", proveedor="openrouter",
        datos="generales", autorizar_nube=True))
except HTTPException as exc:
    assert exc.status_code == 503
else:
    raise AssertionError("Explicit provider silently changed after quota exhaustion")
assert len(used) == len(cloud.OPTIONAL_PROVIDERS)
'''
    result = subprocess.run([sys.executable, "-c", code],
                            cwd=ROOT, capture_output=True,
                            text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-3000:]
