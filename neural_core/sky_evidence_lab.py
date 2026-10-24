"""SKY Evidence Lab: verifiable-source protocol for education and innovation.

A catalogue of official websites is NOT evidence that SKY accessed them.
Owner uploads are searchable with citations but remain unverified sources.
No fabricated bibliography, interviews, budgets, health data or impact.
"""
from __future__ import annotations

import re
from typing import Any

OFFICIAL_REGISTRY = {
    "mined_meidi": {
        "label": "MINED — Educación Inicial y MEIDI",
        "url": "https://www.mined.gob.ni/educacion-inicial/",
        "domains": ["educacion", "inicial"],
    },
    "mined_primaria": {
        "label": "MINED — Educación Primaria",
        "url": "https://www.mined.gob.ni/educacion-primaria/",
        "domains": ["educacion", "primaria"],
    },
    "mined_secundaria": {
        "label": "MINED — Educación Secundaria",
        "url": "https://www.mined.gob.ni/educacion-secundaria/",
        "domains": ["educacion", "secundaria"],
    },
    "inatec_hackathon": {
        "label": "Tecnológico Nacional — Plataforma Hackathon Nicaragua",
        "url": "https://mapa.tecnacional.edu.ni/hackathon-nicaragua",
        "domains": ["innovacion", "tecnico"],
    },
    "inatec_portal": {
        "label": "Tecnológico Nacional (INATEC)",
        "url": "https://tecnacional.edu.ni/",
        "domains": ["tecnico", "innovacion", "educacion"],
    },
    "unesco_education_ai": {
        "label": "UNESCO — IA generativa en educación e investigación",
        "url": "https://www.unesco.org/es/articles/guia-para-el-uso-de-ia-generativa-en-educacion-e-investigacion",
        "domains": ["educacion", "investigacion"],
    },
    "who_health_ai": {
        "label": "OMS — IA para la salud",
        "url": "https://www.who.int/publications/i/item/9789240084759",
        "domains": ["salud", "medicina"],
    },
}
RESEARCH_AREAS = frozenset({
    "educacion", "salud", "medicina", "transporte", "social", "ambiental", "cultural",
    "agropecuario", "turismo", "energia", "industria", "economia", "tecnologia",
    "vivienda", "gestion_publica", "innovacion", "investigacion", "tecnico",
})
EVIDENCE_POLICY = (
    "No afirmar resultados externos no recuperados; fuentes oficiales del catálogo "
    "son enlaces para consultar, no lecturas verificadas. "
    "Distinguir evidencia, testimonio, hipótesis y propuesta."
)


def catalogue(domain: str | None = None) -> dict:
    if domain is not None and domain not in RESEARCH_AREAS:
        raise ValueError("Área de investigación no admitida.")
    return {
        "central_agent": "SKY",
        "areas": sorted(RESEARCH_AREAS),
        "official_reference_links": [
            {"id": key, "label": value["label"], "url": value["url"],
             "status": "reference_only_not_fetched"}
            for key, value in OFFICIAL_REGISTRY.items()
            if domain is None or domain in value["domains"]
        ],
        "official_links_verified_live": False,
        "automatic_remote_research_implemented": False,
        "medical_diagnostic_authority": False,
        "evidence_policy": EVIDENCE_POLICY,
    }


def evidence_brief(topic: str, domain: str, *, library_search: bool = True) -> dict:
    """Read only the explicitly consented local knowledge library.

    Do not send student names or private material to web/model providers.
    """
    if domain not in RESEARCH_AREAS:
        raise ValueError("Área desconocida.")
    if not isinstance(topic, str) or not 5 <= len(topic.strip()) <= 240:
        raise ValueError("La investigación necesita un tema de 5 a 240 caracteres.")
    text = topic.strip()
    evidence: list[dict[str, Any]] = []
    blocked: list[str] = []
    if library_search:
        try:
            from . import sky_knowledge_library as lib
            found = lib.search(text, limit=6)
            for rec in found.get("results", []):
                evidence.append({
                    "citation": rec["citation"],
                    "source": rec["filename"],
                    "excerpt": rec["excerpt"][:850],
                    "source_status": rec.get("source_trust", "user_uploaded_unverified"),
                    "claim_externally_verified": False,
                })
        except RuntimeError:
            blocked.append("Biblioteca privada no configurada o sin clave de cifrado.")
    references = [x for x in catalogue(domain)["official_reference_links"]]
    if not evidence:
        blocked.append("No hay documentos privados con fragmentos relevantes ya indexados.")
    blocked.append(
        "No se realizó investigación web ni verificación cruzada automática: "
        "consultar fuentes, fecharlas y contrastarlas antes de asegurar hechos."
    )
    return {
        "central_agent": "SKY",
        "topic": text,
        "domain": domain,
        "evidence": evidence,
        "possible_official_sources": references,
        "review_required": True,
        "claim_externally_verified": False,
        "research_completed": False,
        "missing_evidence": blocked,
        "research_questions": [
            "¿Qué magnitud tiene el problema y quiénes lo reportan?",
            "¿Qué datos oficiales actuales y fecha sustentan la necesidad?",
            "¿Qué dicen las personas afectadas mediante entrevistas autorizadas?",
            "¿Qué soluciones existen y cuáles son sus limitaciones?",
            "¿Cómo se validará la propuesta antes de afirmar impacto?",
        ],
        "policy": EVIDENCE_POLICY,
    }


def check_claims(claims: list[dict]) -> dict:
    """Validate disclosure metadata; does NOT independently fetch or attest sources."""
    if not isinstance(claims, list) or len(claims) > 30:
        raise ValueError("Máximo 30 afirmaciones.")
    reviewed = []
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError("Afirmación con formato inválido.")
        statement = claim.get("statement", "")
        if not isinstance(statement, str) or not 4 <= len(statement.strip()) <= 800:
            raise ValueError("Afirmación vacía o demasiado extensa.")
        provided = claim.get("citation", "")
        if provided and (not isinstance(provided, str) or len(provided) > 500):
            raise ValueError("Referencia inválida.")
        reviewed.append({
            "statement": statement.strip(),
            "citation_provided": bool(provided),
            "citation": provided,
            "status": "requires_external_verification",
            "safe_to_present_as_verified_fact": False,
        })
    return {
        "central_agent": "SKY",
        "claims": reviewed,
        "all_facts_verified": False,
        "warning": "Una URL o una cita declarada no demuestran por sí solas la veracidad.",
    }
