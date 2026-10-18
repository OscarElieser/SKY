"""Contratos offline para proveedores multi-IA. Nunca usan claves ni la red real."""
from types import SimpleNamespace as NS
import sys
import types
import pytest
from neural_core import providers

MESSAGES=[{'role':'system','content':'Sos SKY'}, {'role':'user','content':'Hola'}]

@pytest.mark.parametrize('provider,secret',[
    ('gemini','GEMINI_API_KEY'),('openai','OPENAI_API_KEY'),
    ('anthropic','ANTHROPIC_API_KEY'),('mistral','MISTRAL_API_KEY'),
    ('groq','GROQ_API_KEY'),('deepseek','DEEPSEEK_API_KEY')])
def test_no_envia_sin_clave(monkeypatch,provider,secret):
    monkeypatch.delenv(secret,raising=False)
    assert not providers.provider_ready(provider)
    with pytest.raises(providers.ProviderError):providers.reply(MESSAGES,provider)

def test_seleccion_automatica_segun_area(monkeypatch):
    for cfg in providers.PROVIDERS.values():
        if cfg.env:monkeypatch.delenv(cfg.env,raising=False)
    monkeypatch.setenv('GEMINI_API_KEY','fake')
    monkeypatch.setenv('ANTHROPIC_API_KEY','fake')
    assert providers.choose_provider('auto','Programación Flutter')[0]=='anthropic'
    assert providers.choose_provider('auto','Educación primaria')[0]=='gemini'
    assert providers.choose_provider('auto','Campaña negocio')[0]=='gemini'  # sin OpenAI configurado

def test_openai_responses_api(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','dummy')
    got=[]
    class Responses:
        def create(self,**kw):
            got.append(kw);return NS(output_text='Respuesta SKY GPT')
    class Client:
        responses=Responses()
        def close(self):got.append('closed')
    monkeypatch.setattr(providers,'_openai_sdk',lambda *a,**kw:Client())
    assert providers.reply(MESSAGES,'openai')=='Respuesta SKY GPT'
    assert got[0]['instructions']=='Sos SKY'
    assert got[0]['store'] is False
    assert got[-1]=='closed'

def test_anthropic_messages(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY','dummy')
    seen=[]
    class Msg:
        def create(self,**kw):
            seen.append(kw);return NS(content=[NS(type='text',text='Hola SKY'),NS(type='tool_use',text=None)])
    class Client:
        messages=Msg()
        def close(self):seen.append('closed')
    m=types.ModuleType('anthropic');m.Anthropic=lambda **kw:Client()
    monkeypatch.setitem(sys.modules,'anthropic',m)
    assert providers.reply(MESSAGES,'anthropic')=='Hola SKY'
    assert seen[0]['system']=='Sos SKY'
    assert seen[-1]=='closed'

def test_mistral_chat(monkeypatch):
    monkeypatch.setenv('MISTRAL_API_KEY','dummy')
    seen=[]
    class Chat:
        def complete(self,**kw):
            seen.append(kw);return NS(choices=[NS(message=NS(content='Mistral responde'))])
    class Client:
        chat=Chat()
    m=types.ModuleType('mistralai');m.Mistral=lambda **kw:Client()
    monkeypatch.setitem(sys.modules,'mistralai',m)
    assert providers.reply(MESSAGES,'mistral')=='Mistral responde'
    assert seen[0]['messages'][0]['role']=='system'

@pytest.mark.parametrize('provider,endpoint',[
    ('groq','https://api.groq.com/openai/v1'),('deepseek','https://api.deepseek.com')])
def test_compatibles_chat(monkeypatch,provider,endpoint):
    monkeypatch.setenv(providers.PROVIDERS[provider].env,'fake')
    got=[]
    class Completions:
        def create(self,**kw):
            got.append(kw);return NS(choices=[NS(message=NS(content='Respuesta compatible'))])
    class Client:
        chat=NS(completions=Completions())
        def close(self):got.append('closed')
    def fake_factory(key,base_url=None):
        assert base_url==endpoint
        return Client()
    monkeypatch.setattr(providers,'_openai_sdk',fake_factory)
    assert providers.reply(MESSAGES,provider)=='Respuesta compatible'
    assert got[-1]=='closed'

def test_mensajes_invalidos_no_se_envian(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','fake')
    called=[]
    monkeypatch.setattr(providers,'_openai_sdk',lambda *a,**k:called.append(1))
    with pytest.raises(ValueError):providers.reply([{'role':'user','content':'Hola'}],'openai')
    assert not called

def test_no_sustituye_proveedor_tras_error(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','dummy')
    def failing(*a,**k):raise ConnectionError('failed API')
    monkeypatch.setattr(providers,'_openai_sdk',failing)
    with pytest.raises(providers.ProviderError,match='OpenAI'):
        providers.reply(MESSAGES,'openai')

def test_modelo_personalizable(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','fake')
    monkeypatch.setenv('GEMINI_MODEL','gemini-ejemplo-personal')
    assert providers.choose_provider('gemini')[1]=='gemini-ejemplo-personal'

def test_sky_wakeword_sin_nombre_anterior():
    from sky_manos_libres import text_after_wake
    assert text_after_wake('SKY, abrí Baqueano') == 'abrí Baqueano'
    assert text_after_wake('Esquai abrí el navegador') == 'abrí el navegador'
    assert text_after_wake('Abre el navegador') is None
