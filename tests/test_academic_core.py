"""Pruebas unitarias para SKY Universal Knowledge & Education Engine (SKY-ACADEMIC-CORE)."""
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from neural_core.academic_core import (
    load_academic_prompt,
    is_academic_task,
    detect_engines,
    detect_level,
    academic_instructions,
    analyze_academic_request,
    list_academic_engines,
    ACADEMIC_FILE
)
from metaverse.api import app

def test_academic_core_knowledge_file():
    """Verifica que el archivo maestro académico exista con metadatos y autoría."""
    assert ACADEMIC_FILE.is_file()
    content = load_academic_prompt()
    assert "SKY Universal Knowledge & Education Engine" in content
    assert "Oscar Elieser Chamorro Guzmán" in content
    assert "SKY-MATH" in content
    assert "SKY-APA" in content
    assert "SKY-EDU" in content

def test_detect_engines():
    """Verifica la activación de motores según la materia consultada."""
    assert "SKY-MATH" in detect_engines("resuelve esta ecuación cuadrática y calcula la derivada")
    assert "SKY-APA" in detect_engines("cómo citar un libro según normas APA 7ma edición")
    assert "SKY-CHEM" in detect_engines("balanceo de ecuaciones químicas y estequiometría")
    assert "SKY-AUTO" in detect_engines("diagnóstico de inyección y bujías en motor de combustión")
    assert "SKY-BUILD" in detect_engines("cálculo de materiales y cubicación de concreto para cimientos")

def test_detect_level():
    """Verifica la detección automática del nivel educativo."""
    assert detect_level("actividades de motricidad para niños de preescolar e inicial") == "inicial"
    assert detect_level("ejercicios de fracciones para primaria de cuarto grado") == "primaria"
    assert detect_level("taller práctico de soldadura en formación técnica de inatec") == "tecnico"
    assert detect_level("tesis de maestría con análisis epistemológico para doctorado") == "posgrado"

def test_academic_instructions():
    """Verifica la inyección modular de directivas pedagógicas y de rigor científico."""
    inst = academic_instructions("matemáticas", "calcular integral definida paso a paso")
    assert "SKY UNIVERSAL KNOWLEDGE & EDUCATION ENGINE" in inst
    assert "SKY-MATH" in inst
    assert len(inst) <= 6000

    non_acad = academic_instructions("General", "receta de pastel de chocolate")
    assert non_acad == ""

def test_academic_api_endpoints():
    """Verifica los endpoints de la API de educación y conocimiento."""
    client = TestClient(app)

    # 1. Lista de motores
    r_eng = client.get("/api/academic/engines")
    assert r_eng.status_code == 200
    d_eng = r_eng.json()
    assert d_eng["ok"] is True
    assert len(d_eng["engines"]) >= 20

    # 2. Análisis pedagógico
    r_ana = client.post("/api/academic/analyze", json={"prompt": "plan de clase de ciencias para primaria con rubrica de evaluacion"})
    assert r_ana.status_code == 200
    d_ana = r_ana.json()
    assert d_ana["ok"] is True
    assert d_ana["analysis"]["is_academic"] is True
    assert d_ana["analysis"]["educational_level"] == "primaria"
    assert d_ana["analysis"]["pedagogical_mode"] == "Evaluador"
