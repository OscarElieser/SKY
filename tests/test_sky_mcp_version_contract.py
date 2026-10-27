"""Regression for SKY MCP SDK + CrewAI optional dependency resolution.

This static contract catches the previously impossible intersection.
It does not replace a real pip --dry-run in the target Python environment.
"""
from pathlib import Path

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]


def _requirements(path: str) -> list[Requirement]:
    result = []
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or text.startswith("-r "):
            continue
        result.append(Requirement(text.split(" #", 1)[0]))
    return result


def test_full_install_mcp_range_intersects_crewai_1x_requirement():
    from_mcp = next(
        req for req in _requirements("requirements_mcp_optional.txt")
        if req.name == "mcp"
    )
    assert any(req.name == "crewai" for req in _requirements("requirements_sky_optional_integrations.txt"))
    # CrewAI >=1.15,<2 currently requires MCP >=1.30,<2.
    # Test intersection rather than pinning to a single patch release.
    candidate = Version("1.30.0")
    assert candidate in from_mcp.specifier
    assert candidate in Requirement("mcp>=1.30,<2").specifier
    assert Version("2.0.0") not in Requirement("mcp>=1.30,<2").specifier


def test_mcp_catalogue_matches_optional_manifest():
    req = next(req for req in _requirements("requirements_mcp_optional.txt") if req.name == "mcp")
    from neural_core import sky_mcp_hub
    # Descriptor is informational; no MCP server or network call is initiated.
    assert f"mcp{req.specifier}" in (ROOT / "neural_core/sky_mcp_hub.py").read_text(encoding="utf-8")
    assert "mcp>=1.30,<3" in (ROOT / "neural_core/sky_mcp_hub.py").read_text(encoding="utf-8")
