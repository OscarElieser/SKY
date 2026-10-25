"""SKY: integration real contracts without external data transmission."""
import json
import pytest
from neural_core import sky_make_bridge as make
from neural_core import sky_framework_agents as frameworks
from neural_core import sky_train_model as training


def test_make_requires_approval_and_alias(monkeypatch):
    monkeypatch.setenv("SKY_MAKE_ALIASES","avisos")
    monkeypatch.setenv("SKY_MAKE_WEBHOOK_AVISOS","https://hook.eu2.make.com/abcd12345token")
    with pytest.raises(PermissionError):make.trigger("avisos",{"message":"test"})
    with pytest.raises(make.MakeInvalid):make.trigger("unknown",{"message":"test"},approved=True)
    monkeypatch.setenv("SKY_LOCAL_ONLY","1")
    with pytest.raises(make.MakeInvalid):make.trigger("avisos",{"message":"test"},approved=True)


@pytest.mark.parametrize("url",[
    "http://hook.eu2.make.com/abcdefghij",
    "https://evil.example.com/abcdefghij",
    "https://hook.eu2.make.com.evil.com/abcdefghij",
    "https://hook.eu2.make.com/abcdefghij?token=hello",
    "https://hook.eu2.make.com:8443/abcdefghij",
    "https://bob@hook.eu2.make.com/abcdefghij",
])
def test_make_blocks_unapproved_hosts(monkeypatch,url):
    monkeypatch.setenv("SKY_MAKE_WEBHOOK_AVISOS",url)
    with pytest.raises(make.MakeInvalid):make._webhook("avisos")


def test_make_real_transport_with_no_retry_and_no_fake_completion(monkeypatch):
    monkeypatch.setenv("SKY_LOCAL_ONLY","0")
    monkeypatch.setenv("SKY_MAKE_ALIASES","avisos")
    monkeypatch.setenv("SKY_MAKE_WEBHOOK_AVISOS","https://hook.eu2.make.com/abcdefghij")
    monkeypatch.setenv("SKY_MAKE_API_KEY_AVISOS","private_make_key")
    requests=[]
    class FakeResponse:
        status_code=202
    class FakeClient:
        def __init__(self,**kwargs):
            assert kwargs["follow_redirects"] is False
            assert kwargs["trust_env"] is False
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,**kwargs):
            requests.append((url,kwargs))
            return FakeResponse()
    monkeypatch.setattr(make.httpx,"Client",FakeClient)
    result=make.trigger("avisos",{"message":"Informe SKY"},approved=True)
    assert result["delivered_to_webhook"] is True
    assert result["scenario_completed"] is False
    assert len(requests)==1
    assert requests[0][1]["headers"]["x-make-apikey"]=="private_make_key"


def test_frameworks_fail_closed_when_not_installed(monkeypatch):
    monkeypatch.setenv("SKY_FRAMEWORK_CREWAI_ENABLED","0")
    assert frameworks.configured_frameworks()["controller"]=="SKY"
    with pytest.raises(frameworks.FrameworkUnavailable):
        frameworks.consult("crewai","Prepara un plan para enseñar programación")
    with pytest.raises(frameworks.FrameworkInvalid):
        frameworks.consult("untrusted_framework","Prepara un plan para enseñar programación")


def test_langchain_real_api_contract_with_simulated_local_class(monkeypatch):
    import sys
    from types import ModuleType
    import importlib.util
    from neural_core import sky_lmstudio as lm
    monkeypatch.setenv("SKY_FRAMEWORK_LANGCHAIN_ENABLED","1")
    monkeypatch.setenv("SKY_LMSTUDIO_ENABLED","1")
    monkeypatch.setenv("SKY_LMSTUDIO_MODEL","model-local")
    original=importlib.util.find_spec
    monkeypatch.setattr(importlib.util,"find_spec",lambda name:
                        object() if name=="langchain_openai" else original(name))
    lc=ModuleType("langchain_openai")
    events=[]
    class Chat:
        def __init__(self,**kwargs):events.append(kwargs)
        def invoke(self,messages):return type("Response",(),{"content":"Análisis original preparado localmente por SKY"})()
    lc.ChatOpenAI=Chat
    messages=ModuleType("langchain_core.messages")
    messages.SystemMessage=lambda content:("system",content)
    messages.HumanMessage=lambda content:("user",content)
    monkeypatch.setitem(sys.modules,"langchain_openai",lc)
    monkeypatch.setitem(sys.modules,"langchain_core.messages",messages)
    response=frameworks.consult("langchain","Compara rutas para una aplicación educativa")
    assert response["provider"]=="lmstudio_local"
    assert response["executed_external_actions"] is False
    assert events[0]["base_url"].startswith("http://127.0.0.1:")
    assert events[0]["use_responses_api"] is False


def test_training_requires_owner_rights(tmp_path):
    dataset=tmp_path/"data.jsonl"
    dataset.write_text("\n".join(json.dumps({
        "instruction":f"Consulta autorizada {i}",
        "response":f"Respuesta consentida {i}",
        "approved_for_training":True}) for i in range(22)),encoding="utf-8")
    pairs=training.validate_dataset(dataset)
    a,b=training.split_dataset(pairs)
    assert len(a)+len(b)==22
    assert len(b)>0
    with pytest.raises(training.SkyTrainingError):
        training.train(dataset=str(dataset),base_model=str(tmp_path),output=str(tmp_path/"model"))


def test_training_rejects_unapproved_and_secrets(tmp_path):
    data=tmp_path/"private.jsonl"
    rows=[{"instruction":"Una pregunta de prueba", "response":"Respuesta válida de prueba",
           "approved_for_training":True} for _ in range(20)]
    rows[4]["approved_for_training"]=False
    data.write_text("\n".join(json.dumps(x) for x in rows))
    with pytest.raises(training.SkyTrainingError):
        training.validate_dataset(data)
    rows[4]["approved_for_training"]=True
    rows[5]["response"]="-----BEGIN PRIVATE KEY----- forbidden"
    data.write_text("\n".join(json.dumps(x) for x in rows))
    with pytest.raises(training.SkyTrainingError):
        training.validate_dataset(data)
