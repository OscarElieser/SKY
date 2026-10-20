"""Pruebas unitarias para Codebase Indexer y Code Intelligence de SKY v11.1."""
from pathlib import Path
import pytest
from neural_core.codebase_indexer import (
    analyze_directory_structure,
    extract_python_symbols,
    search_symbols_in_directory,
    detect_codebase_frameworks
)
from neural_core.github_reader import (
    list_reference_repositories,
    find_repository_entry
)

ROOT = Path(__file__).resolve().parents[1]

def test_analyze_directory_structure():
    """Verifica que el indexador escanee directorios, cuente archivos y detecte lenguajes."""
    res = analyze_directory_structure(ROOT, max_depth=2)
    assert res["total_files"] > 10
    assert res["total_directories"] > 0
    assert "Python" in res["language_distribution"]
    assert any("requirements" in cf.lower() for cf in res["config_files"])

def test_extract_python_symbols():
    """Verifica la extracción de funciones, imports y clases vía AST de Python."""
    target_file = ROOT / "neural_core" / "developer_core.py"
    res = extract_python_symbols(target_file)
    assert res["file"] == "developer_core.py"
    assert res["total_functions"] >= 4
    fn_names = [f["name"] for f in res["functions"]]
    assert "developer_instructions" in fn_names
    assert "is_developer_task" in fn_names
    assert "analyze_tech_stack" in fn_names

def test_search_symbols_in_directory():
    """Verifica la búsqueda de símbolos en el árbol de archivos."""
    matches = search_symbols_in_directory(ROOT / "neural_core", "developer_instructions")
    assert len(matches) >= 1
    m0 = matches[0]
    assert m0["name"] == "developer_instructions"
    assert "developer_core.py" in m0["file"]

def test_detect_codebase_frameworks():
    """Verifica la detección automática de frameworks y herramientas."""
    fws = detect_codebase_frameworks(ROOT)
    assert "FastAPI" in fws or "Pytest" in fws

def test_github_reader_lookup():
    """Verifica que github_reader encuentre repositorios de referencia."""
    sources = list_reference_repositories()
    assert len(sources) >= 5
    sky_repo = find_repository_entry("SKY")
    assert sky_repo is not None
    assert sky_repo["repository"] == "OscarElieser/SKY"
