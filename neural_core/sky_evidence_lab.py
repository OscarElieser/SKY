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



def retrieve_official_sources(topic: str, source_ids: list[str]) -> dict:
    """Fetch only vetted HTTPS catalogue URLs, on explicit owner instruction.

    This is a limited, non-search-engine retrieval. HTML is UNTRUSTED DATA.
    Retrieving an official site does not certify a particular claim or
    establish that the site is up to date.
    """
    from datetime import datetime, timezone
    from hashlib import sha256
    from html.parser import HTMLParser
    import ssl
    import urllib.error
    import urllib.parse
    import urllib.request

    if not isinstance(topic, str) or not 5 <= len(topic.strip()) <= 240:
        raise ValueError("Tema inválido para consulta de fuentes.")
    if not isinstance(source_ids, list) or not 1 <= len(source_ids) <= 4:
        raise ValueError("Elegí de 1 a 4 referencias oficiales.")
    if len(set(source_ids)) != len(source_ids) or any(x not in OFFICIAL_REGISTRY for x in source_ids):
        raise ValueError("Solo se permiten identificadores únicos del catálogo de SKY.")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            raise ValueError("El origen oficial redirigió; SKY no seguirá la redirección automáticamente.")

    class CleanText(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.fragments=[]
            self.hidden=0
        def handle_starttag(self, tag, attrs):
            if tag in ("script","style","noscript","svg","form"):
                self.hidden+=1
        def handle_endtag(self, tag):
            if tag in ("script","style","noscript","svg","form"):
                self.hidden=max(0,self.hidden-1)
            if not self.hidden and tag in ("p","h1","h2","h3","li","article"):
                self.fragments.append("\n")
        def handle_data(self, text):
            if not self.hidden and len(self.fragments)<8000:
                self.fragments.append(text)

    requested = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}", topic.casefold())[:15]
    responses=[]
    for source_id in source_ids:
        item=OFFICIAL_REGISTRY[source_id]
        url=item["url"]
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!="https" or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("La fuente del catálogo no cumple las reglas de HTTPS.")
        # Verify exact host allowlist derived from reviewed registry, not user input.
        verified_hosts={
            urllib.parse.urlsplit(row["url"]).hostname for row in OFFICIAL_REGISTRY.values()
        }
        if parsed.hostname not in verified_hosts:
            raise ValueError("Dominio no admitido por SKY.")
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"SKY-Evidence-Reader/1.0 (owner-initiated academic use)",
                "Accept":"text/html,text/plain",
            })
            opener=urllib.request.build_opener(
                urllib.request.ProxyHandler({}),
                NoRedirect(),
                urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            )
            with opener.open(req,timeout=8) as response:
                if response.status!=200:
                    raise OSError("HTTP distinto de 200.")
                typ=response.headers.get("Content-Type","").lower()
                if "text/html" not in typ and "text/plain" not in typ:
                    raise OSError("SKY admite solo HTML o texto oficial en este lector.")
                raw=response.read(250_001)
                if len(raw)>250_000:
                    raise OSError("Documento remoto excede el límite de lectura.")
                charset=response.headers.get_content_charset() or "utf-8"
                try:
                    html=raw.decode(charset,errors="replace")
                except LookupError:
                    html=raw.decode("utf-8",errors="replace")
            if "html" in typ:
                parser=CleanText()
                parser.feed(html)
                content=" ".join(" ".join(parser.fragments).split())[:25000]
            else:
                content=" ".join(html.split())[:25000]
            if not content.strip():
                raise OSError("La fuente no entregó texto utilizable.")
            sections=[]
            folded=content.casefold()
            for word in requested:
                pos=folded.find(word)
                if pos>=0:
                    sections.append(content[max(0,pos-180):min(len(content),pos+350)])
                if len(sections)>=5:
                    break
            responses.append({
                "id":source_id,"url":url,"label":item["label"],
                "status":"official_page_retrieved_not_independently_verified",
                "retrieved_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "retrieved_sha256":sha256(raw).hexdigest(),
                "topic_excerpts":sections,"topic_match":bool(sections),
                "site_publication_date_verified":False,
                "text_instructions_executed":False,
            })
        except (OSError,ValueError,TimeoutError,urllib.error.URLError) as exc:
            responses.append({
                "id":source_id,"url":url,"label":item["label"],
                "status":"unavailable_or_unsupported",
                "error":"No se recuperó texto oficial verificable en esta solicitud.",
                "topic_excerpts":[],
            })
    return {
        "central_agent":"SKY",
        "topic":topic.strip(),"sources":responses,
        "pages_retrieved":sum(x["status"].startswith("official_page_retrieved") for x in responses),
        "all_claims_verified":False,
        "research_completed":False,
        "needs_human_source_comparison":True,
        "notice":"SKY consultó sólo enlaces preautorizados. Revisar los extractos, fechas de publicación y fuentes independientes.",
    }
