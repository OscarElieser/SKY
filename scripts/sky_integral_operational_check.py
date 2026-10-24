"""SKY: diagnóstico operativo integral de solo lectura sobre servicios reales.

No certifica hardware, no inicia llamadas/SMS y no reemplaza pruebas humanas.
Uso: python scripts/sky_integral_operational_check.py [--research-live]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HOST = "http://127.0.0.1:8765"
ROUTES = {
    "core": "/api/hud/estado",
    "docencia": "/api/sky/academy/capabilities",
    "evaluacion": "/api/sky/academy/education/assessments/catalogue",
    "telefono": "/api/sky/phone/status",
    "skills": "/api/skillpack/catalogue",
    "investigacion_y_fuentes": "/api/sky/verification/connectors",
    "calidad": "/api/sky/quality/operational",
}


def _token() -> str:
    value = os.getenv("SKY_API_KEY", "").strip()
    if value:
        return value
    # Configuración privada habitual: leer sin imprimir ni exportar la clave.
    try:
        from dotenv import dotenv_values
        value = str(dotenv_values(ROOT / ".env").get("SKY_API_KEY") or "").strip()
        if value:
            return value
    except ImportError:
        pass
    path = ROOT / "local_data" / "sky_api_token.txt"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _probe(path: str, key: str) -> dict:
    request = Request(HOST + path, headers={"X-SKY-KEY": key, "Accept": "application/json"},
                      method="GET")
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read(524288))
        if not isinstance(payload, dict):
            return {"reachable": False, "reason": "non_object_response"}
        return {"reachable": True, "http_status": 200, "response": payload}
    except HTTPError as exc:
        return {"reachable": False, "http_status": exc.code,
                "reason": "auth_required_or_route_error"}
    except (URLError, TimeoutError, OSError):
        return {"reachable": False, "reason": "local_api_unavailable"}
    except (ValueError, TypeError):
        return {"reachable": False, "reason": "invalid_json"}


def run(*, research_live: bool = False, target_number: str = "") -> dict:
    key = _token()
    results = {}
    # Estado de endpoints sin retransmitir tokens, memoria o contenido privado.
    for name, route in ROUTES.items():
        raw = _probe(route, key)
        status = {"reachable": raw["reachable"], "reason": raw.get("reason")}
        if "http_status" in raw:
            status["http_status"] = raw["http_status"]
        if raw["reachable"] and name == "telefono":
            x = raw["response"]
            status["feature_enabled"] = bool(x.get("enabled"))
            status["owner_verified"] = bool(x.get("owner_phone_verified"))
            status["provider_configured"] = bool(x.get("twilio_sms_voice_configured"))
            status["live_tested_by_this_script"] = False
        if raw["reachable"] and name == "calidad":
            x = raw["response"]
            status["observed_actions"] = x.get("actions_observed")
            status["actions_verified"] = x.get("actions_verified")
            status["real_windows_hardware_passed"] = x.get("windows_hardware_passed")
            status["real_android_hardware_passed"] = x.get("android_hardware_passed")
        results[name] = status

    result = {
        "scope": "read_only_local_api_readiness",
        "api_base": HOST,
        "checks": results,
        "local_api_readiness_passed": bool(key) and all(x["reachable"] for x in results.values()),
        "operational_certification_integral": False,
        "certification_note": "Este diagnóstico prueba rutas reales, no voz, SIM, dispositivos, exactitud académica ni servicios externos de pago.",
        "pending_physical_tests": ["windows_application_verified", "live_microphone_and_tts",
            "android_device_and_permissions", "real_academic_sources",
            "video_3d_classroom_browser", "phone_carrier_sms_video",
            "configured_mcp_integrations", "security_recovery_drills"],
    }

    if target_number:
        # Sólo valida el destino con la lógica REAL de SKY; no hace llamadas.
        from neural_core import sky_phone
        try:
            destination = sky_phone.native_destination(target_number)
            result["native_number_check"] = {
                "allowed": destination["allowed"],
                "masked": destination["masked"],
                "manual_os_confirmation_required": True,
                "call_completed": False,
            }
        except (sky_phone.PhoneInvalid, sky_phone.PhoneUnavailable):
            result["native_number_check"] = {"allowed": False, "reason": "invalid_or_blocked"}

    if research_live:
        # Real outbound metadata request, no mock, no paper claims.
        try:
            from neural_core.sky_scholarly import search_papers
            papers = search_papers("educacion digital", provider="crossref", limit=2)
            items = papers.get("items", [])
            result["scholarly_live"] = {
                "metadata_retrieved": bool(items),
                "provider": "crossref",
                "count": len(items),
                "full_text_verified": False,
            }
        except Exception:
            result["scholarly_live"] = {"metadata_retrieved": False,
                                        "reason": "external_provider_unavailable",
                                        "full_text_verified": False}
    return result


def main() -> int:
    cli = argparse.ArgumentParser(description="Diagnóstico real de SKY sin acciones de pago")
    cli.add_argument("--research-live", action="store_true",
                     help="Consulta metadatos actuales de Crossref desde Internet")
    cli.add_argument("--target-number", default="",
                     help="Valida E.164 y bloqueos internos sin iniciar una llamada")
    args = cli.parse_args()
    report = run(research_live=args.research_live, target_number=args.target_number)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["local_api_readiness_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
