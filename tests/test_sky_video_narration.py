"""Offline narration adapter tests."""
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sky_video_narration.py"
spec = importlib.util.spec_from_file_location("sky_video_narration", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_rejects_empty_script(tmp_path):
    with pytest.raises(ValueError, match="text"):
        module.synthesize("", tmp_path / "voice.wav")


def test_rejects_invalid_voice(tmp_path):
    with pytest.raises(ValueError, match="voice"):
        module.synthesize("Hola", tmp_path / "voice.wav", voice="es;rm -rf /")


@pytest.mark.skipif(not shutil.which("espeak-ng"), reason="espeak-ng unavailable")
def test_produces_real_wav(tmp_path):
    result = module.synthesize("Hola, soy SKY.", tmp_path / "voice.wav")
    assert result.exists() and result.read_bytes()[:4] == b"RIFF"
    if shutil.which("ffprobe"):
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1",
             str(result)], check=True, capture_output=True, text=True)
        assert "pcm_" in probe.stdout
