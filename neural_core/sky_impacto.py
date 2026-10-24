"""SKY Impacto: docencia, investigación verificable e innovación.

Motor determinista de planificación (NO confundir con investigación ejecutada).
Sin acceso a documentos privados, sin tareas en segundo plano y sin promesas de premios.
Sólo consulta páginas HTTPS del catálogo explícito a petición del usuario.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import re
import ssl
from urllib import request, parse, error

from neural_core.academic_core import detect_level

SOURCES = {
    "mined": ("MINED", "educacion", "Nicaragua", "https://www.mined.gob.ni/"),
    "inatec": ("INATEC", "educacion", "Nicaragua", "https://www.tecnacional.edu.ni/"),
    "intur": ("INTUR", "turismo", "Nicaragua", "https://www.intur.gob.ni/"),
    "marena": ("MARENA", "ambiente", "Nicaragua", "https://www.marena.gob.ni/"),
    "mific": ("MIFIC", "economia", "Nicaragua", "https://www.mific.gob.ni/"),
    "bcn": ("Banco Central de Nicaragua", "economia", "Nicaragua", "https://www.bcn.gob.ni/"),
    "inide": ("INIDE", "estadistica", "Nicaragua", "https://www.inide.gob.ni/"),
    "unesco": ("UNESCO", "educacion", "Global", "https://www.unesco.org/"),
    "uis": ("UNESCO UIS", "estadistica", "Global", "https://uis.unesco.org/"),
    "onu": ("Naciones Unidas", "desarrollo", "Global", "https://www.un.org/"),
    "un_data": ("UNdata", "estadistica", "Global", "https://data.un.org/"),
    "worldbank": ("Banco Mundial Datos", "desarrollo", "Global", "https://data.worldbank.org/"),
    "cepal": ("CEPAL", "desarrollo", "Latinoamérica", "https://www.cepal.org/"),
    "who": ("OMS", "salud", "Global", "https://www.who.int/"),
    "fao": ("FAO", "agricultura", "Global", "https://www.fao.org/"),
    "europarl": ("Parlamento Europeo", "legislacion", "Europa", "https://www.europarl.europa.eu/"),
    "mit": ("MIT OpenCourseWare", "educacion", "Global", "https://ocw.mit.edu/"),
    "harvard": ("Harvard University", "investigacion", "Global", "https://www.harvard.edu/"),
    "stanford": ("Stanford University", "investigacion", "Global", "https://www.stanford.edu/"),
}
DOMAINS = {parse.urlsplit(v[3]).hostname for v in SOURCES.values()}
ALLOWED_DOCS = {"ensayo", "monografia", "tesis", "articulo", "protocolo", "informe", "diagnostico", "proyecto"}
LESSON_STAGES = ("Activación de conocimientos previos", "Explicación guiada",
                 "Demostración y ejemplo", "Práctica participativa",
                 "Comprobación de aprendizaje", "Retroalimentación y cierre")
DELIVERABLES = ("Árbol de problemas", "Objetivos SMART", "Hipótesis verificables",
                "Propuesta de valor", "Buyer persona", "Mapa de empatía",
                "Modelo Canvas", "Matriz impacto-viabilidad", "MVP y pruebas",
                "Presupuesto", "Pitch", "Defensa ante el jurado")
CATEGORIES = {
    "educacion": ("mined", "inatec", "unesco", "uis"),
    "turismo": ("intur", "unesco"),
    "ambiente": ("marena", "fao", "onu"),
    "economia": ("mific", "bcn", "worldbank", "cepal"),
    "transporte": ("inide", "worldbank", "cepal"),
    "salud": ("who", "onu"),
    "agricultura": ("fao", "marena"),
    "estadistica": ("inide", "un_data", "worldbank"),
    "cultura": ("intur", "unesco"),
    "legislacion": ("europarl", "onu"),
    "investigacion": ("mit", "harvard", "stanford", "unesco"),
    "desarrollo": ("onu", "cepal", "worldbank"),
}


def _clean(value: str, length: int = 250) -> str:
    if not isinstance(value, str):
        raise ValueError("Se requiere texto.")
    value = re.sub(r"\\s+", " ", value).strip()
    if not value or len(value) > length:
        raise ValueError(f"El texto debe tener entre 1 y {length} caracteres.")
    return value


def _unaccent(text: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


def classify(text: str) -> str:
    t = _unaccent(text)
    words = {
        "educacion": ("escuela", "docente", "clase", "aprendizaje", "educacion"),
        "turismo": ("turismo", "destino", "visitante", "ruta turistica"),
        "ambiente": ("ambiental", "contaminacion", "residuo", "clima", "reciclaje"),
        "transporte": ("transporte", "trafico", "movilidad", "buses"),
        "salud": ("salud", "medicina", "hospital"),
        "agricultura": ("agricultura", "cultivo", "agricola"),
        "economia": ("economia", "emprendimiento", "empleo", "comercio"),
        "cultura": ("cultura", "patrimonio", "arte", "musica"),
        "legislacion": ("ley", "derecho", "legislacion"),
        "estadistica": ("censo", "estadistica", "poblacion"),
    }
    for category, kws in words.items():
        if any(w in t for w in kws):
            return category
    return "desarrollo"


def list_sources(category: str = "") -> list[dict]:
    if category and category not in CATEGORIES:
        raise ValueError("Categoría no reconocida.")
    keys = CATEGORIES[category] if category else tuple(SOURCES)
    return [dict(id=k, name=SOURCES[k][0], category=SOURCES[k][1],
                 region=SOURCES[k][2], url=SOURCES[k][3],
                 connection="catalogued_not_connected") for k in keys]


class _SafeRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname not in DOMAINS or parsed.port not in (None, 443) or parsed.username:
            raise ValueError("Redirección fuera de las fuentes autorizadas.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def consult_source(source_id: str, *, timeout: float = 8.0) -> dict:
    """Lectura bajo petición de URL precargada; sin URL externa suministrada por usuario.

    El catálogo no equivale a conectividad. Los errores se devuelven explícitos.
    """
    if source_id not in SOURCES:
        raise ValueError("Fuente no autorizada.")
    name, category, region, url = SOURCES[source_id]
    outcome = dict(id=source_id, name=name, url=url, consulted_at=datetime.now(timezone.utc).isoformat())
    opener = request.build_opener(_SafeRedirect, request.HTTPSHandler(context=ssl.create_default_context()))
    req = request.Request(url, headers={"User-Agent": "SKY-Impacto/1.0 (research; explicit read-only access)",
                                        "Accept": "text/html,text/plain,application/json"})
    try:
        with opener.open(req, timeout=min(12.0, max(1.0, timeout))) as response:
            mime = response.headers.get_content_type()
            if mime not in ("text/html", "text/plain", "application/json"):
                return {**outcome, "ok": False, "error": "Formato de contenido no compatible."}
            raw = response.read(100001)
            if len(raw) > 100000:
                return {**outcome, "ok": False, "error": "Documento demasiado grande para esta consulta limitada."}
            charset = response.headers.get_content_charset() or "utf-8"
            content = raw.decode(charset, errors="replace")
            if mime == "text/html":
                content = re.sub(r"<(script|style|nav|footer)\\b[^>]*>.*?</\\1>", " ", content,
                                 flags=re.IGNORECASE | re.DOTALL)
                content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\\s+", " ", unescape(content)).strip()
            return {**outcome, "ok": True, "content": content[:6500],
                    "truncated": len(content) > 6500, "final_url": response.geturl(),
                    "note": "Extracto; no representa toda la fuente ni valida automáticamente sus afirmaciones."}
    except (OSError, ValueError, UnicodeError, error.URLError) as exc:
        return {**outcome, "ok": False, "error": type(exc).__name__ + ": " + str(exc)[:160]}


def research_plan(topic: str, kind: str = "informe", category: str = "") -> dict:
    topic = _clean(topic, 500)
    kind = _unaccent(_clean(kind, 30))
    if kind not in ALLOWED_DOCS:
        raise ValueError("Tipo de documento no admitido.")
    category = category or classify(topic)
    sources = list_sources(category)
    structure = ["Problema y contexto", "Preguntas y objetivos", "Antecedentes documentados",
                 "Metodología y criterios de evidencia", "Análisis y resultados",
                 "Limitaciones", "Conclusiones", "Referencias y anexos"]
    if kind in ("tesis", "monografia", "protocolo"):
        structure.insert(3, "Marco teórico y conceptual")
        structure.insert(5, "Diseño de recolección y análisis de datos")
    if kind == "ensayo":
        structure = ["Tesis argumental", "Contexto y fuentes", "Argumentos contrastados",
                     "Contraargumentos", "Conclusión", "Referencias"]
    return {
        "topic": topic, "document_type": kind, "category": category,
        "research_questions": [f"¿Cuál es la magnitud verificable del problema relacionado con {topic}?",
                               "¿Qué estrategias existentes cuentan con resultados medidos?",
                               "¿Qué propuesta puede evaluarse de forma ética, viable y sostenible?"],
        "sections": structure, "sources_to_consult": sources,
        "evidence_requirements": ["Citas originales localizables", "Fecha y vigencia de datos",
                                  "Métodos reproducibles", "Contraste de fuentes",
                                  "Identificación de incertidumbres"],
        "status": "plan_only", "verified_research_completed": False,
        "notice": "No se han consultado fuentes ni generado resultados científicos."
    }


def lesson_plan(topic: str, level: str = "", minutes: int = 45,
                objective: str = "") -> dict:
    topic = _clean(topic, 300)
    if level:
        level = _unaccent(_clean(level, 40))
    else:
        level = detect_level(topic)
    allowed = {"inicial", "primaria", "secundaria", "tecnico", "universidad", "posgrado", "general"}
    if level not in allowed:
        raise ValueError("Nivel educativo no válido.")
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 10 <= minutes <= 240:
        raise ValueError("La duración debe estar entre 10 y 240 minutos.")
    objective = _clean(objective, 500) if objective else f"Comprender y aplicar: {topic}"
    weights = (12, 23, 20, 25, 12, 8)
    allocations = [minutes * p // 100 for p in weights]
    allocations[-1] += minutes - sum(allocations)
    methods = {
        "inicial": "Juego, objetos concretos, cuentos, exploración y preguntas breves",
        "primaria": "Ejemplos cotidianos, trabajo guiado y práctica visual",
        "secundaria": "Indagación, ejemplos graduados y aplicación colaborativa",
        "tecnico": "Demostración práctica, seguridad y procedimiento verificable",
        "universidad": "Problemas aplicados, bibliografía y discusión crítica",
        "posgrado": "Evidencia científica, evaluación crítica y debate metodológico",
        "general": "Diagnóstico, explicación graduada y práctica guiada",
    }
    stages = [{"step": i + 1, "name": name, "duration_minutes": allocations[i],
               "voice_instruction": f"Explicá {topic} durante la etapa «{name}» usando {methods[level].lower()}. "
                                    "Hacé una pregunta, escuchá al estudiante y no avancés sin verificar su respuesta."}
              for i, name in enumerate(LESSON_STAGES)]
    return dict(topic=topic, level=level, objective=objective, minutes=minutes,
                methodology=methods[level], steps=stages, current_step=1,
                assessment="Usar preguntas y evidencias reales de desempeño, sin inventar calificaciones.",
                delivery="Disponible para voz y texto mediante los motores ya instalados; "
                         "la reproducción de audio depende del dispositivo.")


def lesson_step(plan: dict, step: int, student_response: str = "") -> dict:
    """Turno guiado; no presume evaluar automáticamente respuestas libres."""
    steps = plan.get("steps") if isinstance(plan, dict) else None
    if not isinstance(steps, list) or isinstance(step, bool) or not isinstance(step, int) or not 1 <= step <= len(steps):
        raise ValueError("Plan o paso inválido.")
    stage = steps[step - 1]
    if not isinstance(stage, dict) or "voice_instruction" not in stage:
        raise ValueError("Etapa no válida.")
    response = student_response.strip()[:1500] if isinstance(student_response, str) else ""
    return {"step": step, "stage": stage, "student_response_received": bool(response),
            "needs_assessment": bool(response), "next_step": step + 1 if step < len(steps) else None,
            "instruction": ("Revisá la respuesta del estudiante de acuerdo con el objetivo; "
                            "si hay error, explicá nuevamente con otro ejemplo. "
                            "No afirmés comprensión sin evidencia. " + stage["voice_instruction"])}


def innovation_project(challenge: str, competition: str = "", audience: str = "") -> dict:
    challenge = _clean(challenge, 500)
    competition = _clean(competition, 120) if competition else "Por definir"
    audience = _clean(audience, 120) if audience else "Por investigar"
    category = classify(challenge)
    return {
        "challenge": challenge, "competition": competition, "audience": audience,
        "category": category, "status": "draft_requires_validation",
        "questions": ["¿Cuál es la población afectada y su necesidad comprobada?",
                      "¿Qué soluciones existen y qué limita sus resultados?",
                      "¿Qué reglamento, plazos y rúbrica oficial rigen la competencia?",
                      "¿Cómo se medirá el impacto en una prueba real?"],
        "proposal_canvas": {"problem": challenge, "customer_segments": audience,
                            "value_proposition": "Pendiente de validación con usuarios.",
                            "channels": "Pendiente de investigación.",
                            "customer_relationships": "Pendiente de validación.",
                            "key_activities": "Prototipar, medir, validar y mejorar.",
                            "key_resources": "Pendiente de presupuesto.",
                            "key_partners": "Pendiente de acuerdos verificables.",
                            "cost_structure": "Pendiente de cotizaciones reales.",
                            "revenue_streams": "Pendiente de modelo sostenible."},
        "deliverables": list(DELIVERABLES),
        "source_recommendations": list_sources(category),
        "pitch_structure": ["Problema y evidencia", "Usuario y oportunidad",
                            "Solución y diferenciación", "Demostración del MVP",
                            "Impacto medible y viabilidad", "Solicitud o cierre"],
        "competition_result": "No predecible: se persigue el primer lugar sin garantizarlo.",
    }


def judge_project(scores: dict, rubric: dict) -> dict:
    """Sólo puntúa entradas y ponderaciones explícitas, no supone una rúbrica oficial."""
    if not isinstance(rubric, dict) or not rubric:
        raise ValueError("Se necesita la rúbrica explícita del concurso.")
    if not isinstance(scores, dict):
        raise ValueError("Puntuaciones inválidas.")
    if set(rubric) != set(scores):
        raise ValueError("Las puntuaciones deben cubrir exactamente la rúbrica.")
    if len(rubric) > 20:
        raise ValueError("Demasiados criterios.")
    total_w = 0.
    result = []
    for name, weight in rubric.items():
        if not isinstance(name, str) or not 1 <= len(name) <= 70:
            raise ValueError("Nombre de criterio inválido.")
        score = scores[name]
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or weight <= 0:
            raise ValueError("Pesos inválidos.")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
            raise ValueError("Las puntuaciones deben estar entre 0 y 10.")
        total_w += weight
        result.append({"criterion": name, "score": score, "weight": weight})
    if abs(total_w - 100.0) > 0.01:
        raise ValueError("Los pesos deben sumar 100.")
    score_total = sum(x["score"] * x["weight"] / 100 for x in result)
    return {"score_out_of_10": round(score_total, 2), "criteria": result,
            "weakest": sorted(result, key=lambda x: x["score"])[:3],
            "status": "user_supplied_scores_not_verified",
            "note": "Simulación interna: ni la rúbrica ni las puntuaciones se han validado contra la convocatoria."}


def verify_references(references: list[dict]) -> dict:
    """Audita metadatos, no verifica existencia remota de artículos o DOI."""
    if not isinstance(references, list) or len(references) > 50:
        raise ValueError("Se aceptan hasta 50 referencias.")
    results = []
    for item in references:
        if not isinstance(item, dict):
            raise ValueError("Referencia debe ser un objeto.")
        title = str(item.get("title") or "").strip()[:400]
        author = str(item.get("author") or "").strip()[:250]
        url = str(item.get("url") or "").strip()[:1000]
        year = item.get("year")
        valid_url = parse.urlsplit(url)
        issues = []
        if not title: issues.append("Falta título")
        if not author: issues.append("Falta autor o institución")
        if not isinstance(year, int) or isinstance(year, bool) or not 1800 <= year <= datetime.now(timezone.utc).year + 1:
            issues.append("Año ausente o inválido")
        if valid_url.scheme != "https" or not valid_url.hostname:
            issues.append("URL HTTPS de consulta ausente o inválida")
        results.append({"title": title, "metadata_complete": not issues, "issues": issues,
                        "existence_verified": False})
    return {"references": results, "total": len(results),
            "metadata_complete": sum(x["metadata_complete"] for x in results),
            "online_verification_performed": False,
            "note": "Un DOI o una URL con formato correcto no demuestra que la fuente exista."}


def impact_instructions(area: str, prompt: str) -> str:
    """Enruta solicitudes relevantes al modelo configurado de SKY, sin fingir consultas."""
    t = _unaccent((area + " " + prompt)[:4000])
    terms = ("tesis", "monografia", "ensayo", "investigacion", "rally", "hackathon",
             "innovatec", "pitch", "canvas", "propuesta de valor", "innovacion",
             "impartir clase", "plan de clase", "docente", "educacion inicial",
             "desarrollo de nicaragua", "concurso", "proyecto social")
    if not any(x in t for x in terms):
        return ""
    category = classify(prompt)
    names = ", ".join(s["name"] for s in list_sources(category))
    return (
        "SKY IMPACTO — MÓDULO DOCENTE, INVESTIGADOR Y DE INNOVACIÓN. "
        "La meta es aspirar al primer lugar en competencias, nunca garantizar una victoria. "
        "Ajustá rigurosamente la respuesta al objetivo del usuario. "
        "Si es clase, guiá por etapas, enseñá por voz cuando esté disponible, "
        "preguntá y adaptá la explicación a las respuestas reales. "
        "Si es tesis, ensayo o investigación, diferenciá hipótesis y evidencia, "
        "no inventés referencias, estadísticas, DOI ni autores; apoyá la integridad académica. "
        "Si es proyecto o concurso, investigá primero reglas y rúbrica oficiales, "
        "después propuesta de valor, Canvas, MVP, presupuesto, pitch y evaluación crítica. "
        "Fuentes recomendadas para consultar bajo petición (NO consultadas automáticamente): "
        + names + ". No afirmés conexión gubernamental ni lectura documental si no sucedió. "
        "Priorizá impacto verificable, derechos, seguridad e inclusión."
    )
