#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export SKY_CREATIVE_WORKER=0
exec python3 sky_render_worker.py
