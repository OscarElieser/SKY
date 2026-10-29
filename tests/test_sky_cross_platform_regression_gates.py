"""Regression gates for SKY's cross-platform capability inventory.

Static checks only. Device acceptance remains separate.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "shared" / "sky_platform_parity.json"
REQUIRED = {
    "chat", "memory", "voice", "speaker_verification", "app_launch",
    "app_interaction", "music", "documents_docx", "spreadsheets_xlsx",
    "presentations_pptx", "pdf", "multifile", "research", "education",
    "multiagents", "learning", "social", "privacy_security", "shared_sync",
}
UNVERIFIED = {"missing", "limited", "code"}


def _inventory():
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def test_critical_capabilities_remain_in_inventory():
    data = _inventory()
    indexed = {entry["id"]: entry for entry in data["capabilities"]}
    assert REQUIRED <= indexed.keys(), sorted(REQUIRED - indexed.keys())
    assert data["runtime_verified"] is False
    assert data["scope"] == "static_source_review"


def test_both_platforms_keep_honest_evidence():
    for entry in _inventory()["capabilities"]:
        for platform in ("windows", "android"):
            details = entry[platform]
            assert details["state"] in UNVERIFIED, (entry["id"], platform)
            if details["state"] == "missing":
                assert not details["evidence"], (entry["id"], platform)
            else:
                assert details["evidence"], (entry["id"], platform)
                for relative in details["evidence"]:
                    candidate = (ROOT / relative).resolve()
                    assert candidate.is_relative_to(ROOT), relative
                    assert candidate.is_file(), relative


def test_missing_security_capabilities_are_not_claimed_as_ready():
    indexed = {entry["id"]: entry for entry in _inventory()["capabilities"]}
    for capability in ("speaker_verification", "shared_sync"):
        for platform in ("windows", "android"):
            assert indexed[capability][platform]["state"] == "missing"


def test_shared_security_contract_denies_unknown_and_untrusted_actions():
    contract = json.loads((ROOT / "shared" / "sky_core_contract_v1.json").read_text(encoding="utf-8"))
    assert contract["unknown_action"] == "deny"
    assert contract["security"]["model_output_grants_authorization"] is False
    assert contract["security"]["unverified_receipt_is_not_success"] is True
    assert contract["security"]["require_platform_permissions"] is True
    assert contract["security"]["high_risk_requires_local_ui_confirmation"] is True
    assert contract["security"]["shared_owner_data_by_default"] is False
    assert contract["security"]["credentials_in_source"] is False
    assert contract["security"]["independent_offline_mode"] is True
    assert "model_output" in contract["untrusted_origins"]
    assert "web_page" in contract["untrusted_origins"]
    assert "document" in contract["untrusted_origins"]
    assert "raw_shell" in contract["forbidden_actions"]
    assert "disable_play_protect" in contract["forbidden_actions"]
    assert "bypass_screen_lock" in contract["forbidden_actions"]
    assert "secret_exfiltration" in contract["forbidden_actions"]


def test_high_risk_actions_require_individual_approval():
    contract = json.loads((ROOT / "shared" / "sky_core_contract_v1.json").read_text(encoding="utf-8"))
    for name in ("delete_file", "send_message", "send_email", "social_publish",
                 "payment", "permissions_change", "remote_device_control"):
        action = contract["actions"][name]
        assert action["risk"] == "high", name
        assert action["approval"] == "explicit_per_action", name
    assert contract["security"]["explicit_approval_is_per_action"] is True
