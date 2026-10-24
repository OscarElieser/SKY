"""Owner authenticated education, innovation and evidence APIs for SKY CORE.

Never claims sources were fetched; outputs remain marked as didactic drafts
until verified with official curricula and independent, dated evidence.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .api import require_key
from neural_core import sky_aula, sky_evidence_lab, sky_innovation_lab

router = APIRouter(prefix="/api/sky/academy",dependencies=[Depends(require_key)])


class LessonRequest(BaseModel):
    topic: str=Field(min_length=4,max_length=160)
    level: str=Field(min_length=5,max_length=20)
    duration_minutes: int=Field(default=45,ge=15,le=180)
    learning_goal: str=Field(default="",max_length=250)
    reference_text: str=Field(default="",max_length=12000)
    grade: str=Field(default="",max_length=55)


class ProjectRequest(BaseModel):
    name: str=Field(min_length=3,max_length=110)
    challenge: str=Field(min_length=10,max_length=1000)
    category: str=Field(min_length=3,max_length=35)
    event: str=Field(default="general",max_length=40)
    solution: str=Field(default="",max_length=1100)
    beneficiaries: str=Field(default="",max_length=300)
    evidence_text: str=Field(default="",max_length=3500)
    pitch_minutes: int=Field(default=3,ge=1,le=5)


class StudentResponse(BaseModel):
    answer: str=Field(min_length=2,max_length=800)


class ResearchRequest(BaseModel):
    topic: str=Field(min_length=5,max_length=240)
    domain: str=Field(min_length=3,max_length=35)
    library_search: bool=True


class OfficialSourcesRequest(BaseModel):
    topic: str=Field(min_length=5,max_length=240)
    source_ids: list[str]=Field(min_length=1,max_length=4)


class DocumentFormat(BaseModel):
    kind: str=Field(default="docx",pattern="^(docx|pdf|pptx|md)$")


class LessonExport(LessonRequest):
    kind: str=Field(default="docx",pattern="^(docx|pdf|pptx|md)$")


class ProjectExport(ProjectRequest):
    kind: str=Field(default="docx",pattern="^(docx|pdf|pptx|md)$")


def _lesson(body: LessonRequest):
    return sky_aula.lesson(**body.model_dump())


def _project(body: ProjectRequest):
    return sky_innovation_lab.build_project(**body.model_dump())


def _document(content: str,title: str,kind: str):
    from neural_core.sky_office import create_document
    try:
        file=create_document({"kind":kind,"title":title,"content":content})
    except (ValueError,RuntimeError,ImportError) as exc:
        raise HTTPException(422,str(exc)[:180]) from exc
    return Response(
        content=file.data, media_type=file.media_type,
        headers={"Content-Disposition":f'attachment; filename="{file.filename}"',
                 "X-SKY-Research-Status":"draft-not-externally-verified",
                 "Cache-Control":"private, no-store"},
    )


@router.get("/capabilities")
def capabilities():
    return {
        "central_agent":"SKY",
        "aula":sky_aula.catalogue(),
        "innovation":sky_innovation_lab.catalogue(),
        "research":sky_evidence_lab.catalogue(),
        "live_classroom_video_or_real_student_grading":False,
        "real_time_web_fact_verification":False,
    }


@router.get("/education/levels")
def levels():
    return sky_aula.catalogue()


@router.post("/education/lesson")
def prepare_lesson(body: LessonRequest):
    try:
        return _lesson(body)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.post("/education/sessions", status_code=201)
def start_lesson(body: LessonRequest):
    try:
        return sky_aula.start(**body.model_dump())
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(429,str(exc)) from exc


@router.get("/education/sessions/{lesson_id}")
def current_lesson(lesson_id: str):
    try:
        return sky_aula.current(lesson_id)
    except KeyError as exc:
        raise HTTPException(404,str(exc)) from exc


@router.post("/education/sessions/{lesson_id}/next")
def next_lesson(lesson_id: str):
    try:
        return sky_aula.next_stage(lesson_id)
    except KeyError as exc:
        raise HTTPException(404,str(exc)) from exc


@router.post("/education/sessions/{lesson_id}/respond")
def student_response(lesson_id: str, body: StudentResponse):
    try:
        return sky_aula.formative_response(lesson_id,body.answer)
    except KeyError as exc:
        raise HTTPException(404,str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.delete("/education/sessions/{lesson_id}")
def delete_lesson(lesson_id: str):
    return {"closed":sky_aula.end(lesson_id)}


@router.post("/education/lesson/document")
def lesson_document(body: LessonExport):
    try:
        fields=body.model_dump()
        kind=fields.pop("kind")
        spec=sky_aula.lesson(**fields)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    plan_lines=[
        f"# Plan de clase SKY — {spec['topic']}",
        f"**Nivel:** {spec['level_label']}",
        f"**Grado/curso:** {spec['grade'] or '[por precisar]'}",
        f"**Duración:** {spec['duration_minutes']} minutos",
        f"**Aprendizaje esperado:** {spec['goal']}",
        f"**Enfoque metodológico:** {spec['method']}",
        f"**Evidencia de aprendizaje:** {spec['assessment_method']}",
        "## Desarrollo por etapas",
    ]
    for i,stage in enumerate(spec["stages"]):
        # Only teacher-provided source, never generated curricula.
        detail=sky_aula.stage_output({**spec,"_source_text":body.reference_text},i)
        plan_lines.extend([
            f"### {stage['name']} — {stage['minutes']} min",
            detail["voice_ready_text"],
            f"**Pregunta al grupo:** {detail['question']}",
        ])
    plan_lines += [
        "## Estado documental",
        "Plan didáctico preliminar, pendiente de cotejar con el programa de estudio.",
        "No se verificaron automáticamente las competencias ni las fuentes.",
        *spec["evidence_gaps"],
    ]
    return _document("\n\n".join(plan_lines),
                     f"Clase SKY {spec['topic']}",kind)


@router.get("/innovation/capabilities")
def innovation_capabilities():
    return sky_innovation_lab.catalogue()


@router.post("/innovation/project")
def project(body: ProjectRequest):
    try:
        return _project(body)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.post("/innovation/project/document")
def project_document(body: ProjectExport):
    try:
        fields=body.model_dump()
        kind=fields.pop("kind")
        proposal=sky_innovation_lab.build_project(**fields)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    return _document(proposal["document_markdown"],
                     proposal["project_name"],kind)


@router.post("/research/brief")
def evidence_brief(body: ResearchRequest):
    try:
        return sky_evidence_lab.evidence_brief(
            body.topic,body.domain,library_search=body.library_search
        )
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.post("/research/official-sources")
def official_source_retrieval(body: OfficialSourcesRequest):
    try:
        return sky_evidence_lab.retrieve_official_sources(body.topic,body.source_ids)
    except ValueError as exc:
        raise HTTPException(422,str(exc)[:200]) from exc


@router.get("/research/sources")
def source_catalogue():
    return sky_evidence_lab.catalogue()


# SKY Investigadora: bibliografía de fuentes reales, no referencias inventadas.
class BibliographyRequest(BaseModel):
    query: str=Field(min_length=5,max_length=240)
    provider: str=Field(default="openalex",pattern="^(openalex|crossref)$")
    limit: int=Field(default=6,ge=1,le=12)


class RubricRequest(BaseModel):
    objective: str=Field(min_length=5,max_length=300)
    criteria: list[str]=Field(min_length=1,max_length=6)
    student_response: str=Field(min_length=2,max_length=800)


@router.post("/research/live-papers")
def live_bibliography(body: BibliographyRequest):
    from neural_core.sky_scholarly import search_papers
    from neural_core import sky_metricas
    import time
    tic=time.perf_counter()
    try:
        result=search_papers(body.query,provider=body.provider,limit=body.limit)
        sky_metricas.registrar("servicio","bibliography_lookup",True,(time.perf_counter()-tic)*1000)
        return {
            **result,
            "results_observed":len(result.get("items",[])),
            "metadata_only":True,
            "content_or_peer_review_verified":False,
            "generated_citations_without_metadata":False,
        }
    except (ValueError,RuntimeError,OSError) as exc:
        sky_metricas.registrar("servicio","bibliography_lookup",False,(time.perf_counter()-tic)*1000)
        raise HTTPException(502,"No se pudo consultar la fuente académica: "+str(exc)[:140]) from exc


@router.post("/education/formative-rubric")
def guided_rubric(body: RubricRequest):
    from neural_core.sky_verification_lab import formative_review
    try:
        return formative_review(body.objective,body.criteria,body.student_response)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
