"""Static Windows/Android parity contract; never substitute file existence for device tests."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "shared" / "sky_platform_parity.json"


def load():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_capabilities_are_traceable_to_both_platforms():
    data = load()
    assert data["schema_version"] == 1
    assert data["scope"] == "static_source_review"
    assert data["runtime_verified"] is False
    capabilities = data["capabilities"]
    assert len(capabilities) >= 20
    names = [item["id"] for item in capabilities]
    assert len(names) == len(set(names))
    for item in capabilities:
        assert item["label"] and item["note"]
        for platform in ("windows", "android"):
            section = item[platform]
            assert section["state"] in data["status_definition"]
            if section["state"] != "missing":
                assert section["evidence"], (item["id"], platform)
            for relative in section["evidence"]:
                source = (ROOT / relative).resolve()
                assert source.is_relative_to(ROOT.resolve()), relative
                assert source.is_file(), (item["id"], platform, relative)


def test_key_gaps_are_not_falsely_marked_as_complete():
    found = {item["id"]: item for item in load()["capabilities"]}
    for name in ("chat", "memory", "documents_docx", "spreadsheets_xlsx",
                 "presentations_pptx", "privacy_security"):
        assert found[name]["windows"]["state"] == "code"
        assert found[name]["android"]["state"] == "code"
    # Missing capabilities may later gain an implementation. Require evidence
    # whenever they are promoted; device acceptance remains independent.
    for name, platform in (
        ("multiagents", "android"),
        ("local_llm", "android"),
        ("shared_sync", "windows"),
        ("shared_sync", "android"),
        ("speaker_verification", "windows"),
        ("speaker_verification", "android"),
    ):
        entry = found[name][platform]
        if entry["state"] != "missing":
            assert entry["evidence"], (name, platform)


def test_no_static_review_claims_full_operational_equivalence():
    data = load()
    assert data["runtime_verified"] is False
    assert all(item["windows"]["state"] != "complete" and
               item["android"]["state"] != "complete"
               for item in data["capabilities"])
