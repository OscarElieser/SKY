"""SKY Core is one policy for Windows and Android; static + fail-closed tests."""
import json
from pathlib import Path

from neural_core import sky_core_contract as core

ROOT = Path(__file__).resolve().parents[1]


def test_policy_snapshot_used_by_android_matches_python_byte_for_byte():
    shared = (ROOT / "shared/sky_core_contract_v1.json").read_bytes()
    android = (ROOT / "mobile/android-agent/app/src/main/assets/sky_core_contract_v1.json").read_bytes()
    assert shared == android
    data = json.loads(shared)
    assert data["product"] == "SKY IA"
    assert data["execution"] == "platform_native"
    assert data["unknown_action"] == "deny"
    assert data["security"]["independent_offline_mode"] is True
    assert data["security"]["biometric_voice_identity_verified"] is False


def test_owner_intent_needs_real_device_permission():
    assert core.inspect("open_app", "owner_typed")["reason"] == "platform_permission"
    ok = core.inspect("open_app", "owner_typed", platform_permission=True)
    assert ok["allowed"] and ok["reason"] == "authorized_by_policy_not_executed"
    assert not core.inspect("open_app", "model_output", platform_permission=True)["allowed"]
    assert not core.inspect("open_app", "web_page", platform_permission=True)["allowed"]


def test_sensitive_actions_reject_global_consent_without_per_action_approval():
    for action in ("delete_file", "send_message", "send_email", "social_publish",
                   "payment", "permissions_change", "remote_device_control", "file_write"):
        decision = core.inspect(action, "owner_spoken", platform_permission=True)
        assert not decision["allowed"] and decision["requires_confirmation"]
        decision = core.inspect(action, "owner_typed", platform_permission=True,
                                per_action_approved=True, local_ui_approved=True)
        assert decision["allowed"] and decision["requires_confirmation"]
        if core.contract()["actions"][action]["risk"] == "high":
            no_ui = core.inspect(action, "owner_spoken", platform_permission=True,
                                 per_action_approved=True)
            assert not no_ui["allowed"] and no_ui["reason"] == "local_ui_approval"


def test_untrusted_input_cannot_execute_even_when_approved():
    for origin in ("document", "web_page", "model_output", "external_message",
                   "remote_server", "owner_claimed"):
        assert not core.inspect("delete_file", origin, platform_permission=True,
                                per_action_approved=True)["allowed"]


def test_bypass_and_unknown_actions_fail_closed():
    for action in ("raw_shell", "bypass_screen_lock", "disable_play_protect",
                   "secret_exfiltration", "disable_security_controls"):
        assert core.inspect(action, "owner_typed", platform_permission=True,
                            per_action_approved=True)["reason"] == "forbidden"
    assert core.inspect("grant_full_control_unlimited", "owner_typed",
                        platform_permission=True)["reason"] == "unknown_action"


def test_never_inflate_unverified_action_receipts():
    assert core.canonical_receipt("ENVIADA_SIN_VERIFICAR") == "ENVIADA_SIN_VERIFICAR"
    assert core.canonical_receipt("COMPLETADA") == "ESTADO_DESCONOCIDO"
    assert core.canonical_receipt("VERIFICADA_LOCAL") == "VERIFICADA_LOCAL"
