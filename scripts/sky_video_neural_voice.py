"""SKY Video Studio optional premium neural TTS adapter.

Piper is an offline neural TTS engine. The user supplies a legally obtained,
compatible ONNX voice model and its config. No voice is bundled or downloaded.
"""
import argparse
import shutil
import subprocess
from pathlib import Path


def synthesize(text, output, *, model, config=None):
    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
        raise ValueError("Narration text must be 1-4000 characters")
    binary = shutil.which("piper")
    if not binary:
        raise RuntimeError("Piper TTS not installed")
    model = Path(model).resolve()
    if not model.is_file() or model.suffix.lower() != ".onnx":
        raise ValueError("A local Piper ONNX voice model is required")
    output = Path(output).resolve()
    if output.suffix.lower() != ".wav":
        raise ValueError("Output must be a WAV file")
    args = [binary, "--model", str(model), "--output_file", str(output)]
    if config:
        config = Path(config).resolve()
        if not config.is_file() or config.suffix.lower() != ".json":
            raise ValueError("Piper model config must be a JSON file")
        args += ["--config", str(config)]
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(args, input=text, text=True, check=True, timeout=180)
    if not output.is_file() or output.stat().st_size < 44:
        raise RuntimeError("Piper did not produce a valid WAV")
    return output


def main():
    parser = argparse.ArgumentParser(description="Synthesize narration with an installed Piper voice")
    parser.add_argument("script")
    parser.add_argument("output")
    parser.add_argument("--model", required=True)
    parser.add_argument("--config")
    args = parser.parse_args()
    print(synthesize(Path(args.script).read_text(encoding="utf-8"), args.output,
                     model=args.model, config=args.config))


if __name__ == "__main__":
    main()
