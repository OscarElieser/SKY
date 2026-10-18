"""Pruebas locales sin llamadas a Internet ni uso de credenciales reales."""
import base64
import pytest
import sys
from types import SimpleNamespace
from neural_core import baqueano, gemini_provider


def test_ruta_limitada_a_contenido_publicable():
    assert baqueano.ruta_editable('website/index.html')
    assert baqueano.ruta_editable('web/index.html')
    assert baqueano.ruta_editable('docs/guia.md')
    for ruta in ('.env','website/.env','website/secret.key','admin/config.js',
                 'website/../../../foo.html','website/.github/workflows/deploy.yml',
                 'website/privado.json','/website/index.html'):
        assert not baqueano.ruta_editable(ruta)


def test_pr_exige_permiso_y_no_contacta_red(monkeypatch):
    monkeypatch.setenv('BAQUEANO_GITHUB_TOKEN','')
    with pytest.raises(PermissionError):
        baqueano.propuesta_pr('website/index.html','abc','Propuesta de cambio', 'a'*40,'NO')
    with pytest.raises(baqueano.IntegracionError):
        baqueano.propuesta_pr('website/index.html','abc','Propuesta de cambio', 'a'*40,'CREAR PROPUESTA')


def test_diff():
    d=baqueano.vista_diff('texto uno','texto dos','website/index.html')
    assert '-texto uno' in d and '+texto dos' in d


def test_supabase_no_acepta_tablas_arbitrarias():
    with pytest.raises(ValueError):
        baqueano.supabase_publico('auth.users')


def test_github_archivo_decodifica(monkeypatch):
    v=base64.b64encode(b'<h1>hola</h1>').decode()
    monkeypatch.setattr(baqueano,'_json_api',lambda *a,**k:{'type':'file','size':13,'encoding':'base64',
                                                       'content':v,'sha':'a'*40,'html_url':'https://github.com/o/r'})
    a=baqueano.leer_archivo('website/index.html')
    assert a['contenido']=='<h1>hola</h1>'


def test_gemini_errores_antes_de_llamar_api(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    assert gemini_provider.disponible() is False
    with pytest.raises(gemini_provider.GeminiError):
        gemini_provider._cliente()
    with pytest.raises(ValueError):
        gemini_provider.analizar_imagen('imagen',b'123','application/octet-stream')
    with pytest.raises(ValueError):
        gemini_provider.generar_imagen('  ')


def test_gemini_texto_mock(monkeypatch):
    class R:
        text='Gemini probando, sin red'
    class M:
        def generate_content(self,**kwargs):
            assert kwargs['model']=='gemini-flash-latest'
            assert kwargs['config'].system_instruction == 'Eres NeuralT'
            return R()
    class C:
        models=M()
        def close(self): pass
    mock_module=SimpleNamespace(types=SimpleNamespace(GenerateContentConfig=lambda **kwargs:SimpleNamespace(**kwargs)))
    monkeypatch.setitem(sys.modules,'google.genai',mock_module)
    monkeypatch.setattr(gemini_provider,'_cliente',lambda:C())
    respuesta=gemini_provider.responder_gemini([
        {'role':'system','content':'Eres NeuralT'},
        {'role':'user','content':'Hola'}],modelo='gemini-flash-latest')
    assert respuesta.startswith('Gemini probando')
