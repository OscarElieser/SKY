"""Installable SKY mobile/desktop PWA entrypoints; reuse the original HUD and SKY API.

HTTPS required on remote phones. Never cache authenticated routes, commands,
recordings or personal data. Native Android OS control requires a separate,
explicitly permissioned agent (not provided by a browser).
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response, RedirectResponse

STATIC = Path(__file__).resolve().parent / "static"
router = APIRouter()

@router.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return Response(
        json.dumps({
            "id": "/hud", "name": "SKY IA — Asistente personal",
            "short_name": "SKY IA", "description": "SKY IA: voz, texto, docencia y control autorizado",
            "lang": "es", "start_url": "/hud?app=1", "scope": "/",
            "display": "standalone", "background_color": "#07131f",
            "theme_color": "#07131f", "orientation": "any",
            "icons": [
                {"src": "/static/sky-icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                {"src": "/static/sky-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
            ]
        }, ensure_ascii=False),
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"})

@router.get("/sky-sw.js", include_in_schema=False)
def service_worker():
    return Response(
        (STATIC / "sky-sw.js").read_text(encoding="utf-8"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-store", "Service-Worker-Allowed": "/",
                 "X-Content-Type-Options": "nosniff"})

@router.get("/mobile", include_in_schema=False)
def mobile_entry():
    return RedirectResponse(url="/hud?app=1", status_code=307)

@router.get("/api/mobile/install-info")
def install_info():
    return {"client": "sky-hud-pwa", "desktop": "browser_install_or_native_launcher",
            "android": "install_from_https_browser", "ios": "add_to_home_screen_where_supported",
            "windows_actions": "owner_authenticated_SKY_API_then_authorized_windows_agent",
            "android_native_actions": "requires_separate_native_agent_and_system_permissions",
            "remote_prerequisites": ["private HTTPS endpoint", "owner authentication", "authorized device agent"],
            "offline_actions": False, "offline_authentication": False,
            "does_not_expose_pc_api_directly_to_internet": True}
