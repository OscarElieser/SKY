"""Contract tests for the authenticated SKY Video Studio API."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_video_studio_router_requires_owner_auth():
    source = (ROOT / "metaverse" / "video_studio_api.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "dependencies=[Depends(require_key)]" in source
    assert "creative.asset_path(" in source
    assert "subprocess.run(" not in source


def test_sky_api_registers_video_studio():
    source = (ROOT / "metaverse" / "api.py").read_text(encoding="utf-8")
    assert "app.include_router(sky_video_studio_router)" in source


def test_video_studio_has_no_client_paths():
    source = (ROOT / "metaverse" / "video_studio_api.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    scene = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Scene")
    fields = {n.target.id for n in scene.body if isinstance(n, ast.AnnAssign)
              and isinstance(n.target, ast.Name)}
    assert fields == {"asset_id", "duration"}
