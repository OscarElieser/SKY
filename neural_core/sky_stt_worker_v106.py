"""Private process entry point; invoked only by sky_stt_isolated_v106.

It accepts a normalized local WAV file, not URLs or arbitrary shell commands.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from . import sky_stt_local as base


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True)
    parser.add_argument('--language', default=None)
    arguments = parser.parse_args(argv)
    wav = Path(arguments.file)
    if wav.is_symlink() or not wav.is_file() or wav.suffix.lower() != '.wav':
        raise ValueError('Se requiere un WAV local normalizado')
    if wav.stat().st_size > base.MAX_SECONDS * 32000 + 10000:
        raise ValueError('El audio excede el límite')
    # stdout contains only JSON; exceptions must not leak credentials.
    result = base.transcribe(wav.read_bytes(), filename='audio.wav', language=arguments.language)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
