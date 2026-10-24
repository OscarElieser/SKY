"""SKY Aula + Innovation Lab: educational safety, evidence integrity and Office files."""
from __future__ import annotations

import io
import json
import zipfile

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

KEY="sky-academy-owner-secret-regression-key-2026"


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv("SKY_API_KEY",KEY)
    monkeypatch.setenv("SKY_NEURAL_MEMORY_KEY",Fernet.generate_key().decode())
    monkeypatch.setenv("SKY_KNOWLEDGE_DB",str(tmp_path/"private_knowledge.sqlite3"))
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED","0")
    from neural_core import sky_aula
    with sky_aula._LOCK:
        sky_aula._SESSIONS.clear()
    from metaverse.api import app
    with TestClient(app) as api:
        yield api


def auth():
    return {"X-SKY-KEY":KEY}


def lesson(**extra):
    data={
        "topic":"Números naturales: antecesor y sucesor",
        "level":"inicial",
        "grade":"tercer nivel",
        "duration_minutes":45,
        "learning_goal":"Establece relaciones entre números naturales hasta 20",
    }
    data.update(extra)
    return data


def project(**extra):
    data={
        "name":"Solución de movilidad comunitaria",
        "challenge":"Las personas de comunidades rurales enfrentan dificultades de transporte para llegar a centros educativos",
        "category":"transporte",
        "event":"hackathon_nicaragua",
        "solution":"Prototipo de información colaborativa de horarios y rutas",
        "pitch_minutes":3,
    }
    data.update(extra)
    return data


def test_requires_owner_for_every_academy_endpoint(client):
    for endpoint in (
        "/api/sky/academy/capabilities",
        "/api/sky/academy/education/levels",
        "/api/sky/academy/research/sources",
        "/api/sky/academy/innovation/capabilities",
    ):
        assert client.get(endpoint).status_code==401
        assert client.get(endpoint,headers=auth()).status_code==200
    assert client.post("/api/sky/academy/education/lesson",json=lesson()).status_code==401
    assert client.post("/api/sky/academy/innovation/project",json=project()).status_code==401


@pytest.mark.parametrize("level",[
    "inicial","primaria","secundaria","tecnico","universitario","maestria","doctorado"
])
def test_all_levels_generate_seven_coherent_age_appropriate_stages(level):
    from neural_core import sky_aula
    p=sky_aula.lesson("Comprensión de lectura",level,duration_minutes=45)
    assert p["level"]==level
    assert len(p["stages"])==7
    assert sum(st["minutes"] for st in p["stages"])==45
    assert p["goal_verified_against_curriculum"] is False
    assert p["lesson_ready_to_teach_verified_facts"] is False
    assert p["child_data_collected"] is False
    if level=="inicial":
        assert p["official_source_reference"]["status"]=="reference_only_not_fetched"
        assert "MEIDI" in p["level_label"]
    if level=="doctorado":
        assert "investigación" in p["level_label"].lower()


def test_lessons_without_sources_do_not_fabricate_explanation():
    from neural_core import sky_aula
    p=sky_aula.lesson("Geometría tridimensional","universitario")
    explanation=sky_aula.stage_output(p,2)
    assert "necesito el texto" in explanation["voice_ready_text"]
    assert not explanation["knowledge_from_verified_source"]
    assert explanation["speech_audio_generated"] is False
    assert explanation["may_speak_using_browser_tts"] is True
    p2=sky_aula.lesson("Geometría tridimensional","universitario",
                       reference_text="El material de estudio describe cubos y prismas.")
    step=sky_aula.stage_output({**p2,"_source_text":"El material de estudio describe cubos y prismas."},2)
    assert "cubos" in step["voice_ready_text"]
    assert "todavía necesita verificarse" in step["voice_ready_text"]


def test_sessions_step_by_step_in_memory_and_natural_voice(client):
    res=client.post("/api/sky/academy/education/sessions",headers=auth(),json=lesson())
    assert res.status_code==201,res.text
    data=res.json()
    ident=data["lesson_id"]
    assert ident.startswith("lesson_")
    assert data["step"]["stage_number"]==1
    assert data["privacy"].startswith("in_memory")
    numbers=[1]
    for _ in range(6):
        nxt=client.post("/api/sky/academy/education/sessions/"+ident+"/next",
                        headers=auth(),json={})
        assert nxt.status_code==200,nxt.text
        numbers.append(nxt.json()["step"]["stage_number"])
    assert numbers==[1,2,3,4,5,6,7]
    final=client.post("/api/sky/academy/education/sessions/"+ident+"/next",
                      headers=auth(),json={}).json()
    assert final["status"]=="completed"
    assert client.delete("/api/sky/academy/education/sessions/"+ident,
                         headers=auth()).json()["closed"]
    assert client.get("/api/sky/academy/education/sessions/"+ident,
                      headers=auth()).status_code==404

    chat=client.post("/api/asistente/mensaje",headers=auth(),json={
        "texto":"SKY, impartí una clase de la cultura nicaragüense para primaria",
        "modo":"chat",
    })
    assert chat.status_code==200,chat.text
    response=chat.json()
    assert response["atendido_por"]=="SKY"
    assert response["proveedor"]=="sky-aula"
    assert response["lesson_id"].startswith("lesson_")
    step=client.post("/api/asistente/stream",headers=auth(),json={
        "texto":"SKY, siguiente paso de la clase","modo":"voz",
        "lesson_id":response["lesson_id"],
    })
    assert step.status_code==200,step.text
    last=json.loads(step.text.strip().splitlines()[-1])["final"]
    assert last["atendido_por"]=="SKY"
    assert last["academy"]["step"]["stage_number"]==2
    assert last["lesson_id"]==response["lesson_id"]


