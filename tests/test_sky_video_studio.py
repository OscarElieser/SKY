"""Real FFmpeg smoke test for SKY Video Studio."""
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sky_video_studio.py"
spec = importlib.util.spec_from_file_location("sky_video_studio", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_rejects_invalid_fps(tmp_path):
    manifest = tmp_path / "video.json"
    manifest.write_text(json.dumps({"fps": 5, "scenes": [{"file": "missing.jpg"}]}), encoding="utf-8")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg unavailable")
    with pytest.raises(ValueError, match="fps"):
        module.render(manifest, tmp_path / "out.mp4")


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg and ffprobe required")
def test_renders_real_mp4(tmp_path):
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=blue:s=320x568:r=30",
                    "-t", "0.6", "-c:v", "mpeg4", str(source)], check=True)
    manifest = tmp_path / "video.json"
    manifest.write_text(json.dumps({"format": "vertical", "fps": 30,
                                     "scenes": [{"file": "source.mp4", "duration": 0.6}]}),
                        encoding="utf-8")
    output = module.render(manifest, tmp_path / "output.mp4")
    assert output.is_file() and output.stat().st_size > 1000
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "json", str(output)],
                           check=True, capture_output=True, text=True)
    stream = json.loads(probe.stdout)["streams"][0]
    assert (stream["width"], stream["height"]) == (1080, 1920)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg and ffprobe required")
def test_renders_crossfade_between_scenes(tmp_path):
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=blue:s=320x568:r=30",
                    "-t", "1.5", "-c:v", "mpeg4", str(source)], check=True)
    manifest = tmp_path / "video.json"
    manifest.write_text(json.dumps({
        "format": "square", "fps": 30, "transition": "fade",
        "transition_duration": 0.3,
        "scenes": [{"file": "source.mp4", "duration": 1.5},
                   {"file": "source.mp4", "duration": 1.5}]
    }), encoding="utf-8")
    output = module.render(manifest, tmp_path / "fade.mp4")
    assert output.exists() and output.stat().st_size > 1000
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "json", str(output)],
                           check=True, capture_output=True, text=True)
    stream = json.loads(probe.stdout)["streams"][0]
    assert (stream["width"], stream["height"]) == (1080, 1080)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg and ffprobe required")
def test_renders_captioned_mp4(tmp_path):
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=black:s=320x568:r=30",
                    "-t", "1.5", "-c:v", "mpeg4", str(source)], check=True)
    manifest = tmp_path / "video.json"
    manifest.write_text(json.dumps({
        "format": "vertical", "fps": 30,
        "scenes": [{"file": "source.mp4", "duration": 1.5}],
        "captions": [{"start": 0.1, "end": 1.2, "text": "SKY Video Studio"}]
    }), encoding="utf-8")
    output = module.render(manifest, tmp_path / "captions.mp4")
    assert output.exists() and output.stat().st_size > 1000


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg and ffprobe required")
def test_renders_voiceover_and_music_mix(tmp_path):
    video = tmp_path / "source.mp4"
    voice = tmp_path / "voice.wav"
    music = tmp_path / "music.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=blue:s=320x568:r=30",
                    "-t", "1", "-c:v", "mpeg4", str(video)], check=True)
    for filename, frequency in [(voice, 440), (music, 220)]:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=48000",
                        "-t", "1", str(filename)], check=True)
    manifest = tmp_path / "video.json"
    manifest.write_text(json.dumps({
        "format": "square", "fps": 30,
        "scenes": [{"file": "source.mp4", "duration": 1}],
        "voiceover": "voice.wav", "audio": "music.wav", "music_volume": 0.15
    }), encoding="utf-8")
    output = module.render(manifest, tmp_path / "mixed.mp4")
    assert output.exists() and output.stat().st_size > 1000
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                            "-of", "json", str(output)], capture_output=True, text=True, check=True)
    assert {"video", "audio"} <= {stream["codec_type"] for stream in json.loads(probe.stdout)["streams"]}


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg and ffprobe required")
def test_renders_title_overlay(tmp_path):
    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=blue:s=320x568:r=30",
                    "-t", "1", "-c:v", "mpeg4", str(source)], check=True)
    manifest = tmp_path / "video.json"
    manifest.write_text(json.dumps({
        "format": "square", "fps": 30, "title": "SKY IA",
        "title_duration": 0.8,
        "scenes": [{"file": "source.mp4", "duration": 1}]
    }), encoding="utf-8")
    output = module.render(manifest, tmp_path / "title.mp4")
    assert output.exists() and output.stat().st_size > 1000
