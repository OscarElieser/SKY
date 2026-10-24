"""Extensión autenticada de la API existente de SKY para docencia e innovación."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from neural_core import sky_impacto as engine
from neural_core import sky_scholarly, sky_pro_skills

# La autenticación se aplica al registrar el router en metaverse.api.
router = APIRouter(prefix="/api/impacto", tags=["SKY Impacto"])


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    kind: str = Field(default="informe", max_length=30)
    category: str = Field(default="", max_length=30)


class LessonRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    level: str = Field(default="", max_length=40)
    minutes: int = Field(default=45, ge=10, le=240)
    objective: str = Field(default="", max_length=500)


class LessonTurn(BaseModel):
    plan: dict
    step: int = Field(ge=1, le=6)
    student_response: str = Field(default="", max_length=1500)


class ProjectRequest(BaseModel):
    challenge: str = Field(min_length=1, max_length=500)
    competition: str = Field(default="", max_length=120)
    audience: str = Field(default="", max_length=120)


class JudgeRequest(BaseModel):
    scores: dict
    rubric: dict


class ReferenceRequest(BaseModel):
    references: list[dict] = Field(default_factory=list, max_length=50)


def _run(func, *args, **kwargs):
    try:
        return {"ok": True, "result": func(*args, **kwargs)}
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)[:260]) from exc


@router.get("/status")
def status():
    return {"ok": True, "module": "SKY Impacto", "version": "1.0",
            "catalogued_sources": len(engine.SOURCES),
            "external_services_connected": False,
            "model_required_for_freeform_reasoning": True,
            "voice_uses_existing_sky_engine": True}


@router.get("/sources")
def sources(category: str = ""):
    return _run(engine.list_sources, category)


@router.post("/sources/{source_id}/consult")
def consult(source_id: str):
    # Petición explícita; sin capacidad de introducir URLs arbitrarias.
    return _run(engine.consult_source, source_id)


@router.post("/research/plan")
def research(body: ResearchRequest):
    return _run(engine.research_plan, body.topic, body.kind, body.category)


@router.post("/lesson/plan")
def lesson(body: LessonRequest):
    return _run(engine.lesson_plan, body.topic, body.level, body.minutes, body.objective)


@router.post("/lesson/step")
def lesson_turn(body: LessonTurn):
    return _run(engine.lesson_step, body.plan, body.step, body.student_response)


@router.post("/innovation/project")
def project(body: ProjectRequest):
    return _run(engine.innovation_project, body.challenge, body.competition, body.audience)


@router.post("/competition/review")
def judge(body: JudgeRequest):
    return _run(engine.judge_project, body.scores, body.rubric)


@router.post("/references/audit")
def references(body: ReferenceRequest):
    return _run(engine.verify_references, body.references)


# ----------------------------------------------------------------------
# SKY Scholar y Skills: siguen protegidos por require_key/2FA en metaverse.api.
# ----------------------------------------------------------------------
class ScholarSearch(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    provider: str = Field(default="openalex", max_length=20)
    limit: int = Field(default=6, ge=1, le=15)


class DoiRequest(BaseModel):
    doi: str = Field(min_length=7, max_length=250)


class GitHubDocument(BaseModel):
    repository: str = Field(min_length=3, max_length=120)
    path: str = Field(min_length=1, max_length=160)


class SkillsRequest(BaseModel):
    task: str = Field(min_length=1, max_length=2500)
    selected: list[str] | None = Field(default=None, max_length=8)


class ResearchWriteRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    instruction: str = Field(min_length=5, max_length=1500)
    literature_provider: str = Field(default="openalex", max_length=20)
    model_provider: str = Field(default="auto", max_length=30)
    selected_skills: list[str] | None = Field(default=None, max_length=8)


def _external(fn, *args):
    # No exponer trazas de red ni declarar consulta exitosa si la API externa falla.
    try:
        return {"ok": True, "result": fn(*args)}
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)[:250]) from exc
    except (OSError, TimeoutError, UnicodeError) as exc:
        raise HTTPException(502, "La fuente académica no respondió: " + type(exc).__name__) from exc


@router.get("/university/repositories")
def university_repositories(country: str = ""):
    return _run(sky_scholarly.list_universities, country)


@router.get("/scholar/google-link")
def scholar_google_link(query: str):
    return _run(sky_scholarly.scholar_link, query)


@router.post("/scholar/search")
def scholar_search(body: ScholarSearch):
    return _external(sky_scholarly.search_papers, body.query, body.provider, body.limit)


@router.post("/scholar/doi")
def scholar_doi(body: DoiRequest):
    return _external(sky_scholarly.lookup_doi, body.doi)


@router.post("/repository/read")
def repository_read(body: GitHubDocument):
    return _external(sky_scholarly.read_github_reference, body.repository, body.path)


@router.post("/document/read")
async def document_read(file: UploadFile = File(...)):
    """Reutiliza el extractor SKY, sin guardar ni publicar archivos.

    No se declara texto extraído si el lector devuelve un marcador de error.
    """
    from neural_core.documentos import extraer_texto
    import re
    filename = (file.filename or "").split("/")[-1].split("\\")[-1]
    if not re.fullmatch(r"[\w .()\-]{1,100}\.(pdf|docx|txt|md|rst)", filename, re.I):
        raise HTTPException(422, "Sólo PDF, DOCX, TXT, MD y RST.")
    raw = await file.read(5_000_001)
    if not raw or len(raw) > 5_000_000:
        raise HTTPException(413, "Archivo vacío o mayor a 5 MB.")
    try:
        extracted = extraer_texto(filename, raw)
    except (ValueError, OSError, RuntimeError) as exc:
        raise HTTPException(422, "El documento no pudo interpretarse.") from exc
    if extracted.startswith(("[Documento PDF:", "[Documento DOCX:", "[Archivo recibido:")):
        raise HTTPException(422, "No se detectó texto legible; puede requerir OCR autorizado.")
    return {"ok": True, "result": {"filename": filename, "characters": len(extracted),
            "text": extracted[:35_000], "truncated": len(extracted) > 35_000,
            "source_type": "user_uploaded_document", "content_untrusted": True,
            "note": "Texto extraído. No se consideran verificadas sus afirmaciones."}}


@router.get("/skills")
def skills_list():
    return {"ok": True, "skills": sky_pro_skills.catalog()}


@router.post("/skills/plan")
def skills_plan(body: SkillsRequest):
    return _run(sky_pro_skills.skill_plan, body.task, body.selected)


@router.post("/research/write")
def research_write(body: ResearchWriteRequest):
    """Pesquisa y borrador mediante motor ya configurado. La búsqueda es explícita.

    Sólo pasa títulos, autores, años y URLs al modelo: nunca aparenta acceso
    al texto íntegro de los artículos. Debe citar y verificar antes de publicar.
    """
    found = _external(sky_scholarly.search_papers, body.topic, body.literature_provider, 5)["result"]
    items = found["items"]
    if not items:
        return {"ok": False, "error": "La consulta no produjo referencias; no se generará un texto académico con fuentes inventadas.",
                "literature": found}
    from neural_core.assistant import responder
    from neural_core.providers import ProviderError
    skills = sky_pro_skills.match_skills(body.instruction + " " + body.topic,
                                          explicit=body.selected_skills)
    refs = [{"titulo": x["title"], "fuente": x["provider"],
             "fecha": str(x.get("year") or ""), "url": x.get("url", "")}
            for x in items if x.get("title") and x.get("url")][:5]
    task = (f"Tema: {body.topic}\nObjetivo editorial: {body.instruction}\n"
            f"Skills elegidas: {', '.join(skills) or 'investigación'}.\n"
            "Redactá un BORRADOR de apoyo, no una tesis terminada. Estas referencias son "
            "sólo metadatos bibliográficos recuperados; NO conocés los métodos, "
            "resultados ni conclusiones de sus artículos. No inventés citas, cifras, "
            "estudios, DOI, resultados ni páginas. Señalá dónde hace falta leer el "
            "texto íntegro y verificar la evidencia. Distingí lo que se sabe de lo "
            "que sólo es una pregunta de investigación.")
    try:
        answer, _ = responder(task, "Investigación académica y redacción", proveedor=body.model_provider,
                              fuentes_externas=refs)
    except (ProviderError, ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(503, "Motor de redacción no disponible: " + type(exc).__name__) from exc
    return {"ok": True, "draft": answer, "literature": found, "skills": skills,
            "status": "draft_with_metadata_not_fulltext", "citations_verified_in_text": False}
