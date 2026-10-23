#!/usr/bin/env bash
# SKY v11.1 — Asistente Personal: agente de dispositivo + API + panel con voz.
set -e
cd "$(dirname "$0")"
if [ ! -f ".venv/bin/python" ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
PY=.venv/bin/python
if [ ! -f "$HOME/.neuralt/device_agent_policy.json" ]; then
  echo 'SKY: primera vez → perfil "multimedia" (música, volumen, apps, avisos). Cambialo con:'
  echo '     python agente_dispositivo.py --perfil completo --carpeta ~/Música'
  $PY agente_dispositivo.py --perfil multimedia --solo-config
fi
$PY agente_dispositivo.py & AGENTE=$!
trap 'kill $AGENTE 2>/dev/null || true' EXIT
URL='http://127.0.0.1:8765/asistente'
echo "SKY: panel del asistente en $URL"
( sleep 3; (command -v xdg-open >/dev/null && xdg-open "$URL") || (command -v open >/dev/null && open "$URL") || true ) &
$PY -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
