"""SKY Design AI: real existing LLM gateway, explicit consent, safe visual tokens.

We mock the remote model interface here to isolate privacy/schema policy;
separate CI compiles the generated actual React/Flutter sources with SDKs.
"""
from __future__ import annotations

import io
import json
import zipfile
import pytest
from fastapi.testclient import TestClient

from neural_core import sky_design_ai as ai
from neural_core import sky_design_studio as studio
from neural_core import providers


def valid_design_plan() -> dict:
    return {
        "subtitle": "Explorá rutas verdaderamente humanas",
        "description": "Una experiencia de turismo local y naturaleza con itinerarios útiles.",
        "eyebrow": "TURISMO · CULTURA",
        "features": [
            {"title": "Rutas de montaña", "detail": "Descubrí senderos y paisajes.", "icon": "compass"},
            {"title": "Comunidad cercana", "detail": "Conectá directamente con guías.", "icon": "layers"},
            {"title": "Viajes seguros", "detail": "Información transparente.", "icon": "shield"},
        ],
        "style": "aurora", "layout": "immersive", "palette_index": 2,
    }


def test_validated_llm_plan_is_unique_to_brief_and_changes_react_source():
    plan=ai._validate_plan(json.dumps(valid_design_plan()))
    result=studio.create_design(
        "Ruta Luminosa", "Turismo rural y comunitario", design_plan=plan)
    cfg=json.loads(result["files"]["src/config.json"])
    assert cfg["subtitle"]==plan["subtitle"]
    assert cfg["features"]==plan["features"]
    assert cfg["description"]==plan["description"]
    assert result["colors"]["primary"]==studio._THEMES[2][0]
    assert result["style"]=="aurora"
    assert result["layout"]=="immersive"
    assert result["ai_edited_tokens"] is True
    assert result["generated_sources_built_now"] is False


def test_llm_plan_controls_flutter_content_without_executing_new_code():
    result=studio.create_design(
        "Aula Viva", "Formación innovadora", platform="flutter",
        design_plan=valid_design_plan())
    cfg=result["files"]["lib/sky_config.dart"]
    assert "Rutas de montaña" in cfg
    assert "Descubrí senderos y paisajes." in cfg
    assert "skyStyle = \"aurora\"" in cfg
    assert "skyLayout = \"immersive\"" in cfg
    assert result["compiled_on_owner_device"] is False


@pytest.mark.parametrize("overrides", [
    {"palette_index": -1}, {"palette_index": True},
    {"layout": "rm -rf"},
    {"features": [{"title":"x","detail":"hi","icon":"untrusted"}]*3},
    {"features": []},
    {"subtitle": "<script>alert(1)</script>"},
    {"description": "x"*225},
])
def test_untrusted_model_output_is_rejected(overrides):
    obj=valid_design_plan()
    obj.update(overrides)
    with pytest.raises(studio.DesignInvalid):
        ai._validate_plan(json.dumps(obj))


def test_structured_llm_response_accepts_whole_json_codeblock_only():
    payload=json.dumps(valid_design_plan())
    assert ai._validate_plan("json invalid" if False else payload)["features"]
    assert ai._validate_plan(chr(96)*3+"json\n"+payload+"\n"+chr(96)*3)["subtitle"]
    with pytest.raises(studio.DesignInvalid):
        ai._validate_plan("La IA recomienda: "+payload)


def test_cloud_provider_requires_opt_in_before_reply(monkeypatch):
    monkeypatch.setattr(providers,"choose_provider",lambda *a,**kw:("anthropic","test-model"))
    called=[]
    monkeypatch.setattr(providers,"reply",lambda *a,**kw:called.append(kw) or "{}")
    with pytest.raises(PermissionError):
        ai.compose_plan(title="Sky",brief="Sitio educativo",provider="anthropic",allow_cloud=False)
    assert called==[]


