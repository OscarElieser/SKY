"""SKY Developer Workbench: real integration and fail-closed regression checks."""
from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from neural_core import sky_developer_workbench as dev


def test_catalogue_covers_major_platforms_without_faking_installed_status():
    listed = dev.ecosystem(limit=150)
    assert listed["exhaustive_world_catalogue"] is False
    assert listed["installed_or_verified"] is False
    names = {e["name"] for e in listed["items"]}
    assert {"Python", "HTML", "CSS", "Swift", "Rust", "C#"}.issubset(names)
    frameworks = dev.ecosystem(category="frameworks", limit=120)
    names = {i["name"] for i in frameworks["items"]}
    assert {"React", "Tailwind CSS", "Flutter", "Unity", "Unreal Engine", "Godot",
            "Jetpack Compose", "SwiftUI", "FastAPI", "PyTorch"}.issubset(names)
    assert not any(i["installed"] for i in frameworks["items"])
    assert {"PostgreSQL", "Supabase", "Firebase", "Redis"} <= {
        e["name"] for e in dev.ecosystem(category="databases")["items"]}
    assert {"Lucide", "Font Awesome", "Material Symbols", "Iconify"} <= {
        e["name"] for e in dev.ecosystem(category="icons")["items"]}
    assert {"Google Fonts", "Fontsource", "Inter"} <= {
        e["name"] for e in dev.ecosystem(category="fonts")["items"]}


def test_query_and_unknown_category_rejected():
    assert [x["name"] for x in dev.ecosystem("frameworks", query="tailwind")["items"]] == [
        "Tailwind CSS"
    ]
    with pytest.raises(dev.WorkbenchInvalid):
        dev.ecosystem("all-executable-things")
    with pytest.raises(dev.WorkbenchInvalid):
        dev.ecosystem(limit=10000)


def test_project_reconnaissance_react_tailwind_postgres_no_execution():
    project = {
        "package.json": json.dumps({"name":"client", "scripts":{"build":"node build.js"},
            "dependencies":{"react":"^19.0.0","tailwindcss":"^4.0.0","pg":"^8.0.0",
                            "lucide-react":"^1.0.0"}}),
        "src/main.tsx": "export default function App() { return <h1>SKY</h1>; }",
        ".vscode/settings.json": "{}",
    }
    result = dev.inspect_project(project)
    assert {"React", "Tailwind CSS"}.issubset(result["frameworks_detected"])
    assert "PostgreSQL" in result["databases_detected"]
    assert "Visual Studio Code (config presente)" in result["ide_project_hints"]
    assert "lucide-react" in result["dependency_names"]
    assert result["dependencies_installed"] is False
    assert result["project_built"] is False
    assert result["tests_run"] is False
    assert result["security_audit_certified"] is False
    assert any("scripts" in w for w in result["warnings"])


def test_android_flutter_unity_and_godot_project_recognition():
    flutter = dev.inspect_project({
        "pubspec.yaml": "name: sample\ndependencies:\n  flutter:\n    sdk: flutter\n  google_fonts: ^6.0.0\n  sqflite: ^2.0.0\n",
        "lib/main.dart": "void main() {}"
    })
    assert "Flutter" in flutter["frameworks_detected"]
    assert "SQLite" in flutter["databases_detected"]
    assert "Dart" in flutter["language_files"]
    unity = dev.inspect_project({
        "Packages/manifest.json": json.dumps({"dependencies": {"com.unity.ugui": "1.0.0"}}),
        "ProjectSettings/ProjectVersion.txt": "m_EditorVersion: 6000.0",
        "Assets/Game.cs": "class Game {}",
    })
    assert "Unity" in unity["frameworks_detected"]
    assert "C#" in unity["language_files"]
    godot = dev.inspect_project({"project.godot": "config_version=5", "scripts/Player.gd": "extends Node"})
    assert "Godot" in godot["frameworks_detected"]


@pytest.mark.parametrize("path", [
    ".env", ".env.local", "server.pem", "private.key", "secrets.json",
    "google-services.json", "node_modules/evil.js", "../private.txt",
    "C:\\Users\\owner\\secret.txt",
])
def test_private_files_and_paths_are_rejected(path):
    with pytest.raises(dev.WorkbenchInvalid):
        dev.inspect_project({path:"this-is-not-for-project-inspection"})


def test_explain_line_by_line_complete_and_no_source_mutation():
    source = "import os\n\n# nota\ndef suma(a,b):\n    return a+b\nprint(suma(2,3))"
    result = dev.explain_code("Python", source, start_line=1, max_lines=3)
    assert [a["line"] for a in result["annotations"]] == [1,2,3]
    assert result["next_start_line"] == 4
    follow = dev.explain_code("Python", source, start_line=4, max_lines=100)
    assert [a["line"] for a in follow["annotations"]] == [4,5,6]
    assert follow["has_more"] is False
    assert result["code_executed"] is False
    assert result["source_modified"] is False
    assert result["syntax_valid"] is True
    assert result["semantics_fully_proven"] is False
    assert result["annotations"][0]["code"] == "import os"


