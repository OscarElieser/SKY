"""SKY Aula multimodal/3D/evaluation regression suite, with no live student data.

Live YouTube, browser TTS and WebGL require physical browser/device checks.
"""
import json
from pathlib import Path
import pytest

from neural_core import sky_aula, sky_aula_multimedia as media
from neural_core import sky_aula_assessment as assess


def test_aula_is_extended_in_place_with_prior_seven_stages():
    x=sky_aula.lesson("partes de una computadora","tecnico",reference_text="CPU y memoria.")
    assert len(x["stages"])==7
    assert x["multimedia"]["3d_scene"]["available"] is True
    assert x["multimedia"]["3d_scene"]["component_count"]==8
    assert x["assessment_available"]==["diagnostica","formativa","sumativa"]
    assert x["lesson_ready_to_teach_verified_facts"] is False
    session=sky_aula.start("partes de una computadora","tecnico")
    for n in range(7):
        d=sky_aula.current(session["lesson_id"])
        assert d["step"]["evaluation_dimensions"]==["conocer","hacer","ser"]
        if n==3:
            assert d["step"]["visual_3d"]["available"] is True
            assert d["step"]["real_life_case"]["available"] is True
        if n<6:sky_aula.next_stage(session["lesson_id"])
    assert sky_aula.end(session["lesson_id"]) is True


def test_youtube_no_fake_results_without_key(monkeypatch):
    monkeypatch.delenv("SKY_YOUTUBE_API_KEY",raising=False)
    monkeypatch.delenv("SKY_LOCAL_ONLY",raising=False)
    x=media.youtube("física cuántica","secundaria")
    assert x["status"]=="needs_configuration" and x["searched_live"] is False
    assert x["videos"]==[]
    assert x["fallback_search_url"].startswith("https://www.youtube.com/results?")
    monkeypatch.setenv("SKY_LOCAL_ONLY","1")
    y=media.youtube("física cuántica")
    assert y["status"]=="offline" and not y["videos"]


def test_youtube_official_search_filters_video_identifiers(monkeypatch):
    monkeypatch.delenv("SKY_LOCAL_ONLY",raising=False)
    monkeypatch.setenv("SKY_YOUTUBE_API_KEY","dummy-do-not-use")
    observed=[]
    monkeypatch.setattr(media,"_youtube_fetch",lambda url:(
        observed.append(url) or {"items":[
            {"id":{"videoId":"AbCdEFg_123"},"snippet":{"title":"Curso digital","channelTitle":"Escuela","publishedAt":"2026-01-02"}},
            {"id":{"videoId":"BAD<script>"},"snippet":{"title":"Ataque"}},
            {"id":{"videoId":"AbCdEFg_124"},"snippet":{"title":"Tutorial"}}]}))
    r=media.youtube("partes de computadora","tecnico",3)
    assert observed and observed[0].startswith("https://www.googleapis.com/youtube/v3/search?")
    assert "videoEmbeddable=true" in observed[0] and "safeSearch=strict" in observed[0]
    assert r["searched_live"] and len(r["videos"])==2
    assert r["videos"][0]["watch_url"]=="https://www.youtube.com/watch?v=AbCdEFg_123"
    assert r["videos"][0]["embed_url"]=="https://www.youtube-nocookie.com/embed/AbCdEFg_123"
    assert r["videos"][0]["watched_by_sky"] is False
    assert "dummy-do-not-use" not in json.dumps(r)


def test_youtube_refuses_untrusted_api_url():
    with pytest.raises(media.MediaInputError):
        media._youtube_fetch("https://evil.example/youtube")


def test_sources_no_claim_of_reading_full_papers(monkeypatch):
    monkeypatch.delenv("SKY_LOCAL_ONLY",raising=False)
    from neural_core import sky_scholarly
    monkeypatch.setattr(sky_scholarly,"search_papers",lambda *a,**k:{
        "items":[{"title":"Verified by metadata only","doi":"10.1000/test"}]})
    r=media.bibliography("sistema respiratorio")
    assert r["status"]=="live_metadata" and r["verified_article_contents"] is False
    assert r["items"][0]["doi"]=="10.1000/test"


