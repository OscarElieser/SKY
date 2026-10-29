"""Academic project planning for SKY API: thesis, dissertation and research reports.

Produces a transparent structured plan, not fabricated research, citations or
a falsely completed thesis. Existing SKY model providers can use this plan.
"""
from __future__ import annotations
import re

SECTIONS = (
    ("portada", "Portada y datos institucionales"),
    ("resumen", "Resumen y palabras clave"),
    ("introduccion", "Introducción y planteamiento del problema"),
    ("objetivos", "Objetivo general y objetivos específicos"),
    ("marco_teorico", "Marco teórico y antecedentes verificables"),
    ("metodologia", "Metodología, población, muestra e instrumentos"),
    ("resultados", "Resultados y análisis de datos"),
    ("discusion", "Discusión y contraste con la literatura"),
    ("conclusiones", "Conclusiones y recomendaciones"),
    ("referencias", "Referencias bibliográficas verificadas"),
    ("anexos", "Anexos e instrumentos"),
)


def plan_academico(topic: str, instructions: str, *, degree: str = "licenciatura",
                   citation_style: str = "APA 7", language: str = "es") -> dict:
    if not isinstance(topic, str) or not 5 <= len(topic.strip()) <= 500:
        raise ValueError("El tema debe contener entre 5 y 500 caracteres")
    if not isinstance(instructions, str) or not 10 <= len(instructions.strip()) <= 10000:
        raise ValueError("Las instrucciones deben contener entre 10 y 10000 caracteres")
    if degree not in {"tecnico", "licenciatura", "maestria", "doctorado"}:
        raise ValueError("Nivel académico no admitido")
    if citation_style not in {"APA 7", "IEEE", "Vancouver", "Chicago", "MLA"}:
        raise ValueError("Estilo bibliográfico no admitido")
    if not re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", language):
        raise ValueError("Código de idioma inválido")
    return {
        "kind": "academic_research_project",
        "topic": topic.strip(),
        "instructions": instructions.strip(),
        "degree": degree,
        "citation_style": citation_style,
        "language": language,
        "roles": ["director_academico", "investigador", "metodologo",
                  "redactor", "revisor_de_fuentes", "editor"],
        "sections": [{"id": key, "title": title, "status": "pending"}
                     for key, title in SECTIONS],
        "quality_requirements": [
            "Respetar instrucciones, institución, extensión y formato indicados",
            "Verificar fuentes primarias y DOI antes de citarlos",
            "No inventar bibliografía, datos, encuestas ni resultados",
            "Distinguir hipótesis, evidencia y análisis",
            "Revisar coherencia entre objetivos, método y conclusiones",
            "Solicitar datos indispensables cuando no se proporcionen",
        ],
        "status": "planned",
        "generated_document": False,
    }