def test_invalid_python_and_json_are_not_reported_correct():
    x=dev.explain_code("Python","def broke(:\n return 1")
    assert x["syntax_checked"] and x["syntax_valid"] is False
    y=dev.explain_code("JSON",'{"key":[,]}')
    assert y["syntax_checked"] and y["syntax_valid"] is False


def test_offline_web_starter_escapes_user_input_and_remains_multifile():
    d=dev.scaffold_web("<script>alert(1)</script>","hola <img onerror=alert(1)>")
    assert d["files_written"] is False
    assert d["runtime_verified"] is False
    assert set(d["files"])=={"index.html","styles.css","app.js"}
    assert "<script>alert(1)</script>" not in d["files"]["index.html"]
    assert "&lt;script&gt;" in d["files"]["index.html"]
    assert '<script defer src="app.js"></script>' in d["files"]["index.html"]
    assert "addEventListener" in d["files"]["app.js"]


def test_sdk_readiness_reports_presence_without_fake_success(monkeypatch):
    monkeypatch.setattr(dev.shutil, "which", lambda x: "/mock/available" if x == "flutter" else None)
    tools=dev.sdk_readiness()
    flutter=next(x for x in tools["tools"] if x["tool"]=="Flutter")
    assert flutter["found_on_path"] is True
    assert flutter["installed_verified"] is False
    assert flutter["build_or_device_test_run"] is False
    xcode=next(x for x in tools["tools"] if x["tool"].startswith("Xcode"))
    assert xcode["requires_macos"] is True
    assert tools["commands_executed"] is False


@pytest.mark.parametrize("registry,name", [
    ("npm","../../secrets"), ("pub","hello?admin=true"),
    ("pypi","http://127.0.0.1"), ("file","normal"), ("npm",""),
])
def test_registry_ssrf_and_bad_requests_fail_closed(registry,name):
    with pytest.raises(dev.WorkbenchInvalid):
        dev._registry_endpoint(registry,name)


def test_package_metadata_opt_in_and_no_install(monkeypatch):
    monkeypatch.delenv("SKY_DEV_REGISTRY_LOOKUP_ENABLED",raising=False)
    with pytest.raises(dev.RegistryUnavailable):
        dev.lookup_package("pypi","fastapi")
    monkeypatch.setenv("SKY_DEV_REGISTRY_LOOKUP_ENABLED","1")
    assert dev._registry_endpoint("npm","@iconify/react").endswith("%40iconify%2Freact/latest")

    class Response:
        status=200
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def read(self,n):
            return json.dumps({"version":"1.2.3","description":"fake test package"}).encode()
    class Opener:
        def open(self, request, timeout):
            assert request.full_url=="https://registry.npmjs.org/lucide-react/latest"
            return Response()
    monkeypatch.setattr(dev.urllib.request,"build_opener",lambda *a:Opener())
    result=dev.lookup_package("npm","lucide-react")
    assert result["latest_reported"]=="1.2.3"
    assert result["license_verified"] is False
    assert result["package_installed"] is False
    assert result["vulnerabilities_audited"] is False


def test_api_uses_existing_sentinel_and_rejects_invalid_payload(monkeypatch):
    monkeypatch.setenv("SKY_API_KEY","sky-workbench-ci-private-local-test-key")
    from metaverse.api import app,api_token
    with TestClient(app) as client:
        assert client.get("/api/developer/workbench/catalogue").status_code in (401,403)
        headers={"X-SKY-KEY":api_token()}
        res=client.get("/api/developer/workbench/catalogue?category=icons",headers=headers)
        assert res.status_code==200
        assert res.json()["installed_or_verified"] is False
        result=client.post("/api/developer/workbench/explain",headers=headers,json={
            "language":"Python","source":"print('Hola mundo')"})
        assert result.status_code==200
        assert result.json()["code_executed"] is False
        scan=client.post("/api/developer/workbench/inspect",headers=headers,json={
            "files":{"main.dart":"void main() {}","pubspec.yaml":"name: proyecto"}})
        assert scan.status_code==200
        assert scan.json()["project_built"] is False
        deny=client.post("/api/developer/workbench/inspect",headers=headers,json={
            "files":{".env":"SOME_SECRET=TEST"}})
        assert deny.status_code==422
        t=client.post("/api/developer/workbench/starter/web",headers=headers,json={
            "title":"Proyecto Sky"})
        assert t.status_code==200
        assert t.json()["files_written"] is False
        state=client.get("/api/developer/workbench/readiness",headers=headers)
        assert state.status_code==200 and state.json()["commands_executed"] is False
