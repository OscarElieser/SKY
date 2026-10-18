#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -f ".venv/bin/python" ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
.venv/bin/python -c 'import fastapi,uvicorn,httpx' || .venv/bin/python -m pip install 'fastapi>=0.115,<1' 'uvicorn>=0.34,<1' 'httpx>=0.27,<1'
echo 'SKY: Abrí http://127.0.0.1:8765 y usá la clave de local_data/sky_api_token.txt'
.venv/bin/python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
