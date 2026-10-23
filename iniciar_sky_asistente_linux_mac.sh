#!/usr/bin/env bash
# SKY v12 — SKY completo: interfaz HUD + agente del equipo + voz + API.
set -e
cd "$(dirname "$0")"
if [ ! -f ".venv/bin/python" ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
if [ ! -f "$HOME/.neuralt/device_agent_policy.json" ]; then
  .venv/bin/python agente_dispositivo.py --perfil multimedia --solo-config
fi
exec .venv/bin/python iniciar_sky_autonomo.py "$@"
