"""SKY vNext integration gates. No cloud credentials or paid side effects in CI."""
from pathlib import Path
import json
import subprocess
import pytest

from neural_core import sky_skillpack as pack
from neural_core import sky_skillpack_extended as ext
from neural_core import sky_skills_audit as skills_audit
from neural_core import sky_operational_quality as quality


def test_all_29_have_actual_python_adapter_and_remain_unverified():
    report=pack.catalogue()
    assert report["total_requested_here"]==29
    assert report["adapter_count"]==29
    assert all(s["adapter"] is not None for s in report["skills"])
    assert all(s["live_verified"] is False for s in report["skills"])
    assert skills_audit.TARGET==78


def test_google_workspace_uses_official_endpoints_without_fake_oauth(monkeypatch):
    monkeypatch.delenv("SKY_GOOGLE_OAUTH_ACCESS_TOKEN",raising=False)
    with pytest.raises(pack.SkillUnavailable):
        pack.execute("google-workspace-connector",{"service":"drive"})
    monkeypatch.setenv("SKY_GOOGLE_OAUTH_ACCESS_TOKEN","test-no-real-token")
    recorded=[]
    monkeypatch.setattr(ext,"_http",lambda method,url,token,**kw:
                        recorded.append((method,url,token)) or {"ok":True})
    for service in ("drive","gmail","calendar"):
        assert pack.execute("google-workspace-connector",{"service":service})["ok"]
    assert len(recorded)==3
    assert all(x[0]=="GET" and x[1].startswith("https://") for x in recorded)
    with pytest.raises(pack.SkillInvalid):
        pack.execute("google-workspace-connector",{"service":"random"})


def test_slack_reads_authorized_channels_and_requires_explicit_post_approval(monkeypatch):
    monkeypatch.setenv("SKY_SLACK_BOT_TOKEN","not-real-test-token")
    monkeypatch.setenv("SKY_SLACK_ALLOWED_CHANNELS","C0123456789")
    recorded=[]
    monkeypatch.setattr(ext,"_http",lambda method,url,token,**kw:
                        recorded.append((method,url,kw)) or {"ok":True})
    assert pack.execute("slack-communicator",{"operation":"history","channel":"C0123456789"})["ok"]
    with pytest.raises(pack.SkillInvalid):
        pack.execute("slack-communicator",{"operation":"history","channel":"C9999999999"})
    with pytest.raises(pack.SkillInvalid):
        pack.execute("slack-communicator",{"operation":"send","channel":"C0123456789","text":"Hola"})
    r=pack.execute("slack-communicator",{"operation":"send","channel":"C0123456789",
                                              "text":"Hola","approved":True})
    assert r["ok"] and recorded[-1][0]=="POST"
    assert recorded[-1][2]["payload"]["text"]=="Hola"


def test_supermemory_reuses_persistent_manager_with_owner_control(tmp_path,monkeypatch):
    from neural_core import smart_memory
    monkeypatch.setattr(smart_memory,"_default_memory_manager",
                        smart_memory.SmartMemoryManager(tmp_path/"memory.json"))
    body={"operation":"set","category":"proyecto","key":"ruta","value":"Nicaragua"}
    with pytest.raises(pack.SkillInvalid):
        pack.execute("supermemory",body)
    body["approved"]=True
    assert pack.execute("supermemory",body)["ok"]
    assert pack.execute("supermemory",{"operation":"get","category":"proyecto","key":"ruta"})["item"]=="Nicaragua"
    assert (tmp_path/"memory.json").exists()
    with pytest.raises(pack.SkillInvalid):
        pack.execute("supermemory",{"operation":"set","category":"proyecto","key":"bad",
                                   "value":"password: ABC","approved":True})
    assert pack.execute("supermemory",{"operation":"delete","category":"proyecto",
                                       "key":"ruta","approved":True})["deleted"]


def test_aws_does_not_deploy_unapproved_or_unallowlisted_stacks(tmp_path,monkeypatch):
    monkeypatch.setattr(ext,"configured",lambda name:True)
    monkeypatch.setattr(ext,"_ROOT",tmp_path)
    folder=tmp_path/"cloud_templates"
    folder.mkdir()
    (folder/"example.yaml").write_text("AWSTemplateFormatVersion: '2010-09-09'",encoding="utf-8")
    with pytest.raises(pack.SkillInvalid):
        pack.execute("aws-workflow-deploy",{"operation":"deploy","template":"example.yaml",
                                          "stack":"SkyTest"})
    monkeypatch.setenv("SKY_SKILL_ALLOW_AWS_DEPLOY","1")
    with pytest.raises(pack.SkillInvalid):
        pack.execute("aws-workflow-deploy",{"operation":"deploy","template":"example.yaml",
                                          "stack":"SkyTest","approved":True})
    called=[]
    def fake_run(args,**kwargs):
        called.append(args)
        return subprocess.CompletedProcess(args,0,'{"Parameters":[]}',"")
    monkeypatch.setattr(ext.subprocess,"run",fake_run)
    assert pack.execute("aws-workflow-deploy",{"operation":"validate-template",
                                          "template":"example.yaml"})["ok"]
    assert called[-1][1:3]==["cloudformation","validate-template"]
    with pytest.raises(pack.SkillInvalid):
        pack.execute("aws-workflow-deploy",{"operation":"validate-template","template":"../invalid.yaml"})


