"""Piper neural voice integration validation without pretending a model is installed."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sky_video_neural_voice.py"
spec = importlib.util.spec_from_file_location("sky_video_neural_voice", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_empty_text_rejected(tmp_path):
    with pytest.raises(ValueError, match="Narration"):
        module.synthesize("", tmp_path / "out.wav", model=tmp_path / "voice.onnx")


def test_neural_voice_requires_binary_or_model(tmp_path):
    with pytest.raises((RuntimeError, ValueError)):
        module.synthesize("Hola SKY", tmp_path / "out.wav", model=tmp_path / "missing.onnx")
