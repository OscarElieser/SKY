#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
.venv/bin/python sky_live.py --intervalo 1800
