#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then exec .venv/bin/python agente_dispositivo.py; else exec python3 agente_dispositivo.py; fi
