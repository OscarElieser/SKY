"""SKY Extension Hub and verified procedural learning safety tests (no hardware)."""
from pathlib import Path
import json
import pytest

from neural_core import sky_extension_hub as hub
from neural_core import sky_experience_learning as learning
from neural_core import sky_execution_cycle as cycles


@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(learning,"_STORE",tmp_path/"procedures.json")
    cycles._PLANS.clear()
    monkeypatch.setattr(cycles.caps,"parada_activa",lambda:False)
    yield
    cycles._PLANS.clear()


def _cycle(*actions):
    steps=[{"action":a,"params":p} for a,p in actions]
    return cycles.create(steps)


def _verified_launch(app="word",command_id="cmd_1234567890_abcd"):
    plan=_cycle(("launch_app",{"app":app}))
    outcome=cycles.execute_next(plan["id"],lambda a,p,d:{
        "ok":True,"status":"VERIFIED","command_id":command_id},approved=True)
    assert outcome["state"]=="VERIFIED"
    return plan["id"]


def test_all_12_public_repository_references_are_descriptive_not_executable():
    result=hub.catalogue()
    ids={x["id"] for x in result["extensions"]}
    assert {"openclaw","hermes-agent","opencode","n8n","firecrawl","ollama",
            "agent-skills","dify","open-webui","langflow","claude-code","langchain"}<=ids
    assert result["primary_core"]=="SKY CORE"
    assert not result["auto_install"] and not result["auto_execute"]
    assert all(x["external_code_execution_allowed"] is False for x in result["extensions"])
    assert all(x["live_verified"] is False for x in result["extensions"])
    assert hub.extension("openclaw")["state"]=="review_only"
    assert hub.extension("ollama")["mode"]=="native"
    assert hub.catalogue("investigación")["total"]>0
    with pytest.raises(ValueError):hub.catalogue("x"*41)


def test_unverified_sent_or_failed_cycle_cannot_be_learned():
    p=_cycle(("launch_app",{"app":"word"}))
    with pytest.raises(learning.LearningInvalid):
        learning.capture_verified(p["id"],"Abrir Word",approved=True)
    cycles.execute_next(p["id"],lambda a,b,c:{
        "ok":True,"status":"RUNNING","command_id":"cmd_1234567890_abcd"},approved=True)
    with pytest.raises(learning.LearningInvalid):
        learning.capture_verified(p["id"],"Abrir Word",approved=True)
    assert learning.list_procedures()["total"]==0


def test_secret_file_text_url_and_media_actions_are_never_captured():
    for action,params in [("type_text",{"text":"password=123"}),
                          ("open_url",{"url":"https://example.org/private?token=123"}),
                          ("media_key",{"key":"play_pause"})]:
        plan=_cycle((action,params))
        cycles.execute_next(plan["id"],lambda a,b,c:{
            "ok":True,"status":"VERIFIED","command_id":"cmd_abcdefgh1234"},approved=True)
        with pytest.raises(learning.LearningInvalid):
            learning.capture_verified(plan["id"],"Acción privada",approved=True)
    assert learning.list_procedures()["total"]==0


def test_only_real_predefined_app_ids_allowed_and_evidence_required():
    p=_cycle(("launch_app",{"app":"untrusted_app"}))
    cycles.execute_next(p["id"],lambda a,b,c:{"ok":True,"status":"VERIFIED",
                                                "command_id":"cmd_anything"},approved=True)
    with pytest.raises(learning.LearningInvalid):
        learning.capture_verified(p["id"],"Abrir aplicacion",approved=True)
    q=_cycle(("launch_app",{"app":"word"}))
    cycles.execute_next(q["id"],lambda a,b,c:{"ok":True,"status":"VERIFIED"},approved=True)
    with pytest.raises(learning.LearningInvalid):
        learning.capture_verified(q["id"],"Abrir sin evidencia",approved=True)


def test_manual_capture_persists_safe_steps_and_replay_does_not_execute(monkeypatch):
    cid=_verified_launch()
    with pytest.raises(learning.LearningInvalid):
        learning.capture_verified(cid,"Abrir Word",approved=False)
    result=learning.capture_verified(cid,"Abrir Word",approved=True)
    assert result["verified"] and not result["auto_executed"]
    assert learning.list_procedures()["total"]==1
    raw=learning._STORE.read_text(encoding="utf-8")
    assert "launch_app" in raw and "word" in raw
    assert "command_id" not in raw and "token" not in raw
    # Loading an approved recipe creates a fresh READY plan; action still needs approval.
    replay=learning.plan_replay("abrir-word")
    assert replay["state"]=="READY" and replay["verified"]==0
    assert replay["steps"][0]["state"]=="READY"
    assert replay["steps"][0]["action"]=="launch_app"
    with pytest.raises(cycles.CycleInvalid):
        cycles.execute_next(replay["id"],lambda a,b,c:pytest.fail("unauthorized"),
                            approved=False)
    assert learning.interpretar("SKY, repetí procedimiento abrir word")["tipo"]=="ciclo"


def test_repeated_verification_updates_evidence_but_not_unapproved_recipe():
    x=learning.capture_verified(_verified_launch(),"Abrir Word",approved=True)
    y=learning.capture_verified(_verified_launch(),"Abrir Word",approved=True)
    assert x["evidence_count"]==1 and y["evidence_count"]==2
    with pytest.raises(learning.LearningInvalid):
        learning.capture_verified(_verified_launch("excel"),"Abrir Word",approved=True)
    assert learning.list_procedures()["total"]==1


