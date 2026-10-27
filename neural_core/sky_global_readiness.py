"""Read-only, evidence-based global deployment checks for the existing SKY API.

This reports measurable local/runtime facts and explicitly leaves independent
certification, load tests and worldwide coverage UNVERIFIED. It never changes
configuration, reaches arbitrary URLs, stores user data or exposes secrets.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "metaverse" / "static"
LOCALES = ("en", "pt", "fr", "ar", "zh", "ja", "sw")
MIN_UI_COVERAGE = 95.0


def _check(area: str, key: str, status: str, detail: str, *, measured: bool = False) -> dict:
    assert status in ("pass", "fail", "unverified")
    return {"area": area, "id": key, "status": status,
            "detail": detail, "measured": measured}


def readiness(static_dir: Path | None = None) -> dict:
    """Check real configuration/services, never equating configured with certified.

    The public gate is SKY's existing fail-closed deployment_v102 logic; it
    intentionally is NOT rewritten here. External audits remain unverified.
    """
    checks: list[dict] = []
    mode = os.getenv("SKY_DEPLOYMENT_MODE", "local").strip().lower()
    checks.append(_check("infrastructure", "deployment_mode",
                         "pass" if mode == "public" else "fail",
                         "Modo público seleccionado" if mode == "public"
                         else "SKY sigue en modo local; no es un servicio mundial",
                         measured=True))

    if mode == "public":
        try:
            from metaverse.deployment_v102 import validate_environment
            validate_environment()
            checks.append(_check("infrastructure", "existing_public_guard", "pass",
                                 "Validación del arranque público completada",
                                 measured=True))
        except Exception:
            # No exception messages: may contain internal infrastructure data.
            checks.append(_check("infrastructure", "existing_public_guard", "fail",
                                 "La validación pública de SKY impide este despliegue",
                                 measured=True))
    else:
        checks.append(_check("infrastructure", "existing_public_guard", "fail",
                             "Guardia de despliegue público no activada", measured=True))

    redis_configured = bool(os.getenv("SKY_REDIS_URL"))
    if not redis_configured:
        checks.append(_check("infrastructure", "redis_live", "fail",
                             "No está configurado Redis distribuido", measured=True))
    else:
        try:
            from metaverse.distributed_limits import redis_client
            client = redis_client()
            active = client is not None and client.ping() is True
        except Exception:
            active = False
        checks.append(_check("infrastructure", "redis_live",
                             "pass" if active else "fail",
                             "Redis respondió PING" if active else "Redis no respondió PING",
                             measured=True))

    checks.append(_check("infrastructure", "public_tls", "unverified",
                         "La bandera de proxy TLS no verifica un certificado ni una conexión externa"))
    checks.append(_check("infrastructure", "multi_region_failover", "unverified",
                         "Faltan pruebas externas de balanceo, regiones y recuperación"))

    try:
        from neural_core.sky_i18n_audit import report
        source = Path(static_dir) if static_dir is not None else STATIC
        audit = report(source, languages=LOCALES)
        visible = audit["visible_static_labels"]
        coverage = audit["languages"]
        results = {locale: coverage[locale]["percent"] for locale in LOCALES}
        complete = visible > 0 and all(v >= MIN_UI_COVERAGE for v in results.values())
        checks.append(_check("languages", "reviewed_ui_coverage",
                             "pass" if complete else "fail",
                             "Etiquetas estáticas revisadas por idioma; umbral 95%; no mide conversación ni voz",
                             measured=True))
    except Exception:
        visible, results = 0, {}
        checks.append(_check("languages", "reviewed_ui_coverage", "fail",
                             "No fue posible medir las traducciones estáticas",
                             measured=True))
    checks.append(_check("languages", "speech_and_culture", "unverified",
                         "No hay pruebas de reconocimiento, voz y calidad cultural por región"))

    html = (Path(static_dir) if static_dir is not None else STATIC) / "hud.html"
    css = (Path(static_dir) if static_dir is not None else STATIC) / "hud.css"
    try:
        markup, styles = html.read_text(encoding="utf-8"), css.read_text(encoding="utf-8")
        accessible = all(token in markup for token in
                         ('class="skip-link"', 'href="#chat-input"', 'role="log"',
                          'sky-global-i18n.js')) and "prefers-reduced-motion" in styles
    except OSError:
        accessible = False
    checks.append(_check("accessibility", "hud_basic_a11y",
                         "pass" if accessible else "fail",
                         "Controles básicos de teclado, bitácora accesible e idioma presentes"
                         if accessible else "Faltan controles básicos de accesibilidad en HUD",
                         measured=True))
    checks.append(_check("accessibility", "wcag_assistive_technology", "unverified",
                         "Requiere pruebas manuales de lector de pantalla, contraste y WCAG 2.2"))

    checks.append(_check("governance", "privacy_compliance", "unverified",
                         "No consta auditoría jurídica por jurisdicción ni evidencia de derechos del titular"))
    checks.append(_check("governance", "independent_ai_audit", "unverified",
                         "ISO/IEC 42001, ISO/IEC 27001 y evaluación de sesgos requieren evidencias externas"))
    checks.append(_check("reliability", "worldwide_performance", "unverified",
                         "No existen mediciones verificadas desde múltiples regiones y redes"))
    checks.append(_check("reliability", "disaster_recovery", "unverified",
                         "No existe evidencia de restauración operativa y RTO/RPO internacionales"))

    counts = {status: sum(c["status"] == status for c in checks)
              for status in ("pass", "fail", "unverified")}
    return {
        "service": "SKY GLOBAL readiness",
        "mode": mode,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "global_ready": counts["fail"] == 0 and counts["unverified"] == 0,
        "counts": counts,
        "ui_locales_measured": list(LOCALES),
        "visible_static_labels": visible,
        "reviewed_ui_coverage_percent": results,
        "checks": checks,
        "warning": "Un chequeo interno no sustituye despliegue real, pruebas físicas, auditoría legal ni certificación.",
    }
