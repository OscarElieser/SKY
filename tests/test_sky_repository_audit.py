"""Regression tests for the read-only SKY repository audit."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_repository_layout.py"
spec = importlib.util.spec_from_file_location("sky_layout_audit", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_identifies_identical_files_and_imports(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "same.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "b" / "same.py").write_text("import os\n", encoding="utf-8")
    report = module.inventory(tmp_path)
    assert report["files_scanned"] == 2
    assert len(report["exact_duplicate_groups"]) == 1
    assert len(report["same_filename_groups"]) == 1
    assert {item["module"] for item in report["python_imports"]} == {"os"}


def test_ignores_generated_build_outputs(tmp_path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "generated.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "real.py").write_text("import json\n", encoding="utf-8")
    report = module.inventory(tmp_path)
    assert report["files_scanned"] == 1
    assert report["python_imports"] == [{"source": "real.py", "module": "json"}]
