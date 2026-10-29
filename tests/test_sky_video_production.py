"""End-to-end SKY Video Studio project tests."""
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sky_video_production.py"
spec = importlib.util.spec_from_file_location("sky_video_production", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_rejects_project_without_real_media(tmp_path):
    project = tmp_path / "project.json"
    project.write_text('{"title": "SKY"}', encoding="utf-8")
    with pytest.raises(ValueError, match="source scenes"):
        module.produce(project, tmp_path / "out.mp4")


@pytest.mark.skipif(not all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe", "espeak-ng")),
                    reason="Media and TTS tools required")
def test_produces_narrated_captioned_mp4(tmp_path):
    source = tmp_path / "scene.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=blue:s=320x568:r=30",
                    "-t", "1.5", "-c:v", "mpeg4", str(source)], check=True)
    project = tmp_path / "project.json"
    project.write_text(json.dumps({
        "format": "square", "fps": 30, "title": "SKY IA",
        "scenes": [{"file": "scene.mp4", "duration": 1.5}],
        "narration": "Hola, soy SKY.",
        "captions": [{"start": 0.1, "end": 1.2, "text": "SKY IA"}]
    }), encoding="utf-8")
    output = module.produce(project, tmp_path / "complete.mp4")
    assert output.is_file() and output.stat().st_size > 1000
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                            "-of", "json", str(output)], capture_output=True, text=True, check=True)
    assert {"video", "audio"} <= {stream["codec_type"] for stream in json.loads(probe.stdout)["streams"]}