def test_d3_and_remotion_are_real_local_projects_not_pretend_installations(monkeypatch):
    root=Path(__file__).resolve().parents[1]
    assert (root/"sky_d3"/"render.mjs").is_file()
    assert "d3" in json.loads((root/"sky_d3"/"package.json").read_text())["dependencies"]
    assert (root/"sky_remotion"/"src"/"root.tsx").is_file()
    monkeypatch.setattr(ext,"configured",lambda name:False)
    with pytest.raises(pack.SkillUnavailable):
        pack.execute("remotion",{"composition":"SkyIntro","approved":True})
    with pytest.raises(pack.SkillUnavailable):
        pack.execute("claude-d3js-skill",{"values":[1,2,3]})


def test_loki_tasks_execute_only_bounded_deterministic_skills():
    with pytest.raises(pack.SkillInvalid):
        pack.execute("loki-mode",{"operation":"submit","skill":"docker-manager",
                                 "approved":True,"parameters":{}})
    r=pack.execute("loki-mode",{"operation":"submit","skill":"algorithmic-art",
                          "approved":True,"parameters":{"lines":8}})
    job=ext._POLL[r["job_id"]]
    result=job["future"].result(timeout=5)
    assert result["mime"]=="image/svg+xml"
    polled=pack.execute("loki-mode",{"operation":"poll","job_id":r["job_id"]})
    assert polled["state"]=="COMPLETED"


def test_audit_refuses_to_certify_unverified_78():
    a=skills_audit.audit()
    assert a["target"]==78
    assert a["count_by_independent_catalogue"]["external_adapters"]==29
    assert a["manifest_of_78_distinct_ids_present"] is False
    assert a["verified_external_live"]==0
    assert len(a["groups"]["professional_guides"])>=10


def test_quality_report_reuses_action_receipts_and_never_fabricates_100(monkeypatch):
    monkeypatch.setattr(quality.sky_metricas,"resumen",lambda p:{
        "api":{"peticiones":5,"p95_ms":90},"voz":{"interrupciones":1},
        "modelo":{"cost_usd":None,"cost_estimated":True},"asistente":{"turnos":3}})
    monkeypatch.setattr(quality.verificador_acciones,"get_recent_actions",lambda n:[
        {"command_id":"cmd_a","status":"VERIFIED","execution_time_ms":20},
        {"command_id":"cmd_b","status":"DISPATCHED","execution_time_ms":30},
        {"command_id":"cmd_c","status":"FAILED","execution_time_ms":35},
    ])
    r=quality.report()
    assert r["actions_verified"]==1 and r["actions_dispatched_unverified"]==1
    assert r["observed_verified_fraction_pct"]==33.3
    assert r["global_100_score_certified"] is False
    assert r["cost_usd_reported"] is None


def test_live_research_parses_real_scholarly_metadata_without_invention(monkeypatch):
    from neural_core import sky_scholarly
    captured=[]
    def fake_get(url):
        captured.append(url)
        return {"results":[{
            "title":"Documento de prueba publicado",
            "doi":"https://doi.org/10.1234/test",
            "publication_year":2025,
            "authorships":[{"author":{"display_name":"Autora de prueba"}}],
            "primary_location":{"source":{"display_name":"Revista de prueba"}},
        }]}
    monkeypatch.setattr(sky_scholarly,"_get_json",fake_get)
    data=sky_scholarly.search_papers("Educación interactiva",provider="openalex",limit=4)
    assert captured and captured[0].startswith("https://api.openalex.org/works?")
    assert data["live_lookup"] and data["full_text_read"] is False
    assert data["items"][0]["doi"]=="10.1234/test"
    assert data["items"][0]["peer_review_verified"] is False
    from pathlib import Path
    api=Path("metaverse/academy_api.py").read_text(encoding="utf-8")
    assert '"/research/live-papers"' in api
    assert '"metadata_only":True' in api


def test_aula_does_not_grade_answers_and_uses_supplied_reference():
    from neural_core import sky_aula
    session=sky_aula.start("electricidad","tecnico",reference_text="La corriente eléctrica se mide en amperios.")
    feedback=sky_aula.formative_response(session["lesson_id"],"Se mide en amperios.")
    assert feedback["feedback_reference_available"] is True
    assert feedback["correctness_graded"] is False
    assert "corriente eléctrica" in feedback["voice_ready_text"]
    sky_aula.end(session["lesson_id"])


def test_voice_hud_and_api_have_context_barge_in_and_owner_protection():
    hud=(Path("metaverse/static")/"hud.js").read_text(encoding="utf-8")
    assert "Barge-in:" in hud and "S.conv" in hud
    assert "historial: S.historial.slice(-12)" in hud
    api=Path("metaverse/api.py").read_text(encoding="utf-8")
    assert "def sky_full_skills_audit" in api and "Depends(require_key)" in api
    assert "exigir_pin(request, \"una acción externa irreversible de SKY\")" in api
