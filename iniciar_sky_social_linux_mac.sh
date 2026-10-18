#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements_social.txt
printf 'SKY SOCIAL: http://127.0.0.1:8765/community\n'
.venv/bin/python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765 --workers 1
