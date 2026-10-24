"""Pruebas unitarias para SKY Developer Intelligence Core (SKY-DEVELOPER-CORE)."""
from pathlib import Path
import json
import pytest
from starlette.testclient import TestClient

from neural_core.developer_core import (
    load_master_prompt,
    is_developer_task,
    developer_instructions,
    analyze_tech_stack,
    CORE_FILE
)
from neural_core.github_reader import (
    load_sources_catalog,
    list_reference_repositories,
    find_repository_entry
)
from metaverse.api import app


def _llave_dueno():
    """SENTINEL v12.5: la API es privada; las pruebas usan la llave del dueño como lo hace la interfaz."""
    from metaverse.api import api_token
    return api_token()


def test_developer_core_knowledge_file():
    """Verifica que el archivo maestro de conocimiento tecnológico exista y esté completo."""
    assert CORE_FILE.is_file()
    content = load_master_prompt()
    assert "SKY-DEVELOPER-CORE" in content
    assert "Oscar Elieser Chamorro Guzmán" in content
    assert "1. IDENTIDAD Y MISIÓN CENTRAL" in content
    assert "25. DIRECTIVA CENTRAL DE EJECUCIÓN" in content

def test_sources_catalog():
    """Verifica que el catálogo de repositorios de referencia esté cargado y contenga las fuentes oficiales."""
    catalog = load_sources_catalog()
    assert catalog.get("mode") == "read_only"
    repos = list_reference_repositories()
    names = [r["name"] for r in repos]
    assert "SKY" in names
    assert "Python" in names
    assert "Flutter" in names
    assert "Supabase" in names
    assert "FastAPI" in names

    found = find_repository_entry("flutter")
    assert found is not None
    assert found["repository"] == "flutter/flutter"

def test_is_developer_task_detection():
    """Verifica que se detecten correctamente tareas y preguntas sobre programación y software."""
    assert is_developer_task("programación", "hola mundo")
    assert is_developer_task("General", "creame una app con Flutter y Supabase")
    assert is_developer_task("General", "cómo soluciono este error de Python en FastAPI")
    assert is_developer_task("código", "")
    assert not is_developer_task("General", "¿qué clima hace hoy en Managua?")

def test_developer_instructions_injection():
    """Verifica que se generen instrucciones especializadas acordes al contexto tecnológico."""
    # Para consulta de programación
    inst = developer_instructions("programación", "construir arquitectura limpia en Python")
    assert "SKY DEVELOPER INTELLIGENCE CORE" in inst
    assert "IDENTIDAD Y MISIÓN CENTRAL" in inst
    assert "DIRECTIVA CENTRAL DE EJECUCIÓN" in inst
    assert len(inst) <= 6000

    # Para consulta ajena a desarrollo
    non_dev = developer_instructions("General", "receta de cocina tradicional")
    assert non_dev == ""

def test_analyze_tech_stack():
    """Verifica el análisis automático de tecnologías y tipos de tarea."""
    analysis = analyze_tech_stack("Crear una aplicación móvil en Flutter con backend FastAPI y base de datos PostgreSQL")
    assert "Flutter" in analysis["frameworks"]
    assert "Fastapi" in analysis["frameworks"] or "FastAPI" in analysis["frameworks"]
    assert "Postgresql" in analysis["frameworks"]
    assert analysis["task_type"] == "Creación de Proyecto"
    assert analysis["is_dev"] is True

def test_developer_api_endpoints():
    """Verifica los endpoints de API del módulo desarrollador."""
    client = TestClient(app, headers={'X-SKY-KEY': _llave_dueno()})
    
    # 1. Catálogo de fuentes
    r_sources = client.get("/api/developer/sources")
    assert r_sources.status_code == 200
    data_sources = r_sources.json()
    assert data_sources["ok"] is True
    assert len(data_sources["sources"]) >= 5

    # 2. Análisis de stack
    r_analyze = client.post("/api/developer/analyze", json={"prompt": "arreglar bug en react con typescript"})
    assert r_analyze.status_code == 200
    data_analyze = r_analyze.json()
    assert data_analyze["ok"] is True
    assert data_analyze["analysis"]["task_type"] == "Depuración y Corrección"
