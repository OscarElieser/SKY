"""SKY Video Studio: real, local media montage using FFmpeg.

Requires ffmpeg and ffprobe on PATH. Does not generate synthetic AI footage.
Input media must be supplied by the user or obtained through authorized providers.
"""
import argparse
import json
import math
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
        title = spec.get("title")
        if title:
            if not isinstance(title, str) or not title.strip() or len(title) > 100:
                raise ValueError("title must be 1-100 characters")
            title_duration = float(spec.get("title_duration", 2.5))
            if not math.isfinite(title_duration) or not 0.3 <= title_duration <= 10:
                raise ValueError("title_duration must be between 0.3 and 10 seconds")
            title_file = temp / "title.txt"
            title_file.write_text(title.replace("\\n", " ").replace("\\r", " "), encoding="utf-8")
            titled = temp / "titled.mp4"
            # Drawtext reads from a file, so punctuation is not interpolated into filters.
            font_size = max(24, round(width * 0.055))
            drawtext = (
                f"drawtext=textfile={title_file.as_posix()}:"
                f"fontcolor=white:fontsize={font_size}:"
                "box=1:boxcolor=black@0.55:boxborderw=22:"
                "x=(w-text_w)/2:y=(h-text_h)/2:"
                f"enable='between(t,0,{title_duration})'"
            )
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-i", str(silent), "-vf", drawtext, "-an",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                 "-pix_fmt", "yuv420p", str(titled)],
                check=True,
            )
            silent = titled
        # Burn optional, user-authored timed captions into the final video.
        captions = spec.get("captions", [])
        if captions:
            if not isinstance(captions, list) or len(captions) > 100:
                raise ValueError("captions must be a list of at most 100 entries")
            total = sum(float(scene.get("duration", 4)) for scene in scenes)
            if transition == "fade":
                total -= (len(scenes) - 1) * fade_seconds
            def stamp(seconds):
                millis = round(seconds * 1000)
                hours, rem = divmod(millis, 3_600_000)
                minutes, rem = divmod(rem, 60_000)
                secs, ms = divmod(rem, 1000)
                return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"
            def clean_text(value):
                if not isinstance(value, str) or not value.strip() or len(value) > 200:
                    raise ValueError("Caption text must be 1-200 characters")
                return value.replace("\r", " ").replace("\n", " ").strip()
            def srt_line(value):
                # SRT is plain text: prevent multiline injection and markup surprises.
                return clean_text(value).replace("<", "‹").replace(">", "›")
            lines = []
            previous_end = 0.0
            for index, caption in enumerate(captions, 1):
                start = float(caption["start"])
                end = float(caption["end"])
                if not all(math.isfinite(v) for v in (start, end)) or not (0 <= start < end <= total + 0.05):
                    raise ValueError("Caption timestamps must fit the rendered duration")
                if start < previous_end:
                    raise ValueError("Captions must be ordered and non-overlapping")
                previous_end = end
                lines.append(f"{index}\n{stamp(start)} --> {stamp(end)}\n{srt_line(caption['text'])}\n")
            subtitles = temp / "captions.srt"
            subtitles.write_text("\n".join(lines), encoding="utf-8")
            captioned = temp / "captioned.mp4"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-i", str(silent), "-vf", f"subtitles={subtitles.as_posix()}",
                 "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                 "-pix_fmt", "yuv420p", str(captioned)],
                check=True,
            )
            silent = captioned
        audio = spec.get("audio")
        voice = spec.get("voiceover")
        if audio or voice:
            audio_inputs = []
            if voice:
                voice_path = (manifest_path.parent / voice).resolve()
                if not voice_path.is_file():
                    raise ValueError("Voiceover file not found")
                audio_inputs += ["-i", str(voice_path)]
            if audio:
                audio_path = (manifest_path.parent / audio).resolve()
                if not audio_path.is_file():
                    raise ValueError("Music file not found")
                audio_inputs += ["-stream_loop", "-1", "-i", str(audio_path)]
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                       "-i", str(silent), *audio_inputs]
            if voice and audio:
                volume = float(spec.get("music_volume", 0.18))
                if not math.isfinite(volume) or not 0 <= volume <= 1:
                    raise ValueError("music_volume must be between 0 and 1")
                command += ["-filter_complex",
                            f"[1:a]aresample=48000[voice];[2:a]aresample=48000,volume={volume}[music];"
                            "[voice][music]amix=inputs=2:duration=longest:dropout_transition=0[a]",
                            "-map", "0:v:0", "-map", "[a]"]
            else:
                command += ["-map", "0:v:0", "-map", "1:a:0"]
                if audio:
                    volume = float(spec.get("music_volume", 1.0))
                    if not math.isfinite(volume) or not 0 <= volume <= 1:
                        raise ValueError("music_volume must be between 0 and 1")
                    command += ["-af", f"volume={volume}"]
            command += ["-t", str(sum(float(scene.get("duration", 4)) for scene in scenes)
                                      - ((len(scenes) - 1) * fade_seconds if transition == "fade" else 0)),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", str(output_path)]
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
