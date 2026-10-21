"""Puente explícito de voz/texto hacia el agente LOCAL ya autorizado.

No ejecuta shell, manipula archivos ni accede a cuentas. El usuario debe
iniciar el agente en su propio PC. La ejecución manos libres es opt-in.
"""
from __future__ import annotations

import os
from pathlib import Path

from .dispositivos import APP_OPTIONS, MEDIA_KEYS, call_device

SAFE_ACTIONS = frozenset({"status", "open_url", "launch_app", "media_key"})
_TOKEN_PATH = Path.home() / ".neuralt" / "device_agent.token"


def local_agent_credentials() -> tuple[str, str]:
    """Obtiene exclusivamente las credenciales locales del agente del propietario."""
    token = (os.getenv("SKY_DEVICE_TOKEN") or os.getenv("NEURALT_DEVICE_TOKEN") or "").strip()
    if not token:
        try:
            token = _TOKEN_PATH.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    if len(token) < 32:
        raise RuntimeError("El agente local no está emparejado. Iniciá agente_dispositivo.py en esta computadora.")
    port = int(os.getenv("SKY_DEVICE_PORT") or os.getenv("NEURALT_DEVICE_PORT") or "8765")
    if not 1 <= port <= 65535:
        raise ValueError("Puerto local inválido.")
    return f"http://127.0.0.1:{port}", token


def execute_safe_local(intent: dict) -> str:
    """Ejecuta solo órdenes conocidas, nunca rutas, comandos ni acciones sensibles."""
    if not isinstance(intent, dict):
        raise ValueError("Orden inválida.")
    action = intent.get("action")
    params = intent.get("params", {})
    if action not in SAFE_ACTIONS or not isinstance(params, dict):
        raise ValueError("Esta acción requiere un módulo específico y autorización.")
    if action == "launch_app" and params.get("app") not in APP_OPTIONS:
        raise ValueError("La aplicación no está autorizada.")
    if action == "media_key" and params.get("key") not in MEDIA_KEYS:
        raise ValueError("Tecla multimedia no autorizada.")
    if action == "open_url":
        from urllib.parse import urlsplit
        url = params.get("url")
        if not isinstance(url, str):
            raise ValueError("Dirección inválida.")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Solo se permiten direcciones HTTPS.")
    base, token = local_agent_credentials()
    result = call_device(base, token, action, params)
    if not result.get("ok"):
        raise RuntimeError("El agente no confirmó la operación.")
    if action == "open_url":
        return "He abierto la página en el navegador de tu equipo."
    if action == "launch_app":
        return "He solicitado abrir la aplicación en tu computadora."
    if action == "media_key":
        return "Envié la tecla multimedia a Windows. No puedo confirmar el estado del reproductor."
    return "SKY está conectado con tu equipo: " + str(result.get("device", "equipo local")) + "."
