"""Pruebas del Skillpack sin credenciales externas ni acceso a Internet."""
import pytest
from neural_core import sky_skillpack as p


def test_29_named_skills_and_truthful_states(monkeypatch):
    for key in ("NOTION_TOKEN", "LINEAR_API_KEY", "VERCEL_TOKEN", "FIRECRAWL_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    rows = p.catalogue()
    assert rows["total_requested_here"] == 29
    assert len(rows["skills"]) == 29
    assert len({r["id"] for r in rows["skills"]}) == 29
    assert all(not r["live_verified"] for r in rows["skills"])
    lookup = {r["id"]: r for r in rows["skills"]}
    assert lookup["notion-workspace"]["status"] == "needs_configuration"
    assert lookup["google-workspace-connector"]["status"] == "needs_configuration"
    assert rows["adapter_count"] == 29
    assert lookup["pdf-pro"]["office_endpoint"] == "/api/office/generate"


def test_existing_office_studio_is_reused():
    doc = p.execute("docx-coauthoring", {})
    assert doc["endpoint"] == "/api/office/generate"
    assert doc["kind"] == "docx"


def test_seo_checks_are_computed_not_fabricated():
    r = p.execute("seo-audit", {
        "html": '<html><head><title>Educación</title><meta name="description" '
                'content="Programa de educación"></head><body><h1>SKY</h1>'
                '<img src="ok.png" alt="Aula"><img src="missing.png"></body></html>'
    })
    assert r["checks"]["title"]
    assert r["checks"]["meta_description"]
    assert r["checks"]["one_h1"]
    assert r["missing_alt"] == 1
    assert not r["checks"]["images_have_alt"]


def test_svg_is_generated_as_a_real_artifact():
    r = p.execute("algorithmic-art", {"lines": 12})
    assert r["mime"] == "image/svg+xml"
    assert r["content"].startswith("<svg")
    assert r["content"].count("<line ") == 12


def test_carousel_escapes_untrusted_html():
    r = p.execute("open-carousel", {"items": ["Hola", "<script>alert(1)</script>"]})
    assert r["mime"] == "text/html"
    assert "<script>" not in r["content"]
    assert "&lt;script&gt;" in r["content"]


def test_nonimplemented_fails_closed():
    with pytest.raises(p.SkillUnavailable):
        p.execute("google-workspace-connector", {})
    with pytest.raises(p.SkillInvalid):
        p.execute("skill-no-existe", {})


def test_private_service_cannot_run_without_credentials(monkeypatch):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    with pytest.raises(p.SkillUnavailable):
        p.execute("notion-workspace", {})


def test_supabase_table_must_be_preapproved(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "non-secret-for-mocked-test")
    monkeypatch.setenv("SKY_SKILL_SUPABASE_ALLOWED_TABLES", "public_places")
    with pytest.raises(p.SkillInvalid):
        p.execute("supabase-mcp", {"table": "auth.users"})
    with pytest.raises(p.SkillInvalid):
        p.execute("supabase-mcp", {"table": "private_places"})


def test_firecrawl_domain_is_allowlisted_before_network(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fake-test-token")
    monkeypatch.setenv("SKY_FIRECRAWL_ALLOWED_HOSTS", "www.example.org")
    with pytest.raises(p.SkillInvalid):
        p.execute("firecrawl", {"url": "http://www.example.org/"})
    with pytest.raises(p.SkillInvalid):
        p.execute("firecrawl", {"url": "https://127.0.0.1/"})
    with pytest.raises(p.SkillInvalid):
        p.execute("firecrawl", {"url": "https://evil.example.org/"})


def test_remote_connector_uses_fixed_endpoint(monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "fake-token")
    called = {}
    def transport(method, url, **kwargs):
        called.update(method=method, url=url, **kwargs)
        return {"ok": True, "data": {"viewer": {"name": "Test"}}}
    monkeypatch.setattr(p, "_request", transport)
    output = p.execute("linear-sync", {})
    assert output["ok"]
    assert called["method"] == "POST"
    assert called["url"] == "https://api.linear.app/graphql"
    assert "issues" in called["payload"]["query"]


def test_api_contains_owner_protection():
    import ast
    from pathlib import Path
    source = Path("metaverse/api.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    funcs = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    for name in ("skillpack_catalogue", "skillpack_execute"):
        assert name in funcs
        assert any("require_key" in ast.unparse(dec) for dec in funcs[name].decorator_list)


def test_text_and_voice_reuse_explicit_safe_route(monkeypatch):
    captured = {}
    def run(skill, body):
        captured.update(skill=skill, body=body)
        return {"ok": True, "text": "Respuesta confirmada"}
    monkeypatch.setattr(p, "execute", run)
    assert p.interpretar("Abre Word") is None
    response = p.interpretar("SKY, ejecuta skill humanizer: Corrige esta redacción.")
    assert response["tipo"] == "respuesta"
    assert response["mensaje"] == "Respuesta confirmada"
    assert captured["skill"] == "humanizer"
    assert captured["body"]["text"] == "Corrige esta redacción."
    assert p.interpretar("SKY, ejecuta skill slack-communicator: envía hola")["tipo"] == "error"


def test_existing_assistant_registers_skillpack_without_replacing_rules():
    from pathlib import Path
    source = Path("neural_core/sky_asistente_personal.py").read_text(encoding="utf-8")
    assert "sky_skillpack.interpretar(texto)" in source
    assert "sky_skills.interpretar(texto)" in source
