"""Regresiones sin red para SKY Scholar y perfiles profesionales."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from neural_core import sky_scholarly as scholarly
from neural_core import sky_pro_skills as skills


def test_scholar_link_is_manual_only():
    link = scholarly.scholar_link("transporte Nicaragua")
    assert link.startswith("https://scholar.google.com/scholar?q=")
    assert "transporte+Nicaragua" in link
    with pytest.raises(ValueError):
        scholarly.scholar_link("x")


def test_national_and_international_university_catalogue():
    ni = scholarly.list_universities("Nicaragua")
    international = scholarly.list_universities("Internacional")
    assert any("UNAN" in x["name"] for x in ni)
    assert any("UNI" in x["name"] for x in ni)
    assert any("MIT" in x["name"] for x in international)
    assert all(x["access"] == "public_catalogue_not_connected" for x in ni)
    with pytest.raises(ValueError):
        scholarly.list_universities("no-existe")


def test_openalex_result_is_only_metadata(monkeypatch):
    def mock_get(url):
        assert "api.openalex.org/works?" in url
        assert "search=alfabetizacion" in url
        return {"results": [{
            "title": "Aprendizaje y tecnología", "publication_year": 2025,
            "doi": "https://doi.org/10.1234/abc",
            "authorships": [{"author": {"display_name": "Investigadora A"}}],
            "primary_location": {"source": {"display_name": "Revista Educativa"}}
        }]}
    monkeypatch.setattr(scholarly, "_get_json", mock_get)
    data = scholarly.search_papers("alfabetizacion", "openalex", 3)
    assert data["live_lookup"] is True
    assert data["items"][0]["title"] == "Aprendizaje y tecnología"
    assert data["items"][0]["doi"] == "10.1234/abc"
    assert data["items"][0]["full_text_read"] is False
    assert not data["items"][0]["peer_review_verified"]
    assert data["google_scholar_url"].startswith("https://scholar.google.com/")


def test_crossref_and_registered_doi(monkeypatch):
    def mock_get(url):
        assert url.startswith("https://api.crossref.org/")
        return {"message": {"items": [{
            "title": ["Estudio técnico"], "author": [{"given": "Ana", "family": "Pérez"}],
            "DOI": "10.1111/example", "published": {"date-parts": [[2024, 4]]},
            "container-title": ["Revista Global"],
        }]}} if "query.bibliographic" in url else {"message": {
            "title": ["Estudio técnico"], "author": [{"given": "Ana", "family": "Pérez"}],
            "DOI": "10.1111/example", "published": {"date-parts": [[2024, 4]]},
            "container-title": ["Revista Global"],
        }}
    monkeypatch.setattr(scholarly, "_get_json", mock_get)
    papers = scholarly.search_papers("ciencia", "crossref", 2)
    assert papers["items"][0]["authors"] == ["Ana Pérez"]
    assert papers["items"][0]["year"] == 2024
    doi = scholarly.lookup_doi("10.1111/example")
    assert doi["doi_metadata_retrieved"]
    assert doi["full_text_read"] is False
    with pytest.raises(ValueError):
        scholarly.lookup_doi("https://evil.com/anything")
    with pytest.raises(ValueError):
        scholarly.search_papers("educacion", "google", 3)
    with pytest.raises(ValueError):
        scholarly.search_papers("educacion", "openalex", 200)


def test_network_hosts_redirects_and_repo_path_rejected():
    with pytest.raises(ValueError):
        scholarly._read_url("http://api.crossref.org/works", host="api.crossref.org")
    with pytest.raises(ValueError):
        scholarly._read_url("https://127.0.0.1/", host="api.crossref.org")
    with pytest.raises(ValueError):
        scholarly._get_json("https://example.net/")
    with pytest.raises(ValueError):
        scholarly._NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://evil.example")
    for path in ("../../etc/passwd", "README.md?x=1", "script.sh", "nested//README.md", "README.md#x"):
        with pytest.raises(ValueError):
            scholarly.read_github_reference("python/cpython", path)
    with pytest.raises(ValueError):
        scholarly.read_github_reference("unknown/unknown", "README.md")


def test_approved_github_read_reuses_catalogue(monkeypatch):
    def mock_reader(url, *, host, headers=None):
        assert host == "raw.githubusercontent.com"
        assert "python/cpython/main/README.md" in url
        return b"# Python\nScientific community"
    monkeypatch.setattr(scholarly, "_read_url", mock_reader)
    result = scholarly.read_github_reference("python/cpython", "README.md")
    assert result["read_only"] is True
    assert result["content"].startswith("# Python")
    assert result["retrieved"] is True


def test_skill_profiles_are_guidance_not_fake_installed_plugins():
    catalog = skills.catalog()
    assert len(catalog) >= 12
    assert {"humanize", "impeccable", "engineering", "accounting",
            "administration", "marketing", "human-resources"}.issubset({x["id"] for x in catalog})
    assert all(x["external_skill_installed"] is False for x in catalog)
    assert "impeccable" in skills.match_skills("aplicar la skill implecable al diseño gráfico")
    assert "humanize" in skills.match_skills("humanizar una monografía")
    assert "developer" in skills.match_skills("programar API en Python")
    assert skills.match_skills("hola") == []
    assert skills.match_skills("x", explicit=["marketing", "humanize", "marketing"]) == ["marketing", "humanize"]
    with pytest.raises(ValueError):
        skills.match_skills("x", explicit=["not-a-skill"])
    plan = skills.skill_plan("marketing y ventas", selected=["marketing", "humanize"])
    assert not plan["applied_by_model"]
    assert "no invent" in plan["instructions"].lower()


def test_api_scholarly_routes_are_mountable_without_network(monkeypatch):
    from metaverse.impacto_api import router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    monkeypatch.setattr(scholarly, "search_papers", lambda query, provider, limit: {
        "query": query, "items": [], "full_text_read": False})
    response = client.post("/api/impacto/scholar/search", json={"query": "educación"})
    assert response.status_code == 200
    assert response.json()["result"]["items"] == []
    assert client.get("/api/impacto/university/repositories?country=Nicaragua").status_code == 200
    assert client.get("/api/impacto/skills").json()["skills"][0]["type"] == "built_in_guidance"
    assert client.post("/api/impacto/skills/plan", json={
        "task": "mejorar la interfaz de una app", "selected": ["impeccable"]
    }).json()["result"]["skills"][0]["id"] == "impeccable"
    assert client.post("/api/impacto/repository/read", json={
        "repository": "evil/repo", "path": "README.md"
    }).status_code == 422
    assert client.post("/api/impacto/document/read",
                       files={"file": ("extracto.txt", b"Contenido documental de prueba", "text/plain")}).status_code == 200
    assert client.post("/api/impacto/document/read",
                       files={"file": ("../../bad.exe", b"evil", "application/octet-stream")}).status_code == 422


def test_research_writing_requires_real_metadata(monkeypatch):
    from metaverse.impacto_api import router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    monkeypatch.setattr(scholarly, "search_papers", lambda query, provider, limit: {
        "query": query, "items": [], "full_text_read": False})
    r = client.post("/api/impacto/research/write", json={
        "topic": "currículo escolar", "instruction": "ensayo crítico y verificado"})
    assert r.status_code == 200
    assert not r.json()["ok"]
    assert "no se generará" in r.json()["error"]


def test_impacto_requires_existing_owner_credentials():
    from pathlib import Path
    api = (Path(__file__).resolve().parents[1] / "metaverse" / "api.py").read_text(encoding="utf-8")
    assert "app.include_router(sky_impacto_router, dependencies=[Depends(require_key)])" in api


def test_university_resource_limits_and_html(monkeypatch):
    from email.message import Message

    class Response:
        def __init__(self):
            self.headers = Message()
            self.headers["Content-Type"] = "text/html; charset=utf-8"
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def read(self, n):
            return b"<html><body><h1>Tesis educativa</h1><script>ignore()</script><p>Resumen comprobable</p></body></html>"

    class Opener:
        def open(self, req, timeout):
            assert req.full_url.startswith("https://repositorio.unan.edu.ni/")
            return Response()

    monkeypatch.setattr(scholarly, "_opener", lambda: Opener())
    doc = scholarly.read_university_resource("unan_repo", "tesis.html")
    assert doc["read_only"] is True
    assert doc["claims_verified"] is False
    assert "Tesis educativa" in doc["text"]
    assert "ignore()" not in doc["text"]
    for path in ("../secret.pdf", "item/../../secret.pdf", "index.php", "thing.zip", "//private.pdf"):
        with pytest.raises(ValueError):
            scholarly.read_university_resource("unan_repo", path)
    with pytest.raises(ValueError):
        scholarly.read_university_resource("no-registrado", "tesis.pdf")
