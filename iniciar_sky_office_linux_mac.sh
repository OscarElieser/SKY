#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements_office.txt
printf 'SKY Office Studio: http://127.0.0.1:8765/office\n'
.venv/bin/python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765 --workers 1