def test_ollama_default_never_silently_uses_cloud(monkeypatch):
    captured={}
    def choose(p,**kw):
        captured["provider"]=p
        return "ollama","local-mock"
    monkeypatch.setattr(providers,"choose_provider",choose)
    monkeypatch.setattr(providers,"reply",lambda *a,**kw:json.dumps(valid_design_plan()))
    output=ai.compose_plan(title="Demo",brief="Diseño original para turismo",
                           provider="auto",allow_cloud=False)
    assert captured["provider"]=="ollama"
    assert output["cloud_used"] is False
    assert output["code_executed"] is False
    assert output["llm_generated"] is True


def test_existing_cloud_gateway_only_gets_user_brief(monkeypatch):
    monkeypatch.setattr(providers,"choose_provider",lambda *a,**kw:("openai","configured-model"))
    captured={}
    def reply(messages,**kwargs):
        captured.update({"messages":messages,**kwargs})
        return json.dumps(valid_design_plan())
    monkeypatch.setattr(providers,"reply",reply)
    result=ai.compose_plan(title="Ruta de Luz",brief="Turismo accesible",provider="openai",allow_cloud=True)
    assert result["provider_used"]=="openai" and result["cloud_used"] is True
    assert captured["provider"]=="openai"
    assert captured["messages"][0]["role"]=="system"
    assert captured["messages"][1]["role"]=="user"
    assert "Turismo accesible" in captured["messages"][1]["content"]
    assert "OPENAI_API_KEY" not in captured["messages"][1]["content"]


def test_downloaded_ai_zip_contains_same_validated_plan():
    data=studio.create_design("Turismo SKY","Rutas y montañas",design_plan=valid_design_plan())
    bundle=studio.design_archive(data)
    with zipfile.ZipFile(io.BytesIO(bundle)) as z:
        cfg=json.loads(z.read("sky-design-react/src/config.json"))
        assert cfg["subtitle"]==valid_design_plan()["subtitle"]
        assert "sky-design-react/sky-preparar.ps1" in z.namelist()


def test_authorized_owner_ai_api_and_download(monkeypatch):
    monkeypatch.setenv("SKY_API_KEY","sky-design-real-ai-gateway-test-token")
    from metaverse.api import app, api_token
    monkeypatch.setattr(providers,"choose_provider",lambda *a,**kw:("ollama","local-test"))
    monkeypatch.setattr(providers,"reply",lambda *a,**kw:json.dumps(valid_design_plan()))
    with TestClient(app) as client:
        h={"X-SKY-KEY":api_token()}
        assert client.post("/api/developer/design/ai/create",json={
            "title":"SKY", "brief":"Turismo", "approved":True}).status_code in (401,403)
        assert client.post("/api/developer/design/ai/create",headers=h,json={
            "title":"SKY", "brief":"Turismo"}).status_code==403
        response=client.post("/api/developer/design/ai/create",headers=h,json={
            "title":"SKY Turismo", "brief":"Turismo de naturaleza",
            "platform":"react", "provider":"ollama", "approved":True})
        assert response.status_code==200,response.text
        result=response.json()
        assert result["ai_generation_verified"] is True
        assert result["cloud_used"] is False
        assert result["design_plan"]["subtitle"]==valid_design_plan()["subtitle"]
        z=client.post("/api/developer/design/download",headers=h,json={
            "title":"SKY Turismo", "brief":"Turismo de naturaleza", "platform":"react",
            "design_plan":result["design_plan"]})
        assert z.status_code==200
        with zipfile.ZipFile(io.BytesIO(z.content)) as archive:
            spec=json.loads(archive.read("sky-design-react/src/config.json"))
            assert spec["subtitle"]==result["design_plan"]["subtitle"]


def test_install_scripts_have_explicit_approval_and_project_scope():
    files=studio.create_design("Diseño","Academia tecnológica",platform="react")["files"]
    ps=files["sky-preparar.ps1"]
    assert "Read-Host" in ps and 'if ($approval -cne "INSTALAR")' in ps
    assert "npm install --ignore-scripts" in ps
    assert "npm run build" in ps
    assert "npm install -g" not in ps
    flutter=studio.create_design("App","Cursos",platform="flutter")["files"]["sky-preparar.ps1"]
    assert "flutter pub get" in flutter
    assert "flutter analyze" in flutter
    assert "flutter test" in flutter
    assert "Read-Host" in flutter
