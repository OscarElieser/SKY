"""SKY Innovation Lab: project methodology for rallies, hackathons & research.

All output explicitly labels unvalidated assumptions and missing real-world
evidence. Never fabricates beneficiaries, revenue, feasibility or citations.
"""
from __future__ import annotations

import re
from typing import Any

from . import sky_evidence_lab as research

EVENTS = {
    "rally_nacional": "Rally Nacional Nicaragua Innova",
    "rally_latinoamericano": "Rally Latinoamericano de Innovación",
    "hackathon_nicaragua": "Hackathon Nicaragua",
    "hackathon": "Hackathon o reto de innovación",
    "innovatec": "INNOVATEC",
    "emprendimiento": "Emprendimiento / incubación",
    "investigacion": "Investigación aplicada",
    "general": "Proyecto académico o comunitario",
}
CANVAS_BLOCKS = (
    "Segmentos de clientes/beneficiarios",
    "Propuesta de valor",
    "Canales",
    "Relación con clientes/beneficiarios",
    "Fuentes de ingresos o sostenibilidad financiera",
    "Recursos clave",
    "Actividades clave",
    "Socios y alianzas clave",
    "Estructura de costos",
)
DELIVERABLES = (
    "Acta y roles del equipo", "Normas de colaboración",
    "Delimitación del problema y árbol de causas/efectos",
    "Objetivo general y metas SMART comprobables",
    "Hipótesis de solución y validación",
    "Matriz impacto-viabilidad con criterios verificables",
    "Propuesta de valor y segmentos beneficiarios",
    "Buyer persona hipotética y mapa de empatía",
    "Modelo de negocio Canvas de nueve bloques",
    "Prototipo MVP, criterios de prueba y accesibilidad",
    "Pitch, demostración, preguntas del jurado",
    "Fuentes, evidencias, riesgos y costos comprobados",
)


def _string(value: str, name: str, maximum: int, minimum: int=5) -> str:
    if not isinstance(value,str) or not minimum<=len(value.strip())<=maximum:
        raise ValueError(f"{name}: debe tener de {minimum} a {maximum} caracteres.")
    value=" ".join(value.split())
    if any(ord(ch)<32 for ch in value):
        raise ValueError("Datos de texto inválidos.")
    return value