def test_hackathon_project_never_fabricates_canvas_evidence_or_budget(client):
    result=client.post("/api/sky/academy/innovation/project",
                       headers=auth(),json=project())
    assert result.status_code==200,result.text
    data=result.json()
    assert len(data["canvas"])==9
    assert data["competition"]=="Hackathon Nicaragua"
    assert data["pitch_minutes"]==3
    assert sum(x["seconds"] for x in data["pitch_sections"])==180
    assert data["pitch_duration_tested"] is False
    assert data["canvas_validated"] is False
    assert data["smart_goals_verified"] is False
    assert data["impact_scored"] is False
    assert data["viability_scored"] is False
    assert data["research_completed"] is False
    assert data["data_invented"] is False
    assert "pendiente" in data["document_markdown"].lower()
    assert "Matriz" in data["document_markdown"]
    assert "Canvas" in data["document_markdown"]
    assert "No se realizó investigación web" in data["document_markdown"]


@pytest.mark.parametrize("event",[
    "rally_nacional","rally_latinoamericano","hackathon_nicaragua",
    "hackathon","innovatec","emprendimiento","investigacion","general"
])
def test_innovation_events_registered(event):
    from neural_core.sky_innovation_lab import build_project
    data=project(event=event)
    p=build_project(**data)
    assert p["competition"] and p["source_verification_pending"]


def test_medical_innovation_is_a_proposal_not_diagnosis():
    from neural_core import sky_innovation_lab,sky_evidence_lab
    p=sky_innovation_lab.build_project(
        name="Educación sanitaria comunitaria",
        challenge="Faltan materiales locales validados sobre prevención sanitaria en una comunidad",
        category="medicina",
        event="rally_latinoamericano",
        evidence_text="Afirmación de un vecino todavía sin corroborar",
    )
    assert not p["research_completed"] and not p["canvas_validated"]
    assert "no verificada" in p["document_markdown"].lower()
    assert not sky_evidence_lab.catalogue("medicina")["medical_diagnostic_authority"]


def test_research_registry_never_pretends_to_access_web(client):
    r=client.post("/api/sky/academy/research/brief",headers=auth(),json={
        "topic":"Factores que afectan el aprendizaje inicial en Nicaragua",
        "domain":"educacion",
    })
    assert r.status_code==200,r.text
    data=r.json()
    assert not data["research_completed"]
    assert not data["claim_externally_verified"]
    assert data["review_required"]
    assert all(item["status"]=="reference_only_not_fetched"
               for item in data["possible_official_sources"])
    assert any("verificación cruzada" in x for x in data["missing_evidence"])


def test_claims_with_citations_are_not_automatically_verified():
    from neural_core.sky_evidence_lab import check_claims
    result=check_claims([{
        "statement":"Según una fuente, la población aumentó 3%.",
        "citation":"https://example.org/page"
    }])
    assert not result["all_facts_verified"]
    assert result["claims"][0]["citation_provided"]
    assert result["claims"][0]["status"]=="requires_external_verification"


@pytest.mark.parametrize("kind,mime",[
    ("docx","application/vnd.openxmlformats"),
    ("pdf","application/pdf"),
    ("pptx","application/vnd.openxmlformats"),
    ("md","text/markdown"),
])
def test_real_professional_project_exports_marked_draft(client,kind,mime):
    res=client.post("/api/sky/academy/innovation/project/document",
                    headers=auth(),json={**project(),"kind":kind})
    assert res.status_code==200,res.text[:200]
    assert mime in res.headers["content-type"]
    assert res.headers["X-SKY-Research-Status"]=="draft-not-externally-verified"
    assert "attachment" in res.headers["content-disposition"]
    if kind=="pdf": assert res.content.startswith(b"%PDF")
    elif kind in ("docx","pptx"):
        assert zipfile.is_zipfile(io.BytesIO(res.content))
    else: assert "Canvas" in res.text


