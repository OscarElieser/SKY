"""SKY Native Adaptive Core: local, evidence-informed planning.

Incremental policy learning from existing verified-outcome counters.
No cloud model is called; no conversation or credentials are persisted here.
Statistical recommendations CANNOT authorize tools, write model weights, or deploy code.
"""
from __future__ import annotations

import math
from typing import Any

from . import sky_cognition

_ALLOWED_ROLES = frozenset({
    "planificador", "documentalista", "diseñador", "creador_3d", "memoria"
})
_MIN_SAMPLE = 5


def _counts(role: str, stats: dict[str, Any]) -> tuple[int, int]:
    if role not in _ALLOWED_ROLES:
        return 0, 0
    entry = stats.get(role, {})
    if not isinstance(entry, dict):
        return 0, 0
    success, failed = entry.get("completed", 0), entry.get("failed", 0)
    # Fail closed on malformed or adversarial telemetry, never infer permission.
    if (type(success) is not int or type(failed) is not int
            or min(success, failed) < 0 or success + failed > 10000):
        return 0, 0
    return success, failed


def reliability(role: str, stats: dict[str, Any]) -> dict[str, Any]:
    """Conservative Wilson lower bound, zero evidence never looks successful."""
    if role not in _ALLOWED_ROLES:
        return {"role": role, "observations": 0, "status": "no_measured_role",
                "confidence_lower_bound": None, "can_execute": False}
    success, failed = _counts(role, stats)
    n = success + failed
    if not n:
        return {"role": role, "observations": 0, "completed": 0, "failed": 0,
                "success_rate": None, "confidence_lower_bound": None,
                "status": "insufficient_evidence", "can_execute": False}
    p = success / n
    z = 1.96
    denominator = 1 + z * z / n
    center = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lower = max(0.0, (center - spread) / denominator)
    # Enough data only to recommend further supervised testing, not execute.
    status = ("candidate_for_supervised_test"
              if n >= _MIN_SAMPLE and lower >= 0.60
              else "insufficient_evidence" if n < _MIN_SAMPLE else "review_failures")
    return {
        "role": role, "observations": n,
        "completed": success, "failed": failed,
        "success_rate": round(p, 4),
        "confidence_lower_bound": round(lower, 4),
        "status": status, "can_execute": False,
    }


def _verified_stats() -> tuple[dict[str, Any], bool]:
    """Reuse existing local counters; never import untrusted chat or web content."""
    try:
        from .sky_neural_memory import execution_report
        report = execution_report()
        values = report.get("by_role", {})
        if not isinstance(values, dict):
            return {}, False
        return values, True
    except (OSError, RuntimeError, ValueError, TypeError):
        return {}, False


def adaptive_plan(query: str, *, device: str = "unknown") -> dict[str, Any]:
    """An independent SKY planning API. This endpoint never runs actions."""
    proposed = sky_cognition.plan(query, device=device)
    stats, available = _verified_stats()
    requested_role = proposed["role"]
    evidence = reliability(requested_role, stats)
    # Risk from user's request dominates any statistical evidence.
    review = (proposed["requires_confirmation"]
              or proposed["risk"] != "bajo"
              or evidence["status"] != "candidate_for_supervised_test")
    return {
        "sky_native_engine": "adaptive_policy_v1",
        "model_provider_called": False,
        "input_stored": False,
        "weights_updated": False,
        "telemetry_available": available,
        "classification": {
            "role": requested_role, "intent": proposed["intent"],
            "risk": proposed["risk"],
        },
        "role_reliability": evidence,
        "plan": proposed,
        "review_required": review,
        "action_executed": False,
        "permission_granted": False,
        "code_deployed": False,
        "status": "proposed_only",
        "policy": "Un historial positivo no autoriza ejecutar herramientas, publicar, borrar ni cambiar permisos.",
    }


def evolution_status() -> dict[str, Any]:
    """Read-only, privacy-preserving observability of adaptation."""
    stats, available = _verified_stats()
    return {
        "engine": "sky_native_adaptive_policy_v1",
        "mode": "local_statistics_no_external_provider",
        "telemetry_available": available,
        "role_history": {role: reliability(role, stats) for role in sorted(_ALLOWED_ROLES)},
        "automatic_training": False,
        "training_performed": False,
        "model_weights_updated": False,
        "personal_content_saved": False,
        "automatic_tool_execution": False,
        "external_inference_required": False,
        "evidence_source": "sky_neural_memory.verified_executions",
        "trust_limit": "La verificación depende de quien registra cada resultado; las métricas no son atestación criptográfica.",
        "next_step": "Evaluar calidad por tareas y aprobar mejoras mediante CI y revisión humana.",
    }
