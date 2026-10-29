"""Guard SKY's stable repository layout without moving working modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    ".gitignore",
    "mobile/android-agent/README.md",
    "neural_core",
    "metaverse",
    "shared/sky_core_contract_v1.json",
    "shared/sky_platform_parity.json",
    "tests/test_sky_platform_parity.py",
    "docs/arquitectura/ESTRUCTURA_REPOSITORIO_SKY.md",
    ".github/workflows/sky-platform-parity.yml",
)


def test_stable_repository_paths_exist():
    for path in REQUIRED:
        assert (ROOT / path).exists(), path


def test_gitignore_protects_generated_files_and_credentials():
    patterns = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    patterns = {line.strip() for line in patterns if line.strip() and not line.startswith("#")}
    for expected in (".env", "*.pem", "*.key", "*.jks", "*.keystore",
                     "*.apk", "*.aab", "*.sqlite3", "__pycache__/", ".venv/"):
        assert expected in patterns, expected


def test_repository_map_links_to_existing_files():
    doc = (ROOT / "docs/arquitectura/ESTRUCTURA_REPOSITORIO_SKY.md").read_text(encoding="utf-8")
    assert "no migración completada" in doc
    assert "shared/sky_core_contract_v1.json" in doc
    assert "shared/sky_platform_parity.json" in doc
