"""Regresiones seguras para HTML5, CSS3 y sitios web en SKY Developer."""
from __future__ import annotations

import pytest
from neural_core.sky_docker_builder import (
    PROFILES, _source_archive, RunnerInvalid, catalogue,
)
from neural_core.sky_programming_capabilities import (
    resolve_language, detect_languages,
)


def test_html5_css3_and_web_are_native_profiles():
    assert resolve_language("HTML5") == "HTML"
    assert resolve_language("CSS3") == "CSS"
    assert resolve_language("Web") == "Web"
    assert {"HTML", "CSS", "Web"} <= set(PROFILES)
    assert PROFILES["HTML"].run is None
    assert PROFILES["CSS"].run is None
    assert PROFILES["Web"].run == "node /opt/sky-web/smoke.cjs"
    assert PROFILES["Web"].image == "sky-web:2026-10"


def test_sky_understands_multilingual_web_requests():
    names = detect_languages("Crear sitio web completo con HTML5, CSS3 y JavaScript")
    assert "HTML" in names
    assert "CSS" in names
    assert "JavaScript" in names
    assert "Web" in names


def test_web_requires_three_named_files():
    with pytest.raises(RunnerInvalid):
        _source_archive("Web", {"index.html": "<!doctype html><title>SKY</title>"})
    data, has_tests = _source_archive("Web", {
        "index.html": "<!doctype html><html></html>",
        "styles.css": "main { color: red; }",
        "app.js": "console.log('OK')",
    })
    assert data and has_tests is False


@pytest.mark.parametrize("name", [
    "../private.html", "/etc/passwd", "a\\evil.css",
    "config/../../secret.js", "node_modules/index.js",
    ".htmlvalidate.cjs", "Dockerfile", "tests/evil.test.js",
])
def test_reject_unsafe_web_filenames(name):
    with pytest.raises(RunnerInvalid):
        _source_archive("Web", {
            "index.html": "hello",
            "styles.css": "body{color:red}",
            "app.js": "console.log(1)",
            name: "data",
        })


def test_catalogue_reports_only_real_profiles():
    c = catalogue()
    s = {entry["language"]: entry for entry in c["supported"]}
    assert s["HTML"]["main_file"] == "index.html"
    assert s["CSS"]["main_file"] == "styles.css"
    assert s["Web"]["main_file"] == "index.html"
    assert c["full_untrusted_code_isolation_guaranteed"] is False
    assert c["automatic_image_download"] is False
