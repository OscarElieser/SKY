"""SKY academic project planner tests."""
import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "neural_core" / "sky_academic_projects.py"
spec = importlib.util.spec_from_file_location("sky_academic_projects", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_thesis_plan_has_verification_and_roles():
    result = module.plan_academico("Turismo sostenible en Nicaragua",
                                  "Redactar según normas APA con metodología mixta.",
                                  degree="maestria")
    assert result["status"] == "planned"
    assert result["generated_document"] is False
    assert "revisor_de_fuentes" in result["roles"]
    assert any(s["id"] == "metodologia" for s in result["sections"])


def test_rejects_missing_instructions():
    with pytest.raises(ValueError):
        module.plan_academico("Turismo sostenible", "breve")


def test_academic_api_is_authenticated():
    source = (ROOT / "metaverse" / "academic_projects_api.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "dependencies=[Depends(require_key)]" in source
    api = (ROOT / "metaverse" / "api.py").read_text(encoding="utf-8")
    assert "app.include_router(sky_academic_projects_router)" in api
