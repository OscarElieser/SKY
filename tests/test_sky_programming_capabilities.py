"""SKY developer multilanguage: read-only truthful runtime report & syntax checks."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from neural_core import sky_programming_capabilities as dev


def test_catalogo_amplio_sin_confundir_generacion_con_ejecucion():
    assert len(dev.PROFILES) >= 50
    assert {"Python", "C++", "C#", "COBOL", "Fortran", "Rust", "Dart",
            "Kotlin", "Swift", "Go", "R", "Julia", "Assembly", "Solidity"}.issubset(dev.PROFILES)


@pytest.mark.parametrize("prompt,expected,excluded", [
    ("Programá en C++ y C# usando Kotlin", {"C++", "C#", "Kotlin"}, {"C"}),
    ("Migrá JavaScript a TypeScript", {"JavaScript", "TypeScript"}, {"Java"}),
    ("Necesito un servicio en Go y otro en Rust", {"Go", "Rust"}, {"C"}),
    ("Contabilidad en COBOL y análisis con R", {"COBOL", "R"}, set()),
    ("Crear un contrato con Solidity y scripts PowerShell", {"Solidity", "PowerShell"}, set()),
])
def test_deteccion_real_de_lenguajes(prompt, expected, excluded):
    found = set(dev.detect_languages(prompt))
    assert expected.issubset(found), found
    assert not (excluded & found)


def test_catalogo_no_afirma_compilacion_ni_certificacion(monkeypatch):
    monkeypatch.setattr(dev.shutil, "which", lambda x: "/virtual/python3" if x == "python3" else None)
    yes = dev.toolchain_status("Python")
    assert yes["checks"][0]["toolchain_detected"] is True
    assert yes["checks"][0]["state"] == "installed_unverified"
    assert yes["checks"][0]["source_compiled_or_run"] is False
    assert yes["code_execution_performed"] is False
    assert yes["global_all_languages_certified"] is False
    assert "/virtual/" not in str(yes)
    missing = dev.toolchain_status("C++")
    assert missing["checks"][0]["state"] == "needs_toolchain_installation"
    proprietary = dev.toolchain_status("ABAP")
    assert proprietary["checks"][0]["state"] == "requires_specialized_validator_or_service"


def test_validacion_python_comprueba_sintaxis_sin_ejecutar():
    result = dev.validate_source("python", "raise RuntimeError('no ejecutar esto')\n")
    assert result["syntax_checked"] and result["syntax_valid"]
    assert result["code_executed"] is False
    assert result["compile_verified"] is False
    broken = dev.validate_source("Python", "def incompleta(:\n    pass")
    assert broken["syntax_checked"] and broken["syntax_valid"] is False


def test_json_estricto_y_js_no_simulado():
    good = dev.validate_source("JSON", '{"items":[1,2,3]}')
    assert good["syntax_valid"] is True and good["code_executed"] is False
    invalid = dev.validate_source("JSON", '{"items": [1,]}')
    assert invalid["syntax_valid"] is False
    js = dev.validate_source("JavaScript", "const a = ;")
    assert js["syntax_checked"] is False and js["syntax_valid"] is None


@pytest.mark.parametrize("language,source", [
    ("falso", "x"),
    ("Python", ""),
    ("Python", "x" * 50_001),
    ("Python", "print(1)\x00"),
])
def test_no_acepta_entradas_invalidas(language, source):
    with pytest.raises(ValueError):
        dev.validate_source(language, source)


def test_api_protegida_y_verificacion_sin_ejecucion(monkeypatch):
    monkeypatch.setenv("SKY_API_KEY", "sky-developer-test-private-key-2026")
    from metaverse.api import app
    from metaverse.api import api_token
    with TestClient(app) as client:
        assert client.get("/api/developer/toolchains?language=Python").status_code in (401, 403)
        headers={"X-SKY-KEY": api_token()}
        a=client.get("/api/developer/toolchains?language=Python",headers=headers)
        assert a.status_code == 200
        assert a.json()["global_all_languages_certified"] is False
        b=client.post("/api/developer/syntax-check",json={
            "language":"Python","code":"def hello():\n    return 42"},headers=headers)
        assert b.status_code == 200
        assert b.json()["syntax_valid"] is True
        assert b.json()["code_executed"] is False
        c=client.post("/api/developer/syntax-check",json={
            "language":"Python","code":"raise Exception()"},headers=headers)
        assert c.status_code == 200
        assert c.json()["syntax_valid"] is True
        assert client.get("/api/developer/toolchains?language=Desconocido",headers=headers).status_code == 422
