"""SKY Video Studio: real, local media montage using FFmpeg.

Requires ffmpeg and ffprobe on PATH. Does not generate synthetic AI footage.
Input media must be supplied by the user or obtained through authorized providers.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

FORMATS = {"vertical": (1080, 1920), "horizontal": (1920, 1080), "square": (1080, 1080)}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def render(manifest_path, output_path):
    manifest_path = Path(manifest_path).resolve()
    output_path = Path(output_path).resolve()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and ffprobe are required")
    spec = json.loads(manifest_path.read_text(encoding="utf-8"))
    width, height = FORMATS[spec.get("format", "vertical")]
    fps = int(spec.get("fps", 30))
    if fps < 24 or fps > 60:
        raise ValueError("fps must be between 24 and 60")
    scenes = spec.get("scenes", [])
    if not scenes or len(scenes) > 100:
        raise ValueError("Provide between 1 and 100 scenes")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sky-video-") as temp:
        temp = Path(temp)
        clips = []
        for index, scene in enumerate(scenes):
            media = (manifest_path.parent / scene["file"]).resolve()
            if not media.is_file() or media.suffix.lower() not in VIDEO_EXT | IMAGE_EXT:
                raise ValueError(f"Unsupported or missing media in scene {index}")
            duration = float(scene.get("duration", 4))
            if not 0.5 <= duration <= 120:
                raise ValueError("Scene duration must be 0.5 to 120 seconds")
            clip = temp / f"scene-{index:04}.mp4"
            filters = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p"
            )
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
            if media.suffix.lower() in IMAGE_EXT:
                command += ["-loop", "1", "-framerate", str(fps)]
            command += ["-i", str(media), "-t", str(duration), "-vf", filters,
                        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                        "-pix_fmt", "yuv420p", str(clip)]
            subprocess.run(command, check=True)
            clips.append(clip)
        transition = spec.get("transition", "cut")
        if transition not in {"cut", "fade"}:
            raise ValueError("transition must be cut or fade")
        if transition == "fade" and len(clips) > 1:
            fade_seconds = float(spec.get("transition_duration", 0.4))
            if not 0.1 <= fade_seconds <= 1.5:
                raise ValueError("transition_duration must be between 0.1 and 1.5")
            durations = [float(scene.get("duration", 4)) for scene in scenes]
            if any(d <= fade_seconds for d in durations):
                raise ValueError("Every scene must be longer than the transition")
            # A single xfade chain preserves full-frame output at the requested FPS.
            inputs = []
            for clip in clips:
                inputs += ["-i", str(clip)]
            filters = []
            current = "[0:v]"
            elapsed = durations[0]
            for index in range(1, len(clips)):
                target = f"[v{index}]"
                offset = round(elapsed - fade_seconds, 3)
                filters.append(
                    f"{current}[{index}:v]xfade=transition=fade:"
                    f"duration={fade_seconds}:offset={offset}{target}"
                )
                current = target
                elapsed += durations[index] - fade_seconds
            faded = temp / "faded.mp4"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
                 "-filter_complex", ";".join(filters), "-map", current,
                 "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                 "-pix_fmt", "yuv420p", str(faded)],
                check=True,
            )
            clips = [faded]
        concat = temp / "clips.txt"
        concat.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
        silent = temp / "silent.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "concat", "-safe", "0", "-i", str(concat),
                        "-c", "copy", str(silent)], check=True)
        audio = spec.get("audio")
        if audio:
            audio_path = (manifest_path.parent / audio).resolve()
            if not audio_path.is_file():
                raise ValueError("Audio file not found")
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                       "-i", str(silent), "-i", str(audio_path),
                       "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                       "-c:a", "aac", "-b:a", "192k", "-af", "afade=t=in:st=0:d=0.5",
                       "-shortest", "-movflags", "+faststart", str(output_path)]
        else:
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                       "-i", str(silent), "-c", "copy", "-movflags", "+faststart",
                       str(output_path)]
        subprocess.run(command, check=True)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Render a real MP4 from authorized media")
    parser.add_argument("manifest", help="JSON with format, scenes and optional audio")
    parser.add_argument("output", help="Destination MP4")
    args = parser.parse_args()
    print(render(args.manifest, args.output))


if __name__ == "__main__":
    main()
