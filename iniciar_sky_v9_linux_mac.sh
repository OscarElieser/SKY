#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements_studio.txt
.venv/bin/python sky_preflight.py
echo "SKY v9.7: http://127.0.0.1:8765/sky"
echo "Estudio creativo: http://127.0.0.1:8765/creative (requiere FFmpeg para MP4)"
.venv/bin/python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765 --workers 1
