"""REAL HTML5/CSS3/Web validation in SKY offline Docker. No external websites."""
from __future__ import annotations

import os
import pytest

from neural_core.sky_docker_builder import build
from neural_core.sky_programming_capabilities import resolve_language

pytestmark = pytest.mark.skipif(
    os.environ.get("SKY_LIVE_DOCKER_TEST") != "1",
    reason="Requires owner-approved offline Docker images and SKY_LIVE_DOCKER_TEST=1",
)

HTML = (
    '<!doctype html><html lang="es"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Mi sitio SKY</title>'
    '</head><body><main><h1>Hola mundo</h1></main></body></html>'
)
WEB = HTML.replace(
    '</head>',
    '<link rel="stylesheet" href="styles.css">'
    '<script defer src="app.js"></script></head>',
)
CSS = "body { color: #123456; }\n"
JS = 'document.querySelector("h1").textContent = "SKY OK";\n'


def test_html5_alias_and_valid_html_document():
    assert resolve_language("HTML5") == "HTML"
    result = build("HTML5", {"index.html": HTML}, approved=True, timeout_seconds=18)
    assert result["ok"] is True, result
    assert result["status"] == "validated"
    assert result["compile"]["verified"] is True
    assert result["code_executed"] is False
    assert result["run"] is None
    assert result["rendered_in_real_browser"] is False


def test_html5_invalid_semantics_fail_real_validator():
    invalid = '<!doctype html><html><head><title>x</title></head><body><main><p><div>invalid</div></p></main></body></html>'
    result = build("HTML", {"index.html": invalid}, approved=True)
    assert result["ok"] is False
    assert result["status"] == "validation_failed"
    assert result["compile"]["verified"] is False
    assert result["run"] is None


def test_css3_alias_and_css_property_check():
    assert resolve_language("CSS3") == "CSS"
    result = build("CSS3", {"styles.css": CSS}, approved=True)
    assert result["ok"] is True, result
    assert result["status"] == "validated"
    assert result["code_executed"] is False


def test_css3_rejects_invalid_property_and_hex():
    result = build("CSS", {"styles.css": "h1 { color: #zzzzzz; not-a-css-property: 10px; }\n"}, approved=True)
    assert result["ok"] is False
    assert result["status"] == "validation_failed"
    assert result["compile"]["verified"] is False


def test_web_project_real_html_css_js_and_dom():
    result = build("Web", {
        "index.html": WEB, "styles.css": CSS, "app.js": JS,
    }, approved=True, timeout_seconds=22)
    assert result["ok"] is True, result
    assert result["compile"]["verified"] is True
    assert result["run"]["verified"] is True
    assert result["code_executed"] is True
    assert result["dom_emulated"] is True
    assert result["rendered_in_real_browser"] is False
    assert "dom_smoke_verified" in result["run"]["stdout"]


def test_web_project_bad_js_has_no_dom_execution():
    result = build("Web", {
        "index.html": WEB, "styles.css": CSS, "app.js": "const a = ;",
    }, approved=True)
    assert result["ok"] is False
    assert result["status"] == "compile_failed"
    assert result["run"] is None


def test_web_project_missing_css_link_fails_smoke():
    no_link = WEB.replace('<link rel="stylesheet" href="styles.css">', '')
    result = build("Web", {
        "index.html": no_link, "styles.css": CSS, "app.js": JS,
    }, approved=True)
    assert result["compile"]["verified"] is True
    assert result["ok"] is False
    assert result["run"]["verified"] is False


def test_web_script_error_is_not_verified():
    result = build("Web", {
        "index.html": WEB, "styles.css": CSS,
        "app.js": "throw new Error('fallo de JS');",
    }, approved=True)
    assert result["compile"]["verified"] is True
    assert result["ok"] is False
    assert result["run"]["verified"] is False
