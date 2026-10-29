"""SKY Video Studio: single-command, real offline production pipeline.

This orchestrator uses existing, separately testable media and TTS engines.
It never fabricates footage or silently substitutes placeholder content.
"""
import argparse
import importlib.util
import json
import tempfile
from pathlib import Path


def _load(name):
    script = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def produce(project_file, output_file):
    project_file = Path(project_file).resolve()
    project = json.loads(project_file.read_text(encoding="utf-8"))
    if not isinstance(project, dict):
        raise ValueError("Project must be a JSON object")
    if not project.get("scenes"):
        raise ValueError("Real source scenes are required; no placeholder footage")
    narration = project.get("narration")
    if narration is not None and (not isinstance(narration, str) or not narration.strip()):
        raise ValueError("narration must be non-empty text")
    with tempfile.TemporaryDirectory(prefix="sky-production-") as work:
        work = Path(work)
        manifest = dict(project)
        if narration:
            wav = work / "narration.wav"
            _load("sky_video_narration").synthesize(
                narration, wav,
                voice=project.get("narration_voice", "es"),
                speed=int(project.get("narration_speed", 155)),
            )
            manifest["voiceover"] = str(wav)
        manifest.pop("narration", None)
        manifest.pop("narration_voice", None)
        manifest.pop("narration_speed", None)
        # Resolve all user-supplied media relative to the project, not the temp manifest.
        for scene in manifest["scenes"]:
            scene["file"] = str((project_file.parent / scene["file"]).resolve())
        if manifest.get("audio"):
            manifest["audio"] = str((project_file.parent / manifest["audio"]).resolve())
        if manifest.get("voiceover") and not narration:
            manifest["voiceover"] = str((project_file.parent / manifest["voiceover"]).resolve())
        manifest_path = work / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return _load("sky_video_studio").render(manifest_path, output_file)


def main():
    parser = argparse.ArgumentParser(description="Produce a complete video from project JSON")
    parser.add_argument("project")
    parser.add_argument("output")
    args = parser.parse_args()
    print(produce(args.project, args.output))


if __name__ == "__main__":
    main()