def test_computer_3d_has_parts_safe_case_and_no_unknown_fake_models():
    x=media.scene("computer")
    assert x["available"] and len(x["components"])==8
    assert {i["id"] for i in x["components"]}=={
        "case","motherboard","cpu","ram","ssd","psu","gpu","cooling"}
    assert "modelo 3D" not in json.dumps(media.scene("unlisted"),ensure_ascii=False) or not media.scene("unlisted")["available"]
    assert not media.scene("unknown")["available"]
    assert x["hardware_specific_model_verified"] is False
    assert "Never" not in x["safety"]


def test_computer_real_examples_and_others_are_illustrative():
    for topic in ["partes de la computadora","porcentaje","circuito eléctrico",
                  "respiración humana","contabilidad de una venta"]:
        example=media.practical_example(topic)
        assert example["available"]
        assert example["illustrative_not_real_observed_case"] is True
        assert len(example["steps"])>=3
    assert not media.practical_example("materia completamente desconocida")["available"]


@pytest.mark.parametrize("instrument",assess.INSTRUMENTS)
def test_all_instruments_cover_three_saberes(instrument):
    d=assess.build("computadoras","tecnico","Identificar sus componentes",
                   evaluation_type="formativa",instrument=instrument)
    assert len(d["dimensions"])==3
    assert {r["dimension"] for r in d["dimensions"]}=={"conocer","hacer","ser"}
    assert d["teacher_must_approve_before_grading"] is True
    assert d["curriculum_verified"] is False
    if instrument=="rubrica":
        assert all(len(r["levels"])==4 for r in d["dimensions"])
    if instrument=="lista_cotejo":
        assert all("No observado" in r["options"] for r in d["dimensions"])


@pytest.mark.parametrize("evaluation_type",assess.TYPES)
def test_diagnostic_formative_summative_are_supported(evaluation_type):
    x=assess.build("principios de informática","primaria","Explicar hardware",
                   evaluation_type=evaluation_type)
    assert x["type"]==evaluation_type


def test_rubric_teacher_observations_required_before_suggested_score():
    x=assess.build("hardware","tecnico","Explicar piezas")
    ratings={k:{"level":v,"evidence":"Actividad de observación del docente"} for k,v in
             [("conocer",3),("hacer",4),("ser",2)]}
    with pytest.raises(assess.AssessmentInput):
        assess.evaluate(x,ratings,teacher_approved=False)
    r=assess.evaluate(x,ratings,teacher_approved=True)
    assert r["score_pct"]==87.5
    assert r["official_grade"] is False
    with pytest.raises(assess.AssessmentInput):
        assess.evaluate(x,{"conocer":ratings["conocer"]},teacher_approved=True)


def test_private_student_data_not_persisted_and_missing_curriculum_not_invented():
    session=sky_aula.start("introducción a computación","primaria")
    feedback=sky_aula.formative_response(session["lesson_id"],"La memoria sirve para trabajar")
    assert feedback["response_recorded"] is False
    assert feedback["correctness_graded"] is False
    assert sky_aula.end(session["lesson_id"])
    rubric=assess.build("computadoras","primaria","Identificar las piezas")
    assert rubric["personal_student_data_persisted"] is False


def test_hud_docencia_and_public_3d_viewer_are_in_original_app():
    hud=Path("metaverse/static/hud.js").read_text(encoding="utf-8")
    assert "t: 'Docencia'" in hud
    assert "async function" in hud and "function abrirAula()" in hud
    assert "education/resources/videos" in hud and "education/assessments/document" in hud
    html=Path("metaverse/static/sky-aula-computer-3d.html").read_text(encoding="utf-8")
    assert "THREE.BoxGeometry" in html and "OrbitControls" in html
    assert "importmap" in html and "aria-live" in html
    api=Path("metaverse/api.py").read_text(encoding="utf-8")
    assert "def aula_computer_3d" in api
    routes=Path("metaverse/academy_api.py").read_text(encoding="utf-8")
    assert '"/education/resources/videos"' in routes
    assert '"/education/assessments/review"' in routes
    assert '"/education/assessments/document"' in routes