def build_project(name: str, challenge: str, category: str, event: str="general",
                  solution: str="", beneficiaries: str="", evidence_text: str="",
                  pitch_minutes: int=3) -> dict[str, Any]:
    if category not in research.RESEARCH_AREAS:
        raise ValueError("Categoría de proyecto no reconocida.")
    if event not in EVENTS:
        raise ValueError("Evento no reconocido.")
    if not isinstance(pitch_minutes,int) or not 1<=pitch_minutes<=5:
        raise ValueError("El pitch debe durar de uno a cinco minutos.")
    name = _string(name, "Nombre", 110, 3)
    challenge = _string(challenge, "Problema", 1000, 10)
    solution = _string(solution, "Idea de solución", 1100, 0) if solution else ""
    beneficiaries = _string(beneficiaries, "Beneficiarios", 300, 0) if beneficiaries else ""
    evidence_text = _string(evidence_text, "Evidencia proporcionada", 3500, 0) if evidence_text else ""
    solution = solution or "[Por formular con el equipo y posibles usuarios]"
    target = beneficiaries or "[Identificar mediante entrevistas autorizadas]"
    brief = research.evidence_brief(challenge[:200], category)
    citations = [e["citation"] for e in brief["evidence"]]

    # These are drafting scaffolds; strings are always marked as assumptions.
    problem_tree = {
        "problem":challenge,
        "possible_causes":"[Hipótesis: entrevistar usuarios y revisar estudios antes de fijar causas]",
        "possible_effects":"[Hipótesis: investigar efectos y medir línea base]",
        "evidence_status":"requires_field_validation",
    }
    canvas = {
        CANVAS_BLOCKS[0]: target,
        CANVAS_BLOCKS[1]: f"Hipótesis de valor: {solution}",
        CANVAS_BLOCKS[2]: "[Validar canales de alcance y accesibilidad]",
        CANVAS_BLOCKS[3]: "[Validar relación, soporte y confianza]",
        CANVAS_BLOCKS[4]: "[No estimado: calcular ingresos/financiamiento con datos reales]",
        CANVAS_BLOCKS[5]: "[Inventariar equipo, habilidades, licencias y recursos]",
        CANVAS_BLOCKS[6]: "[Planificar investigación, prototipo, pruebas y seguimiento]",
        CANVAS_BLOCKS[7]: "[Confirmar alianzas; no inventar instituciones participantes]",
        CANVAS_BLOCKS[8]: "[Presupuesto pendiente de cotizaciones y gastos comprobados]",
    }
    minutes = pitch_minutes
    pitch_sections = [
        {
            "name":"Problema y población", "seconds":round(minutes*60*.26),
            "draft":f"Queremos estudiar esta situación: {challenge}. "
                    f"Nuestro grupo objetivo, aún por validar, es {target}. "
                    "Para afirmar cifras necesitamos resultados o fuentes comprobables.",
        },
        {
            "name":"Solución y propuesta de valor", "seconds":round(minutes*60*.29),
            "draft":f"Proponemos explorar la siguiente solución: {solution}. "
                    "Su aceptación e impacto requieren prueba con personas usuarias.",
        },
        {
            "name":"Prototipo y viabilidad", "seconds":round(minutes*60*.25),
            "draft":"Mostraremos un MVP y un recorrido reproducible. "
                    "Los costos, riesgos y métricas se actualizarán con evidencia.",
        },
        {
            "name":"Impacto, validación y cierre", "seconds":0,
            "draft":"Nuestra siguiente etapa consiste en contrastar la hipótesis, "
                    "medir resultados y mejorar el prototipo con retroalimentación.",
        },
    ]
    pitch_sections[-1]["seconds"]=minutes*60-sum(s["seconds"] for s in pitch_sections[:-1])
    draft_markdown = "\n".join([
        f"# {name}",
        f"**Tipo:** {EVENTS[event]}  |  **Área:** {category}",
        "## Problema identificado (pendiente de validación)",
        challenge,
        "## Público o población beneficiaria (hipótesis)",
        target,
        "## Propuesta de solución (hipótesis)",
        solution,
        "## Objetivo general propuesto",
        f"Diseñar y evaluar una posible solución a «{challenge}» con el grupo objetivo definido.",
        "## Metas SMART (por completar con línea base real)",
        "- Específica: definir con claridad un problema validado y una solución comprobable.",
        "- Medible: [métrica, fuente, línea base, meta cuantificada y fórmula pendientes].",
        "- Alcanzable: [recursos, presupuesto, restricciones y cotizaciones pendientes].",
        "- Relevante: demostrar relación entre necesidad y beneficio mediante evidencia.",
        "- Temporal: [fecha e hitos por acordar con el equipo].",
        "## Matriz de impacto y viabilidad",
        "Impacto: [sin puntuación hasta tener datos]; Viabilidad: [sin puntuación hasta evaluar recursos].",
        "## Canvas preliminar (no validado)",
        *[f"- **{key}:** {value}" for key,value in canvas.items()],
        "## Evidencia aportada por el equipo (no verificada)",
        evidence_text or "[No se aportaron datos, entrevistas ni documentos específicos.]",
        "Cualquier afirmación incluida aquí debe comprobarse antes de publicar.",
        "## Prototipo y pruebas",
        "MVP: [describir pantallas o prototipo real]. Pruebas: [plan de usuarios, consentimiento, criterios y resultados].",
        "## Guion de pitch (borrador)",
        *[f"### {s['name']} ({s['seconds']} s)\n{s['draft']}" for s in pitch_sections],
        "## Fuentes y grado de confianza",
        ("Fuentes de archivos facilitados: " + ", ".join(citations) if citations
         else "No se recuperó evidencia documental relacionada."),
        "No se realizó investigación web ni validación externa. "
        "Verificar cualquier dato y enlazar fuentes antes de presentarlo como definitivo.",
    ])
    return {
        "central_agent":"SKY",
        "project_name":name,"competition":EVENTS[event],
        "category":category,"challenge":challenge,
        "solution_hypothesis":solution,"beneficiaries_hypothesis":target,
        "problem_tree":problem_tree,
        "canvas":canvas,
        "canvas_validated":False,
        "smart_goals_verified":False,
        "impact_scored":False,"viability_scored":False,
        "pitch_minutes":minutes,"pitch_sections":pitch_sections,
        "pitch_duration_tested":False,"rehearsal_required":True,
        "tasks":[{"deliverable":d,"status":"template_or_pending_validation"}
                 for d in DELIVERABLES],
        "research":brief,
        "supplied_evidence_is_unverified":bool(evidence_text),
        "validation_plan":[
            "Recopilar datos oficiales con fecha y fuente original.",
            "Realizar entrevistas autorizadas con consentimiento y sin datos sensibles de menores.",
            "Definir criterios medibles, indicadores y línea base.",
            "Construir MVP y comprobar funcionamiento mediante pruebas.",
            "Documentar costos y riesgos con soportes reales.",
            "Revisar evidencia, sesgos y viabilidad antes de presentar.",
        ],
        "document_markdown":draft_markdown[:30000],
        "document_generated":False,
        "data_invented":False,
        "research_completed":False,
        "source_verification_pending":True,
        "warning":"Todos los datos no confirmados quedan como hipótesis o campos pendientes.",
    }


def catalogue() -> dict:
    return {
        "central_agent":"SKY",
        "supported_competitions":EVENTS,
        "project_areas":sorted(research.RESEARCH_AREAS),
        "deliverable_templates":list(DELIVERABLES),
        "canvas_nine_blocks":list(CANVAS_BLOCKS),
        "professional_output":"structured_markdown_draft_compatible_with_sky_office",
        "automatic_verified_web_research":False,
        "fabricates_numbers_or_studies":False,
        "medical_decisions":"requires_human_clinical_review",
        "recommendation":"Validate real competition rules for each edition and audience.",
    }
