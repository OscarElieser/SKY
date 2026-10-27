"""Isolated API behavior checks; no provider calls, tokens or real devices."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_home_chat_never_sends_private_data_without_two_consents():
    # Stub only the circular parent import in a separate process, so other
    # tests can still import the real metaverse.api normally.
    script = r'''
import sys, types
api = types.ModuleType('metaverse.api')
api.require_key = lambda: True
sys.modules['metaverse.api'] = api
providers = types.ModuleType('neural_core.providers')
providers.ProviderError = RuntimeError
sys.modules['neural_core.providers'] = providers
from fastapi import HTTPException
from metaverse import sky_home_api as home

assert home.router.dependencies  # auth dependency must remain registered
home._availability = lambda: (False, ('openai',), False)
calls = []
def fake_reply(messages, provider, max_output_tokens):
    calls.append((messages, provider))
    return 'Respuesta de prueba'
providers.reply = fake_reply

def blocked(payload):
    try:
        home.home_chat(home.HomeChat(**payload))
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError('Unexpected cloud transfer allowed')

blocked({'texto': 'datos privados'})
blocked({'texto': 'datos privados', 'autorizar_nube': True})
blocked({'texto': 'datos privados', 'autorizar_datos_privados': True})
assert not calls
response = home.home_chat(home.HomeChat(texto='explica SSD', datos='generales', autorizar_nube=True))
assert response['nube'] and response['proveedor'] == 'openai'
assert response['acciones_ejecutadas'] is False
assert calls[0][0][-1]['content'] == 'explica SSD'

home._availability = lambda: (True, ('openai',), True)
blocked({'texto': 'privado', 'proveedor': 'openai', 'autorizar_nube': True, 'autorizar_datos_privados': True})
response = home.home_chat(home.HomeChat(texto='privado'))
assert response['proveedor'] == 'ollama' and response['nube'] is False

# An authorized AUTO cloud error may fall back to local, but must say so.
home._availability = lambda: (True, ('openai',), False)
def cloud_fails(messages, provider, max_output_tokens):
    if provider == 'openai':
        raise providers.ProviderError('Simulated network failure')
    return 'Respuesta local'
providers.reply = cloud_fails
response = home.home_chat(home.HomeChat(texto='explica SSD', datos='generales', autorizar_nube=True))
assert response['proveedor'] == 'ollama' and response['respaldo_local'] is True
assert response['nube'] is False
# An explicit cloud selection never changes to a local model.
try:
    home.home_chat(home.HomeChat(texto='explica SSD', datos='generales', proveedor='openai', autorizar_nube=True))
except HTTPException as exc:
    assert exc.status_code == 503
else:
    raise AssertionError('Explicit cloud provider unexpectedly changed')
'''
    completed = subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                               capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stderr[-3000:]
