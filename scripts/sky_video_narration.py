"""Offline, explicit SKY Video Studio narration adapter.

Uses a locally installed espeak-ng binary. No cloud keys, hidden downloads,
or fabricated voice. The generated WAV can be passed as 'voiceover' to
scripts/sky_video_studio.py.
"""
import argparse
import shutil
import subprocess
from pathlib import Path


def synthesize(text: str, output: str | Path, *, voice: str = "es", speed: int = 155) -> Path:
    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
        raise ValueError("Narration text must be between 1 and 4000 characters")
    if not isinstance(voice, str) or not voice.replace("-", "").replace("+", "").isalnum():
        raise ValueError("Invalid voice code")
    if not 80 <= speed <= 300:
        raise ValueError("Speech speed must be 80-300 words per minute")
    executable = shutil.which("espeak-ng")
    if not executable:
        raise RuntimeError("espeak-ng not installed; configure an authorized TTS provider")
    output = Path(output).resolve()
    if output.suffix.lower() != ".wav":
        raise ValueError("Output must be WAV")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Feed the script on stdin; never interpolate user content into a shell command.
    subprocess.run([executable, "-v", voice, "-s", str(speed), "-w", str(output),
                    "--stdin"], input=text, text=True, check=True, timeout=120)
    if not output.is_file() or output.stat().st_size < 44:
        raise RuntimeError("Speech synthesis produced no valid WAV")
    return output


def main():
    parser = argparse.ArgumentParser(description="Generate offline narration WAV")
    parser.add_argument("script", help="UTF-8 narration text file")
    parser.add_argument("output", help="Destination WAV")
    parser.add_argument("--voice", default="es")
    parser.add_argument("--speed", type=int, default=155)
    args = parser.parse_args()
    print(synthesize(Path(args.script).read_text(encoding="utf-8"),
                     args.output, voice=args.voice, speed=args.speed))


if __name__ == "__main__":
    main()
