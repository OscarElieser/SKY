"""SKY Skillpack: adapters ejecutables, no un catálogo que simule servicios conectados.

No instala software, no despliega infraestructura, no publica contenido.
Utiliza módulos propios de SKY y APIs oficiales con credenciales del equipo.
Las respuestas de un proveedor externo no se interpretan como instrucciones.
"""
from __future__ import annotations

import html
import json
import math
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

# Todas las 29 denominaciones suministradas; las que no tienen adaptador
# operativo siguen 'not_implemented'. Tener un nombre NO equivale a instalar.
_GROUPS = {
    "cloud": "aws-workflow-deploy vercel-plugin supabase-mcp github-connector docker-manager loki-mode",
    "documents": "pdf-pro xlsx-advanced docx-coauthoring pptx-generator supermemory",
    "marketing": "marketing-skills seo-audit ad-angle-research typefully open-carousel humanizer copywriting-pro",
    "productivity": "notion-workspace google-workspace-connector slack-communicator linear-sync hubspot-crm internal-comms",
    "multimedia": "remotion claude-d3js-skill algorithmic-art scientific-researcher firecrawl",
}
_ALL = {key: category for category, names in _GROUPS.items() for key in names.split()}
assert len(_ALL) == 29

# Sólo se listan capacidades con ruta de ejecución REAL en este archivo
# o existente y referenciada en la API de SKY.
_ADAPTERS = {
    "pdf-pro": ("sky_office", ()),
    "xlsx-advanced": ("sky_office", ()),
    "docx-coauthoring": ("sky_office", ()),
    "pptx-generator": ("sky_office", ()),
    "scientific-researcher": ("scholarly", ()),
    "github-connector": ("github", ()),
    "docker-manager": ("docker", ("docker",)),
    "supabase-mcp": ("supabase_rest", ("SUPABASE_URL", "SUPABASE_KEY")),
    "vercel-plugin": ("vercel", ("VERCEL_TOKEN",)),
    "notion-workspace": ("notion", ("NOTION_TOKEN",)),
    "linear-sync": ("linear", ("LINEAR_API_KEY",)),
    "hubspot-crm": ("hubspot", ("HUBSPOT_ACCESS_TOKEN",)),
    "typefully": ("typefully", ("TYPEFULLY_API_KEY", "TYPEFULLY_SOCIAL_SET_ID")),
    "firecrawl": ("firecrawl", ("FIRECRAWL_API_KEY",)),
    "seo-audit": ("seo", ()),
    "algorithmic-art": ("svg", ()),
    "open-carousel": ("carousel", ()),
    "humanizer": ("llm", ()),
    "copywriting-pro": ("llm", ()),
    "marketing-skills": ("llm", ()),
    "ad-angle-research": ("llm", ()),
    "internal-comms": ("llm", ()),
}
_OFFICE_FORMATS = {
    "pdf-pro": "pdf", "xlsx-advanced": "xlsx",
    "docx-coauthoring": "docx", "pptx-generator": "pptx",
}
_LLM_RULES = {
    "humanizer": "Edita con naturalidad. Conserva exactamente hechos, citas y significado. No inventes.",
    "copywriting-pro": "Redacta texto persuasivo con AIDA o PAS según encaje. Prohíbe cifras y testimonios inventados.",
    "marketing-skills": "Analiza audiencia, posicionamiento, conversión y métricas; separa hechos de hipótesis.",
    "ad-angle-research": "Analiza únicamente anuncios o textos suministrados; no afirmes haber investigado competidores sin fuentes.",
    "internal-comms": "Redacta comunicación profesional formal, precisa y respetuosa; no simules envíos.",
}

class SkillUnavailable(RuntimeError):
    pass

class SkillInvalid(ValueError):
    pass

def _env(key: str) -> str:
    return os.getenv(key, "").strip()