def test_real_lesson_export_and_invalid_levels(client):
    res=client.post("/api/sky/academy/education/lesson/document",
                    headers=auth(),json={**lesson(),"kind":"docx"})
    assert res.status_code==200,res.text[:200]
    assert zipfile.is_zipfile(io.BytesIO(res.content))
    invalid=client.post("/api/sky/academy/education/lesson",
                        headers=auth(),json=lesson(level="inventado"))
    assert invalid.status_code==422
    invalid_project=client.post("/api/sky/academy/innovation/project",
                        headers=auth(),json=project(event="fake-competition"))
    assert invalid_project.status_code==422



def test_official_research_can_fetch_only_whitelisted_sources_and_retain_timestamp(client,monkeypatch):
    import urllib.request
    from email.message import Message

    hits=[]
    class WebResponse:
        status=200
        def __init__(self):
            self.headers=Message()
            self.headers["Content-Type"]="text/html; charset=utf-8"
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self,limit=250001):
            assert limit<=250001
            return b"<html><body><h1>Educacion inicial</h1><p>El aprendizaje promueve experiencias.</p></body></html>"

    class FakeOpener:
        def open(self,request,timeout=8):
            hits.append((request.full_url,timeout))
            return WebResponse()
    monkeypatch.setattr(urllib.request,"build_opener",lambda *handlers: FakeOpener())
    req={
        "topic":"aprendizaje en educación inicial",
        "source_ids":["mined_meidi"],
    }
    actual=client.post("/api/sky/academy/research/official-sources",
                       headers=auth(),json=req)
    assert actual.status_code==200,actual.text
    value=actual.json()
    assert value["pages_retrieved"]==1
    assert not value["all_claims_verified"]
    assert not value["research_completed"]
    assert len(hits)==1 and "mined.gob.ni" in hits[0][0]
    source=value["sources"][0]
    assert source["status"]=="official_page_retrieved_not_independently_verified"
    assert source["retrieved_at"]
    assert source["retrieved_sha256"]
    assert source["topic_match"]
    assert source["site_publication_date_verified"] is False
    assert source["text_instructions_executed"] is False


def test_unapproved_official_source_is_rejected_before_any_network(client,monkeypatch):
    import urllib.request
    def unreachable(*args,**kwargs):
        raise AssertionError("Network must not be touched for invalid source IDs")
    monkeypatch.setattr(urllib.request,"build_opener",unreachable)
    response=client.post("/api/sky/academy/research/official-sources",
                        headers=auth(),json={
                            "topic":"investigación sobre transporte público",
                            "source_ids":["https://evil.example/"],
                        })
    assert response.status_code==422


def test_unavailable_official_source_never_yields_fake_evidence(client,monkeypatch):
    import urllib.request
    class Fail:
        def open(self,req,timeout):
            raise OSError("Sin acceso")
    monkeypatch.setattr(urllib.request,"build_opener",lambda *a: Fail())
    result=client.post("/api/sky/academy/research/official-sources",
                       headers=auth(),json={
                           "topic":"innovación educación nicaragüense",
                           "source_ids":["inatec_portal"]
                       })
    assert result.status_code==200,result.text
    assert result.json()["pages_retrieved"]==0
    assert result.json()["sources"][0]["status"]=="unavailable_or_unsupported"
    assert result.json()["sources"][0]["topic_excerpts"]==[]


@pytest.mark.parametrize("level,voice_command",[
    ("tecnico","SKY, impartí una clase de seguridad ocupacional para nivel técnico"),
    ("universitario","SKY, impartí una clase de probabilidad para universitario"),
    ("doctorado","SKY, impartí una clase de metodología para doctorado"),
])
def test_owner_can_start_other_levels_by_voice(client,level,voice_command):
    response=client.post("/api/asistente/mensaje",headers=auth(),
                         json={"texto":voice_command,"modo":"voz"})
    assert response.status_code==200,response.text
    data=response.json()
    assert data["proveedor"]=="sky-aula"
    assert data["academy"]["plan"]["level"]==level
    assert data["lesson_id"].startswith("lesson_")



def test_interactive_lesson_response_is_formative_without_recording_student_text(client):
    from neural_core import sky_aula
    created=client.post("/api/sky/academy/education/sessions",headers=auth(),
                        json=lesson(level="secundaria"))
    assert created.status_code==201,created.text
    ident=created.json()["lesson_id"]
    answer="Creo que la respuesta depende del orden de los números en la secuencia."
    reply=client.post("/api/sky/academy/education/sessions/"+ident+"/respond",
                      headers=auth(),json={"answer":answer})
    assert reply.status_code==200,reply.text
    data=reply.json()
    assert data["central_agent"]=="SKY"
    assert not data["correctness_graded"]
    assert not data["response_recorded"]
    assert not data["student_personal_data_saved"]
    assert "comprobarla" in data["voice_ready_text"]
    assert answer not in repr(sky_aula._SESSIONS[ident])
    nxt=client.get("/api/sky/academy/education/sessions/"+ident,
                   headers=auth())
    assert nxt.json()["step"]["stage_number"]==1
