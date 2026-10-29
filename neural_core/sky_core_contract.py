"""Shared SKY capability contract: policy inspection only, NEVER device execution.

Windows and Android consume identical declarative rules. A wake word or speech
transcription is NOT biometric proof; OS permissions and device approval remain
separate. Unknown actions and untrusted sources fail closed.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "shared" / "sky_core_contract_v1.json"


@lru_cache(maxsize=1)
def contract() -> dict:
    data = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "sky.core.contract.v1" or data.get("unknown_action") != "deny":
        raise ValueError("Contrato SKY ausente, desconocido o inseguro")
    if data.get("security", {}).get("model_output_grants_authorization") is not False:
        raise ValueError("Contrato SKY: las salidas de modelos no pueden autorizar acciones")
    return data


def inspect(action: str, origin: str, *, per_action_approved: bool = False,
            platform_permission: bool = False, local_ui_approved: bool = False) -> dict:
    """Return a decision; never treat this as having executed an operation."""
    data = contract()
    key = str(action or "").strip()
    if key in data["forbidden_actions"]:
        return {"allowed": False, "requires_confirmation": False, "reason": "forbidden"}
    definition = data["actions"].get(key)
    if definition is None:
        return {"allowed": False, "requires_confirmation": False, "reason": "unknown_action"}
    confirmation = definition["approval"] == "explicit_per_action"
    if origin not in data["allowed_origins"]:
        return {"allowed": False, "requires_confirmation": confirmation, "reason": "untrusted_origin"}
    if not platform_permission:
        return {"allowed": False, "requires_confirmation": confirmation, "reason": "platform_permission"}
    if confirmation and not per_action_approved:
        return {"allowed": False, "requires_confirmation": True, "reason": "per_action_approval"}
    if (definition["risk"] == "high" and
            data["security"].get("high_risk_requires_local_ui_confirmation") is not False and
            not local_ui_approved):
        return {"allowed": False, "requires_confirmation": True,
                "reason": "local_ui_approval"}
    return {"allowed": True, "requires_confirmation": confirmation,
            "reason": "authorized_by_policy_not_executed"}


def canonical_receipt(value: str) -> str:
    """Unknown or model-generated status never becomes verified success."""
    text = str(value or "").strip()
    return text if text in contract()["receipts"] else "ESTADO_DESCONOCIDO"