def _configured(name: str) -> bool:
    kind, required = _ADAPTERS[name]
    if kind == "docker":
        return bool(shutil.which("docker"))
    if kind == "supabase_rest":
        # SKY también reconoce la clave ANON, siempre bajo las políticas RLS.
        return bool(_env("SUPABASE_URL") and (_env("SUPABASE_ANON_KEY") or _env("BAQUEANO_SUPABASE_PUBLISHABLE_KEY")))
    if kind == "llm":
        return bool(_env("OLLAMA_URL") or any(_env(x) for x in
            ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY")))
    return all(_env(x) for x in required)

def catalogue() -> dict:
    rows = []
    for key, group in _ALL.items():
        adapter = _ADAPTERS.get(key)
        if adapter:
            mode, _ = adapter
            available = _configured(key)
            status = ("needs_configuration" if not available else "adapter_ready_unverified")
            if mode == "sky_office":
                status = "available_via_office_api"
            if mode in {"seo", "svg", "carousel", "scholarly", "github"}:
                status = "adapter_ready_unverified"
            if mode == "llm" and not available:
                status = "needs_ai_provider"
            rows.append({"id": key, "group": group, "adapter": mode, "status": status,
                         "configured": available, "live_verified": False,
                         "office_endpoint": "/api/office/generate" if mode == "sky_office" else None})
        else:
            rows.append({"id": key, "group": group, "adapter": None,
                         "status": "not_implemented", "configured": False, "live_verified": False})
    return {"total_requested_here": len(_ALL), "adapter_count": len(_ADAPTERS),
            "live_verified": 0, "skills": rows,
            "note": "Una credencial configurada no es una prueba de conexión ni de ejecución."}

def _limit_str(body: dict, name: str, maximum: int = 2000, required: bool = False) -> str:
    value = body.get(name, "")
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise SkillInvalid("Campo inválido: " + name)
    return value.strip()

def _request(method: str, url: str, *, token: str, headers: dict | None = None,
             payload: dict | None = None) -> dict:
    """Endpoint FIJO; el usuario no introduce hosts, rutas ni tokens."""
    fixed_hosts = {"api.notion.com", "api.linear.app", "api.hubapi.com",
                   "api.typefully.com", "api.vercel.com", "api.firecrawl.dev"}
    if urlparse(url).hostname not in fixed_hosts:
        raise SkillInvalid("Proveedor externo no permitido.")
    request_headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    request_headers.update(headers or {})
    try:
        with httpx.Client(timeout=12, follow_redirects=False) as client:
            r = client.request(method, url, headers=request_headers, json=payload)
            r.raise_for_status()
            data = r.json()
        if isinstance(data, dict):
            if data.get("ok") is False or data.get("errors"):
                raise SkillUnavailable("La API comunicó un error o permisos insuficientes.")
        return {"ok": True, "provider_http_status": r.status_code,
                "data": json.loads(json.dumps(data, ensure_ascii=False)[:14000])}
    except (httpx.HTTPError, ValueError) as exc:
        raise SkillUnavailable("Conexión o respuesta del proveedor no disponible.") from exc

class _SEO(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.h1 = 0
        self.images = 0
        self.images_without_alt = 0
        self.canonical = False
        self._title = False
    def handle_starttag(self, tag, attrs):
        vals = dict(attrs)
        if tag == "title":
            self._title = True
        if tag == "h1":
            self.h1 += 1
        if tag == "img":
            self.images += 1
            if not vals.get("alt"):
                self.images_without_alt += 1
        if tag == "meta" and vals.get("name", "").lower() == "description":
            self.description = vals.get("content", "")[:300]
        if tag == "link" and vals.get("rel", "").lower() == "canonical":
            self.canonical = bool(vals.get("href"))
    def handle_endtag(self, tag):
        if tag == "title":
            self._title = False
    def handle_data(self, data):
        if self._title:
            self.title += data[:250]

def _seo(body: dict) -> dict:
    markup = _limit_str(body, "html", 250_000, True)
    p = _SEO()
    p.feed(markup)
    checks = {"title": bool(p.title.strip()), "meta_description": bool(p.description),
              "one_h1": p.h1 == 1, "images_have_alt": p.images_without_alt == 0,
              "canonical": p.canonical}
    return {"ok": True, "checks": checks, "passed": sum(checks.values()),
            "total": len(checks), "title": p.title.strip()[:200],
            "images": p.images, "missing_alt": p.images_without_alt,
            "note": "Auditoría del HTML facilitado, no rastreo de una URL remota."}

def _svg(body: dict) -> dict:
    count = body.get("lines", 24)
    if type(count) is not int or not 4 <= count <= 100:
        raise SkillInvalid("lines debe ser entero entre 4 y 100.")
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">']
    for i in range(count):
        angle = 2 * math.pi * i / count
        x, y = round(400 + 300 * math.cos(angle), 2), round(400 + 300 * math.sin(angle), 2)
        parts.append('<line x1="400" y1="400" x2="' + str(x) + '" y2="' + str(y) +
                     '" stroke="#165D6F" stroke-width="3"/>')
    parts.append("</svg>")
    return {"ok": True, "mime": "image/svg+xml", "content": "".join(parts)}

def _carousel(body: dict) -> dict:
    items = body.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        raise SkillInvalid("items debe tener entre 1 y 20 elementos.")
    slides = []
    for item in items:
        if not isinstance(item, str) or len(item) > 180:
            raise SkillInvalid("Los textos del carrusel deben ser cortos.")
        slides.append('<section class="slide">' + html.escape(item) + "</section>")
    source = ('<!doctype html><html lang="es"><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width,initial-scale=1">'
              '<style>.gallery{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:1rem}'
              '.slide{scroll-snap-align:center;flex:0 0 80%;padding:3rem;border:1px solid #bbb;'
              'border-radius:1rem;font:1.3rem sans-serif}</style><main class="gallery">'
              + "".join(slides) + "</main></html>")
    return {"ok": True, "mime": "text/html", "content": source}

def execute(skill_id: str, body: dict) -> dict:
    if skill_id not in _ALL:
        raise SkillInvalid("Skill desconocida.")
    if skill_id not in _ADAPTERS:
        raise SkillUnavailable("No existe adaptador ejecutable para esta skill.")
    if not isinstance(body, dict):
        raise SkillInvalid("El cuerpo debe ser un objeto JSON.")
    mode = _ADAPTERS[skill_id][0]
    if mode == "sky_office":
        return {"ok": True, "endpoint": "/api/office/generate",
                "kind": _OFFICE_FORMATS[skill_id],
                "note": "Generación real disponible en la API Office existente; no incluye edición de formularios o macros."}
    if not _configured(skill_id) and mode not in {"seo", "svg", "carousel", "github", "scholarly"}:
        raise SkillUnavailable("Falta configurar el programa, credencial o motor de IA en SKY.")
    if mode == "seo":
        return _seo(body)
    if mode == "svg":
        return _svg(body)
    if mode == "carousel":
        return _carousel(body)
    if mode == "scholarly":
        from .sky_scholarly import search_papers
        q = _limit_str(body, "query", 250, True)
        return {"ok": True, "result": search_papers(q, provider="openalex", limit=5)}
    if mode == "github":
        from .github_reader import get_recent_commits
        repo = _limit_str(body, "repository", 110, True)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise SkillInvalid("Formato esperado: propietario/repositorio.")
        return get_recent_commits(repo, limit=5)
    if mode == "docker":
        try:
            completed = subprocess.run(["docker", "ps", "--format", "{{.ID}} {{.Status}} {{.Names}}"],
                                       capture_output=True, text=True, timeout=8, check=True)
            return {"ok": True, "containers": completed.stdout[:8000].splitlines()}
        except (OSError, subprocess.SubprocessError) as exc:
            raise SkillUnavailable("Docker no responde en este equipo.") from exc
    if mode == "supabase_rest":
        from .sky_supabase import fetch_table
        table = _limit_str(body, "table", 70, True)
        allow = set(x.strip() for x in _env("SKY_SKILL_SUPABASE_ALLOWED_TABLES").split(",") if x.strip())
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,60}", table) or table not in allow:
            raise SkillInvalid("Tabla no autorizada; usá SKY_SKILL_SUPABASE_ALLOWED_TABLES.")
        return {"ok": True, "rows": fetch_table(table, limit=20)}
    if mode == "llm":
        from .assistant import responder
        provider = _limit_str(body, "provider", 30) or "auto"
        if provider not in {"auto", "ollama", "openai", "anthropic", "gemini", "groq"}:
            raise SkillInvalid("Proveedor de IA desconocido.")
        input_text = _limit_str(body, "text", 5000, True)
        instruction = _LLM_RULES[skill_id] + "\nSolicitud: " + input_text
        try:
            answer, _ = responder(instruction, "SKY Skillpack", proveedor=provider)
            return {"ok": True, "text": str(answer)[:10000], "provider_requested": provider}
        except Exception as exc:
            raise SkillUnavailable("El motor de IA de SKY no pudo completar la solicitud.") from exc
    if mode == "notion":
        return _request("POST", "https://api.notion.com/v1/search", token=_env("NOTION_TOKEN"),
                        headers={"Notion-Version": "2022-06-28", "Content-Type": "application/json"},
                        payload={"page_size": 10})
    if mode == "linear":
        return _request("POST", "https://api.linear.app/graphql", token=_env("LINEAR_API_KEY"),
                        payload={"query": "{ viewer { id name } issues(first: 10) { nodes { id title } } }"})
    if mode == "hubspot":
        return _request("GET", "https://api.hubapi.com/crm/v3/objects/contacts?limit=10",
                        token=_env("HUBSPOT_ACCESS_TOKEN"))
    if mode == "typefully":
        social_id = _env("TYPEFULLY_SOCIAL_SET_ID")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,70}", social_id):
            raise SkillInvalid("Social set ID inválido.")
        return _request("GET", "https://api.typefully.com/v2/social-sets/" + social_id + "/drafts?limit=10",
                        token=_env("TYPEFULLY_API_KEY"))
    if mode == "vercel":
        return _request("GET", "https://api.vercel.com/v6/deployments?limit=10",
                        token=_env("VERCEL_TOKEN"))
    if mode == "firecrawl":
        target = _limit_str(body, "url", 1200, True)
        parsed = urlparse(target)
        allow = set(x.strip().lower() for x in _env("SKY_FIRECRAWL_ALLOWED_HOSTS").split(",") if x.strip())
        if (parsed.scheme != "https" or not parsed.hostname or parsed.hostname.lower() not in allow
                or parsed.username or parsed.password or parsed.port):
            raise SkillInvalid("Dominio no autorizado para Firecrawl; configurá SKY_FIRECRAWL_ALLOWED_HOSTS.")
        return _request("POST", "https://api.firecrawl.dev/v2/scrape",
                        token=_env("FIRECRAWL_API_KEY"), payload={"url": target, "formats": ["markdown"]})
    raise SkillUnavailable("Operación no disponible.")


def interpretar(texto: str) -> dict | None:
    """Acceso por VOZ y TEXTO al mismo ejecutor; limitado a operaciones sin efectos.

    La orden debe nombrar explícitamente la skill para no interceptar
    conversaciones normales. Servicios privados requieren la API autenticada.
    """
    if not isinstance(texto, str) or len(texto) > 6000:
        return None
    normalized = texto.casefold().strip()
    if re.search(r"\b(?:que|qué|mostrar|muestra|listar|lista)\b.*\bskills externas\b", normalized):
        summary = catalogue()
        ready = [x["id"] for x in summary["skills"] if x["status"] in
                 {"adapter_ready_unverified", "available_via_office_api"}]
        return {"tipo": "respuesta", "proveedor": "sky-skillpack",
                "mensaje": "Tengo " + str(len(ready)) +
                           " adaptadores locales preparados, pero la ejecución externa exige configuración y prueba. " +
                           ", ".join(ready[:12]) + "."}
    match = re.search(r"\b(?:ejecuta|utiliza|usa)\s+(?:la\s+)?skill\s+([a-z0-9-]{3,80})\s*:\s*(.+)$",
                      normalized, flags=re.DOTALL)
    if not match:
        return None
    skill = match.group(1)
    prompt = texto[-len(match.group(2)):].strip()
    safe = {"scientific-researcher": "query", "github-connector": "repository",
            "seo-audit": "html", "humanizer": "text", "copywriting-pro": "text",
            "marketing-skills": "text", "ad-angle-research": "text", "internal-comms": "text"}
    if skill not in safe:
        return {"tipo": "error", "proveedor": "sky-skillpack",
                "mensaje": "Esta operación requiere usar el endpoint privado del Skillpack y sus permisos."}
    try:
        result = execute(skill, {safe[skill]: prompt})
        if result.get("ok") is False:
            return {"tipo": "error", "proveedor": "sky-skillpack",
                    "mensaje": "El proveedor no confirmó una ejecución correcta."}
        if isinstance(result.get("text"), str):
            msg = result["text"][:6000]
        else:
            msg = json.dumps(result, ensure_ascii=False)[:6000]
        return {"tipo": "respuesta", "proveedor": "sky-skillpack", "mensaje": msg}
    except (SkillInvalid, SkillUnavailable, RuntimeError, ValueError) as exc:
        return {"tipo": "error", "proveedor": "sky-skillpack", "mensaje": str(exc)[:240]}
