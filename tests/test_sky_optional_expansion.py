"""Opt-in SKY expansion: offline adapter, security and no-regression checks.

Provider calls are mocked explicitly. The test suite does NOT claim that owner
accounts, Windows controls or external services were live-verified.
"""
from __future__ import annotations
import inspect
import json
from types import SimpleNamespace
from pathlib import Path
import pytest

from neural_core import sky_research_connectors as research
from neural_core import sky_n8n_bridge as bridge
from neural_core import sky_research_commands as commands
from neural_core import providers


def test_semantic_scholar_parses_provenance_and_stops_at_metadata(monkeypatch):
    seen={}
    def fake_get(host,path,params,**kw):
        seen.update(host=host,path=path,params=params,kw=kw)
        return {"data":[{"title":"Learning research","year":2026,
                         "externalIds":{"DOI":"10.1000/test"},
                         "authors":[{"name":"A. Scientist"}],
                         "url":"https://www.semanticscholar.org/paper/example",
                         "abstract":"A measured study.","citationCount":3}]}
    monkeypatch.setattr(research,"_get",fake_get)
    r=research.semantic_scholar("interactive lessons",3)
    assert r["ok"] and r["results_observed"]==1
    assert seen["host"]=="api.semanticscholar.org"
    assert "abstract" in seen["params"]["fields"]
    assert r["items"][0]["doi"]=="10.1000/test"
    assert r["items"][0]["full_text_read"] is False and not r["items"][0]["peer_review_verified"]
    with pytest.raises(research.ResearchInputError):
        research.semantic_scholar("anything", 300)


def test_zotero_private_read_only_with_fixed_user_and_filtered_records(monkeypatch):
    monkeypatch.setenv("SKY_ZOTERO_USER_ID","123456")
    monkeypatch.setenv("SKY_ZOTERO_API_KEY","fake-key-no-network")
    seen={}
    def fake_get(host,path,params,**kw):
        seen.update(host=host,path=path,params=params,kw=kw)
        return [{"key":"ABCD1234","data":{"title":"Reference", "date":"2025",
                 "DOI":"10.1000/test","creators":[{"lastName":"Cruz"}],
                 "secret":"not returned"}}]
    monkeypatch.setattr(research,"_get",fake_get)
    result=research.zotero_items("innovation")
    assert result["ok"] and result["private_library"] and result["not_published"]
    assert seen["path"]=="/users/123456/items"
    assert seen["kw"]["headers"]["Zotero-API-Key"]=="fake-key-no-network"
    assert "secret" not in json.dumps(result)
    monkeypatch.setenv("SKY_ZOTERO_USER_ID","../../victim")
    with pytest.raises(research.ResearchConnectorError):
        research.zotero_items()


def test_wolfram_requires_appid_and_never_returns_credentials(monkeypatch):
    monkeypatch.delenv("SKY_WOLFRAM_APP_ID",raising=False)
    with pytest.raises(research.ResearchConnectorError):
        research.wolfram_short_answer("2+2")
    monkeypatch.setenv("SKY_WOLFRAM_APP_ID","NO_REAL_APP_ID")
    captured={}
    def fake_get(host,path,params,**kw):
        captured.update(host=host,path=path,params=params,kw=kw)
        return "4"
    monkeypatch.setattr(research,"_get",fake_get)
    r=research.wolfram_short_answer("2+2")
    assert r["answer"]=="4" and "NO_REAL_APP_ID" not in json.dumps(r)
    assert captured["path"]=="/v1/result" and captured["kw"]["plain"] is True
    with pytest.raises(research.ResearchInputError):
        research.wolfram_short_answer("2+2",units="imaginary")


def test_research_commands_only_explicit_provider_names(monkeypatch):
    monkeypatch.setattr(research,"semantic_scholar",lambda q,limit=5:{
        "ok":True,"items":[{"title":"Paper title","year":2024,"doi":"10.1/x",
         "url":"https://example.org/p"}]})
    assert commands.interpretar("SKY, investiga en Semantic Scholar sobre pedagogía")["tipo"]=="respuesta"
    assert commands.interpretar("Busca información sobre pedagogía") is None
    assert commands.interpretar("Despliega el servidor n8n") is None


def test_n8n_strict_origin_security(monkeypatch):
    monkeypatch.setenv("SKY_N8N_ALLOWED_HOSTS","sky-n8n.example.org")
    for bad in ("http://sky-n8n.example.org","https://evil.example.org",
                "https://sky-n8n.example.org@evil.example.org","https://127.0.0.1",
                "https://sky-n8n.example.org/other","https://sky-n8n.example.org?token=123"):
        monkeypatch.setenv("SKY_N8N_URL",bad)
        with pytest.raises(bridge.N8NInvalid):
            bridge._base()
    monkeypatch.setenv("SKY_N8N_URL","https://sky-n8n.example.org")
    assert bridge._base()=="https://sky-n8n.example.org"


