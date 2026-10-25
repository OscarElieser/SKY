"""Inventario real de la inteligencia unificada de SKY (solo propietario).

Se reutilizan los motores existentes. Registrado/configurado NO implica
modelo online, pago habilitado ni permiso para actuar sobre una cuenta.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from .api import require_key

router = APIRouter(prefix="/api/sky/intelligence", dependencies=[Depends(require_key)])


@router.get("/overview")
def overview():
    from neural_core.providers import provider_summary, local_only
    from neural_core.sky_unified_agents import capability_status
    from neural_core.sky_social_hub import capabilities as social
    from neural_core.sky_openjarvis import status as openjarvis_status
    from neural_core.sky_creative_evolution import capabilities as creative_capabilities
    from neural_core import sky_cerebro
    return {
        "identity": "SKY",
        "controller": "SKY CORE",
        "existing_api": True,
        "api_root": "/api",
        "privacy": {"local_only": local_only()},
        "brain": {"requested_engine": sky_cerebro.motor(),
                  "tool_model_operational": sky_cerebro.disponible()},
        "providers_configured_not_healthchecked": provider_summary(),
        "local_optional_engine": openjarvis_status(),
        "automatic_cognitive_subagents": capability_status(),
        "creative_evolution": creative_capabilities(),
        "social_accounts_configured_not_authenticated": social(),
        "learning": {
            "owner_feedback": "sky_evolution",
            "verified_procedures": "sky_experience_learning",
            "persistent_memory": "smart_memory / sky_neural_memory",
            "updates_weights_without_review": False,
            "updates_production_code_without_review": False,
        },
        "tools_and_device_permissions": "SKY SENTINEL y agente existentes",
    }
