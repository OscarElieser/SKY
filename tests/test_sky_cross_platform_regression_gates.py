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