def test_n8n_loopback_is_opt_in_and_port_locked(monkeypatch):
    monkeypatch.setenv("SKY_N8N_URL","http://127.0.0.1:5678")
    monkeypatch.delenv("SKY_N8N_ALLOW_LOCAL",raising=False)
    with pytest.raises(bridge.N8NInvalid):
        bridge._base()
    monkeypatch.setenv("SKY_N8N_ALLOW_LOCAL","1")
    assert bridge._base()=="http://127.0.0.1:5678"
    monkeypatch.setenv("SKY_N8N_URL","http://127.0.0.1:9999")
    with pytest.raises(bridge.N8NInvalid):
        bridge._base()


def test_n8n_read_only_listing_filters_sensitive_definitions(monkeypatch):
    monkeypatch.setenv("SKY_N8N_API_KEY","dummy")
    calls=[]
    def fake_network(method,endpoint,headers,body=None):
        calls.append((method,endpoint))
        return {"data":[{"id":"1","name":"Auditoría","active":True,
             "nodes":[{"parameters":{"password":"never-echo"}}]}]}
    monkeypatch.setattr(bridge,"_network",fake_network)
    r=bridge.list_workflows()
    assert calls==[("GET","/api/v1/workflows?limit=10")]
    assert r["items"][0]["active"]
    assert "never-echo" not in json.dumps(r)
    assert "nodes" not in json.dumps(r)


def test_n8n_never_dispatches_from_text_or_without_allowlist_pin(monkeypatch):
    monkeypatch.setenv("SKY_N8N_ALLOW_DISPATCH","1")
    monkeypatch.setenv("SKY_N8N_ALLOWED_WEBHOOKS","teacher_reminder")
    monkeypatch.setenv("SKY_N8N_WEBHOOK_SECRET","s"*32)
    invoked=[]
    monkeypatch.setattr(bridge,"_network",lambda *a,**k:invoked.append((a,k)) or {})
    with pytest.raises(bridge.N8NInvalid):
        bridge.dispatch_webhook("teacher_reminder",approved=False)
    with pytest.raises(bridge.N8NInvalid):
        bridge.dispatch_webhook("unlisted",approved=True)
    assert invoked==[]
    result=bridge.dispatch_webhook("teacher_reminder",approved=True)
    assert invoked and result["status"]=="DISPATCHED_UNVERIFIED" and result["verified"] is False
    assert "s"*32 not in json.dumps(result)


def test_openrouter_and_huggingface_opt_in_without_auto_provider_switch(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY","dummy")
    monkeypatch.setenv("OPENROUTER_MODEL","org/model-explicit")
    monkeypatch.setenv("HF_TOKEN","dummy")
    monkeypatch.setenv("HF_MODEL","org/model-explicit")
    class MockClient:
        def __init__(self):self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.complete))
        def complete(self,**kwargs):
            assert kwargs["model"]=="org/model-explicit" and kwargs["stream"] is False
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Verified mock output"))])
        def close(self):pass
    seen=[]
    def fake_openai(key,base_url=None):
        seen.append(base_url)
        return MockClient()
    monkeypatch.setattr(providers,"_openai_sdk",fake_openai)
    messages=[{"role":"system","content":"Do not invent"},{"role":"user","content":"Hola SKY"}]
    for name in ("openrouter","huggingface"):
        assert providers.reply(messages,name)=="Verified mock output"
    assert seen==["https://openrouter.ai/api/v1","https://router.huggingface.co/v1"]
    assert "openrouter" not in providers.AUTO_ORDER and "huggingface" not in providers.AUTO_ORDER
    monkeypatch.setenv("SKY_LOCAL_ONLY","1")
    with pytest.raises(providers.ProviderError):
        providers.reply(messages,"openrouter")


def test_registered_capabilities_and_private_endpoint_guards():
    from neural_core import sky_integraciones
    names={row["id"] for row in sky_integraciones.listar()}
    assert {"openrouter","huggingface","semantic_scholar","zotero","wolfram","n8n"}<=names
    api=Path("metaverse/api.py").read_text(encoding="utf-8")
    assert 'exigir_pin(request,"ejecución de automatización externa n8n")' in api
    assert api.count('dependencies=[Depends(require_key)]')>=6
    src=Path("neural_core/sky_asistente_personal.py").read_text(encoding="utf-8")
    assert "sky_research_commands.interpretar(texto)" in src


def test_local_only_blocks_external_research_and_remote_automation(monkeypatch):
    monkeypatch.setenv("SKY_LOCAL_ONLY","1")
    with pytest.raises(research.ResearchConnectorError):
        research._get("api.semanticscholar.org","/graph/v1/paper/search",{"query":"x"})
    monkeypatch.setenv("SKY_N8N_URL","https://sky-n8n.example.org")
    monkeypatch.setenv("SKY_N8N_ALLOWED_HOSTS","sky-n8n.example.org")
    with pytest.raises(bridge.N8NInvalid):
        bridge._base()
    monkeypatch.setenv("SKY_N8N_URL","http://127.0.0.1:5678")
    monkeypatch.setenv("SKY_N8N_ALLOW_LOCAL","1")
    assert bridge._base()=="http://127.0.0.1:5678"