def test_tampered_memory_is_rejected_before_replay():
    learning.capture_verified(_verified_launch(),"Abrir Word",approved=True)
    p=learning._STORE
    doc=json.loads(p.read_text(encoding="utf-8"))
    doc["procedures"]["abrir-word"]["steps"]=[{"action":"type_text",
                  "params":{"text":"sensitive"},"label":"private"}]
    p.write_text(json.dumps(doc),encoding="utf-8")
    with pytest.raises(learning.LearningInvalid):
        learning.plan_replay("abrir-word")
    assert learning.list_procedures()["total"]==0


def test_emergency_stop_blocks_procedure_replay(monkeypatch):
    learning.capture_verified(_verified_launch(),"Abrir Word",approved=True)
    monkeypatch.setattr(cycles.caps,"parada_activa",lambda:{"active":True})
    with pytest.raises(learning.LearningUnavailable):
        learning.plan_replay("abrir-word")


def test_procedure_delete_requires_owner_confirmation_and_is_reversible():
    learning.capture_verified(_verified_launch(),"Abrir Word",approved=True)
    with pytest.raises(learning.LearningInvalid):
        learning.delete("abrir-word",approved=False)
    assert learning.delete("abrir-word",approved=True)
    assert learning.list_procedures()["total"]==0


def test_unsafe_learning_never_registers_as_executable_skill():
    from neural_core import sky_skill_builder, sky_skills
    learning.capture_verified(_verified_launch(),"Abrir Word",approved=True)
    assert "export_verified_replay" in Path("neural_core/sky_execution_cycle.py").read_text()
    assert not sky_skill_builder.base().joinpath("abrir-word").exists()
    assert all(s["id"]!="abrir-word" for s in sky_skills.listar())


def test_authenticated_api_and_voice_text_routes_preserve_core():
    code=Path("metaverse/api.py").read_text(encoding="utf-8")
    assert '"/api/sky/extensions"' in code
    assert '"/api/sky/learning/procedures"' in code
    assert "exigir_pin(request,\"guardar un procedimiento verificado de SKY\")" in code
    voice=Path("metaverse/asistente_api.py").read_text(encoding="utf-8")
    assert voice.count("learning.interpretar(body.texto")>=2
    hud=Path("metaverse/static/hud.js").read_text(encoding="utf-8")
    assert "Recordar procedimiento" in hud and "SKY Extension Hub" in hud
    assert "requires_confirmation_each_step" in code


def test_extension_router_never_executes_unapproved_and_excludes_sidecars(monkeypatch):
    monkeypatch.delenv("SKY_LOCAL_ONLY",raising=False)
    called=[]
    from neural_core import sky_research_connectors as research
    monkeypatch.setattr(research,"semantic_scholar",lambda query,limit=5:
                        called.append((query,limit)) or {"ok":True,"items":[]})
    with pytest.raises(hub.ExtensionInvalid):
        hub.invoke("semantic-scholar",action="search",payload={"query":"enseñanza"},approved=False)
    with pytest.raises(hub.ExtensionInvalid):
        hub.invoke("openclaw",action="search",payload={},approved=True)
    with pytest.raises(hub.ExtensionInvalid):
        hub.invoke("n8n",action="dispatch",payload={},approved=True)
    assert called==[]
    assert hub.invoke("semantic-scholar",action="search",
                      payload={"query":"enseñanza","limit":3},approved=True)["ok"] is True
    assert called==[("enseñanza",3)]
    assert len(hub.callable_tools())==9


def test_hub_honors_local_mode_even_when_user_approved(monkeypatch):
    monkeypatch.setenv("SKY_LOCAL_ONLY","1")
    from neural_core import sky_skillpack
    called=[]
    monkeypatch.setattr(sky_skillpack,"execute",lambda *a,**k:called.append(1))
    with pytest.raises(hub.ExtensionInvalid):
        hub.invoke("firecrawl",action="scrape",payload={"url":"https://example.com"},approved=True)
    assert called==[]


def test_hub_requires_exact_actions_and_calls_owner_selected_local_model(monkeypatch):
    monkeypatch.setenv("SKY_LOCAL_ONLY","1")
    from neural_core import providers
    seen=[]
    monkeypatch.setattr(providers,"reply",lambda messages,provider,max_output_tokens:
                        seen.append(provider) or "Hola desde SKY local")
    with pytest.raises(hub.ExtensionInvalid):
        hub.invoke("ollama",action="install",payload={"question":"hola"},approved=True)
    response=hub.invoke("ollama",action="chat",payload={"question":"Hola"},approved=True)
    assert response["answer"]=="Hola desde SKY local" and seen==["ollama"]
    assert response["not_a_verified_external_fact"] is True


def test_api_extension_dispatch_explicit_approval_and_pin():
    api=Path("metaverse/api.py").read_text(encoding="utf-8")
    assert '"/api/sky/extensions/{extension_id}/invoke"' in api
    assert "exigir_pin(request,\"usar un proveedor externo con posible consumo\")" in api
    assert '"/api/sky/extensions/actions"' in api
