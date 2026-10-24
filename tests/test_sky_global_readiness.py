"""SKY GLOBAL: behavioral tests, not claims of worldwide certification."""
from __future__ import annotations

from pathlib import Path

from neural_core.sky_global_readiness import readiness
from test_sky_v9_7_creative import H, env


def test_local_mode_never_claims_worldwide_readiness(monkeypatch):
    monkeypatch.setenv("SKY_DEPLOYMENT_MODE", "local")
    monkeypatch.delenv("SKY_REDIS_URL", raising=False)
    report = readiness()
    assert report["global_ready"] is False
    by_id = {item["id"]: item for item in report["checks"]}
    assert by_id["deployment_mode"]["status"] == "fail"
    assert by_id["redis_live"]["status"] == "fail"
    assert by_id["multi_region_failover"]["status"] == "unverified"
    assert by_id["independent_ai_audit"]["status"] == "unverified"
    assert by_id["hud_basic_a11y"]["status"] == "pass"
    assert report["counts"]["unverified"] >= 5
    assert report["visible_static_labels"] > 0
    assert "en" in report["reviewed_ui_coverage_percent"]


def test_invalid_public_config_fails_closed_and_never_leaks_secrets(monkeypatch):
    monkeypatch.setenv("SKY_DEPLOYMENT_MODE", "public")
    monkeypatch.setenv("SKY_API_KEY", "testing-secret-not-for-release")
    monkeypatch.delenv("SKY_REDIS_URL", raising=False)
    report = readiness()
    checks = {x["id"]: x for x in report["checks"]}
    assert checks["existing_public_guard"]["status"] == "fail"
    assert report["global_ready"] is False
    assert "testing-secret-not-for-release" not in str(report)


def test_missing_hud_or_translation_cannot_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_DEPLOYMENT_MODE", "local")
    monkeypatch.delenv("SKY_REDIS_URL", raising=False)
    (tmp_path / "hud.html").write_text("<html><body>No access</body></html>", encoding="utf-8")
    (tmp_path / "hud.css").write_text("body {color: black}", encoding="utf-8")
    report = readiness(static_dir=tmp_path)
    ids = {x["id"]: x for x in report["checks"]}
    assert ids["hud_basic_a11y"]["status"] == "fail"
    assert ids["reviewed_ui_coverage"]["status"] == "fail"


def test_global_readiness_is_private_no_cache_and_safe(env, monkeypatch):
    monkeypatch.setenv("SKY_DEPLOYMENT_MODE", "local")
    monkeypatch.delenv("SKY_REDIS_URL", raising=False)
    client, _ = env
    assert client.get("/api/sky/global/readiness").status_code == 401
    response = client.get("/api/sky/global/readiness", headers=H)
    assert response.status_code == 200, response.text
    assert "no-store" in response.headers["cache-control"]
    data = response.json()
    assert data["global_ready"] is False
    assert data["mode"] == "local"
    assert "checks" in data
    assert "SKY_API_KEY" not in str(data)


def test_hud_loads_actual_global_locale_and_has_keyboard_entrypoint(env):
    client, _ = env
    html = client.get("/").text
    assert 'class="skip-link"' in html
    assert 'href="#chat-input"' in html
    assert 'sky-global-i18n.js' in html
    assert 'role="log"' in html
    assert 'role="status"' in html
    assert 'aria-label="Activar o desactivar escucha continua"' in html
    css = client.get("/static/hud.css").text
    assert ".skip-link:focus" in css
    assert "prefers-reduced-motion:reduce" in css


def test_selected_language_is_used_for_browser_voice_and_offline_stt():
    hud = (Path(__file__).resolve().parents[1] / "metaverse" / "static" / "hud.js").read_text(encoding="utf-8")
    assert "function idiomaVoz()" in hud
    assert "rec.lang = idiomaVoz()" in hud
    assert "sr.lang = idiomaVoz()" in hud
    assert hud.count("fd.append('language', idiomaVoz().split('-')[0])") == 2
    assert "window.addEventListener('sky:languagechange'" in hud
    assert "toLocaleDateString(locale" in hud
    assert "S.ttsLocal && idiomaVoz().split('-')[0] === 'es'" in hud
