"""Operational proof dashboard. No synthetic benchmark scores or claimed 100/100."""
from __future__ import annotations

from . import sky_metricas, sky_execution_metrics
from .action_verifier import verificador_acciones

def report(period: str="hoy") -> dict:
    if period not in ("hoy","semana"):raise ValueError("Período inválido")
    k=sky_metricas.resumen(period)
    actions=verificador_acciones.get_recent_actions(100)
    receipts=sky_execution_metrics.summarize_action_receipts(actions)
    n=receipts["total_actions"]
    verified=receipts["verified"]
    failed=receipts["failed"]
    dispatched=receipts.get("dispatched",0)
    # Observed sample completion rate is not the global quality or end-to-end pass rate.
    rate=round(100*verified/n,1) if n else None
    model=k.get("modelo",{})
    cost=(model.get("cost_usd") if isinstance(model,dict) else None)
    return {
        "period":period,
        "actions_observed":n,
        "actions_verified":verified,
        "actions_failed":failed,
        "actions_dispatched_unverified":dispatched,
        "observed_verified_fraction_pct":rate,
        "observed_success_100_pct":bool(n>=20 and verified==n and failed==0 and dispatched==0),
        "percent_is_partial_sample_only":True,
        "recent_action_receipts":receipts,
        "api":k.get("api",{}),
        "voice":k.get("voz",{}),
        "assistant":k.get("asistente",{}),
        "model":model,
        "cost_usd_reported":cost,
        "cost_real_verified":bool(cost is not None and not model.get("cost_estimated",True)) if isinstance(model,dict) else False,
        "offline_simulations_are_not_hardware_tests":True,
        "windows_hardware_passed":None,
        "android_hardware_passed":None,
        "skillpack_29_live_services_verified":None,
        "global_100_score_certified":False,
        "quality_gate":"Sin pruebas físicas y verificación de cada cuenta/API no se puede certificar 100/100.",
    }
