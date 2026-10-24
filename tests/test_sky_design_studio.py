"""SKY Design Studio: tested source generation, real library manifests and private API."""
from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from neural_core import sky_design_studio as studio


def test_relevant_domain_design_is_not_generic():
    cases = {
        "turismo": "Turismo sostenible en Nicaragua con rutas",
        "educacion": "Aula docente con cursos y aprendizaje",
        "salud": "Clínica de salud y bienestar",
        "finanzas": "Dashboard de finanzas para ahorro",
        "videojuegos": "Portal de videojuegos Unity",
        "cultura": "Museo cultura y patrimonio",
    }
    designs = [studio.create_design("Proyecto " + domain, prompt)
               for domain, prompt in cases.items()]
    assert {d["domain"] for d in designs} == set(cases)
    assert len({json.loads(d["files"]["src/config.json"])["subtitle"] for d in designs}) == len(cases)
    assert all(d["generated_sources_built_now"] is False for d in designs)
    assert all(d["device_visual_test_passed"] is False for d in designs)


def test_react_template_imports_real_libraries_and_exact_versions():
    d = studio.create_design("SKY Tourism", "Tourism and nature", platform="react")
    deps = d["libraries_declared"]
    assert set(("react","react-dom","motion","lucide-react","@fontsource/inter")).issubset(deps)
    assert all(not v.startswith("^") and not v.startswith("~") for v in deps.values())
    app = d["files"]["src/App.jsx"]
    entry = d["files"]["src/main.jsx"]
    assert "from 'motion/react'" in app
    assert "from 'lucide-react'" in app
    assert "useReducedMotion" in app
    assert "@fontsource/inter/400.css" in entry
    assert "prefers-reduced-motion" in d["files"]["src/style.css"]
    assert "aria-label" in app and "role=\"dialog\"" in app
    assert "npm run build" in d["commands_to_test_in_separate_approved_project"]
    assert d["files_written_on_owner_device"] is False


def test_flutter_template_has_real_animated_sdk_dependency():
    d = studio.create_design("SKY Turismo", "Turismo en reservas naturales", platform="flutter")
    assert d["libraries_declared"]["flutter_animate"] == "4.5.2"
    assert "flutter_animate" in d["files"]["lib/main.dart"]
    assert "flutter pub get" in d["commands_to_test_in_separate_approved_project"]
    assert d["compiled_on_owner_device"] is False
    assert d["files"]["lib/sky_config.dart"].count("skyColorPrimary") == 1


def test_determinism_and_brand_variation():
    a = studio.create_design("Ruta Uno", "viajes sostenibles por bosques", style="aurora",layout="immersive")
    b = studio.create_design("Ruta Uno", "viajes sostenibles por bosques", style="aurora",layout="immersive")
    c = studio.create_design("Ruta Dos", "cursos de formación para docentes", style="ember", layout="dashboard")
    assert a["files"] == b["files"]
    assert a["colors"] != c["colors"] or a["files"]["src/config.json"] != c["files"]["src/config.json"]
    assert a["layout"] == "immersive" and c["layout"] == "dashboard"
    assert c["style"] == "ember"


@pytest.mark.parametrize("kwargs", [
    {"title": "", "brief": "brief"},
    {"title": "Sky", "brief": ""},
    {"title": "Sky", "brief": "x"*501},
    {"title": "Sky", "brief": "brief", "platform": "shell"},
    {"title": "Sky", "brief": "brief", "style": "arbitrary-package"},
    {"title": "Sky", "brief": "brief", "domain": "secret-sector"},
    {"title": "Sky", "brief": "brief", "layout": "file:///etc/passwd"},
])
def test_invalid_designs_fail_closed(kwargs):
    with pytest.raises(studio.DesignInvalid):
        studio.create_design(**kwargs)


def test_user_content_is_data_not_react_or_dart_executable_code():
    title='</script><img src=x onerror=alert(1)>'
    brief='Ruta con "comillas", $variables y \n saltos especiales'
    react=studio.create_design(title, brief, platform="react")
    cfg=json.loads(react["files"]["src/config.json"])
    assert cfg["title"]==title and cfg["description"]==" ".join(brief.split())
    assert "onerror" not in react["files"]["src/App.jsx"]
    flutter=studio.create_design(title, brief, platform="flutter")
    dart=flutter["files"]["lib/sky_config.dart"]
    assert "\\$" in dart
    assert '\\\"' in dart
    assert "const skyTitle = \"" in dart


def test_zip_export_contains_only_safe_paths_and_manifest():
    d=studio.create_design("Escuela SKY", "educación digital", platform="react")
    payload=studio.design_archive(d)
    assert payload.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        paths=archive.namelist()
        assert "sky-design-react/src/App.jsx" in paths
        assert "sky-design-react/package.json" in paths
        assert "sky-design-react/SKY_MANIFEST.json" in paths
        assert not any(".." in name for name in paths)
        manifest=json.loads(archive.read("sky-design-react/SKY_MANIFEST.json"))
        assert manifest["compiled_on_owner_device"] is False


def test_api_is_private_and_returns_valid_zip(monkeypatch):
    monkeypatch.setenv("SKY_API_KEY", "sky-design-studio-private-token-for-ci-2026")
    from metaverse.api import app, api_token
    with TestClient(app) as client:
        unauth=client.get("/api/developer/design/capabilities")
        assert unauth.status_code in (401,403)
        headers={"X-SKY-KEY": api_token()}
        caps=client.get("/api/developer/design/capabilities",headers=headers)
        assert caps.status_code==200
        assert "react" in caps.json()["platforms"] and "flutter" in caps.json()["platforms"]
        args={"title":"Diseño futuro","brief":"plataforma de educación","platform":"react"}
        obj=client.post("/api/developer/design/create",headers=headers,json=args)
        assert obj.status_code==200, obj.text
        assert "src/App.jsx" in obj.json()["files"]
        no=client.post("/api/developer/design/create",headers=headers,json={
            "title":"Sky","brief":"demo","platform":"python-shell"})
        assert no.status_code==422
        zipr=client.post("/api/developer/design/download",headers=headers,json=args)
        assert zipr.status_code==200
        assert zipr.headers["content-type"]=="application/zip"
        assert zipr.headers["cache-control"]=="no-store"
        with zipfile.ZipFile(io.BytesIO(zipr.content)) as archive:
            assert "sky-design-react/src/config.json" in archive.namelist()


def test_template_paths_are_local_and_fixed(monkeypatch):
    assert studio._ROOT.name == "templates"
    assert set(studio._ALLOWED) == {"react","flutter"}
    assert studio.studio_capabilities()["code_execution_on_generation"] is False
