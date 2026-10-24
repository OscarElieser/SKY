"""SKY Secure Device Hub — authenticated, consent-based device connectivity.

Reuses SKY's Windows agent, Home Assistant and Android USB instead of
pretending Wi-Fi/Bluetooth automatically grant control. No password guessing,
port scanning, interception, exploitation, camera surveillance, or stealth pairing.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_LOCK = threading.RLock()
MAX_DEVICES = 60
IR_TV_COMMANDS = frozenset({"power","volume_up","volume_down","mute","play","pause","stop","channel_up","channel_down"})
DEVICES = frozenset({"computer","laptop","phone","tablet","television","camera","iot","sensor","audio"})
TRANSPORTS = frozenset({"wifi","bluetooth_le","infrared","usb","ethernet","matter"})
CONNECTORS = frozenset({"sky_agent","home_assistant","adb_readonly","os_pairing_required"})
_HA_ENTITY = re.compile(r"^(light|switch|fan|media_player|scene|sensor|binary_sensor|remote|camera|climate)\.[a-z0-9_]{1,120}$")
_AGENT_NAME = re.compile(r"^[\w ._-]{2,80}$", re.UNICODE)
_SUPPORTED = {
    "sky_agent": frozenset({"wifi","ethernet"}),
    "home_assistant": frozenset({"wifi","ethernet","infrared","matter"}),
    "adb_readonly": frozenset({"usb"}),
    "os_pairing_required": frozenset({"bluetooth_le"}),
}


def _path() -> Path:
    return Path(os.getenv("SKY_DEVICE_HUB_DB") or ROOT / "local_data" / "sky_device_hub.sqlite3")


def _conn():
    file = _path()
    file.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(file, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=10000")
    con.execute("""CREATE TABLE IF NOT EXISTS owner_devices(
        id TEXT PRIMARY KEY, name TEXT NOT NULL,
        device_type TEXT NOT NULL, transport TEXT NOT NULL,
        connector TEXT NOT NULL, connection_ref TEXT NOT NULL,
        owner_attested INTEGER NOT NULL, status TEXT NOT NULL,
        created_at INTEGER NOT NULL, verified_at INTEGER
    )""")
    return con


def _validate_record(name: str, device_type: str, transport: str,
                     connector: str, connection_ref: str, owner_attested: bool) -> tuple:
    if owner_attested is not True:
        raise PermissionError("Confirmá que el equipo es tuyo o tenés permiso expreso del titular.")
    if not isinstance(name, str) or not 3 <= len(name.strip()) <= 80 or any(ord(c)<32 for c in name):
        raise ValueError("Nombre de dispositivo inválido.")
    if device_type not in DEVICES or transport not in TRANSPORTS or connector not in CONNECTORS:
        raise ValueError("Tipo, transporte o conector desconocido.")
    if transport not in _SUPPORTED[connector]:
        raise ValueError("Esta combinación de transporte y conector no está implementada.")
    if connector == "home_assistant":
        if not _HA_ENTITY.fullmatch(connection_ref):
            raise ValueError("Referencia Home Assistant no permitida. Ejemplo: media_player.sala.")
        if transport == "infrared" and not connection_ref.startswith("remote."):
            raise ValueError("El infrarrojo necesita un puente IR registrado como remote.*.")
    elif connector == "sky_agent":
        if not _AGENT_NAME.fullmatch(connection_ref):
            raise ValueError("Indicá el nombre exacto de un agente SKY previamente registrado.")
    elif connector == "os_pairing_required":
        if connection_ref:
            raise ValueError("No se almacenan identificadores Bluetooth hasta emparejarlos mediante el sistema operativo.")
    elif connector == "adb_readonly" and connection_ref:
        raise ValueError("SKY no guarda números de serie ni identificadores USB de teléfonos.")
    return name.strip(), device_type, transport, connector, connection_ref


def register(name: str, device_type: str, transport: str, connector: str,
             connection_ref: str = "", owner_attested: bool = False) -> dict:
    """Registers owner-declared inventory, NOT a claim that pairing succeeded."""
    fields = _validate_record(name, device_type, transport, connector,
                              connection_ref, owner_attested)
    with _LOCK, _conn() as con:
        if con.execute("SELECT COUNT(*) FROM owner_devices").fetchone()[0] >= MAX_DEVICES:
            raise ValueError("Límite de dispositivos registrados.")
        ident = "hub_" + uuid.uuid4().hex[:24]
        con.execute("""INSERT INTO owner_devices VALUES(?,?,?,?,?,?,?, ?,?,NULL)""",
                    (ident, *fields, 1, "registered_unverified", int(time.time())))
    return get(ident)


def get(ident: str) -> dict | None:
    if not re.fullmatch(r"hub_[0-9a-f]{24}", ident):
        return None
    with _conn() as con:
        row = con.execute("SELECT * FROM owner_devices WHERE id=?", (ident,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"], "name": row["name"], "device_type": row["device_type"],
        "transport": row["transport"], "connector": row["connector"],
        "connection_ref": row["connection_ref"],
        "owner_attested": bool(row["owner_attested"]),
        "status": row["status"],
        "verified_at": row["verified_at"],
        "control_permission_granted": False,
        "note": "Registro de confianza: control requiere el permiso específico del agente o del sistema IoT.",
    }


def devices() -> list[dict]:
    with _conn() as con:
        ids = [row["id"] for row in con.execute(
            "SELECT id FROM owner_devices ORDER BY created_at DESC, id DESC LIMIT ?", (MAX_DEVICES,))]
    return [item for ident in ids if (item := get(ident))]


def unregister(ident: str) -> bool:
    if not re.fullmatch(r"hub_[0-9a-f]{24}", ident):
        return False
    with _LOCK, _conn() as con:
        return bool(con.execute("DELETE FROM owner_devices WHERE id=?", (ident,)).rowcount)


def _mark_probed(ident: str) -> None:
    with _LOCK, _conn() as con:
        con.execute("UPDATE owner_devices SET status='verified_at_probe', verified_at=? WHERE id=?",
                    (int(time.time()), ident))


def probe(ident: str, *, device_token: str = "") -> dict:
    """Real connection probe to an already configured device, no state-changing commands."""
    item = get(ident)
    if not item:
        raise KeyError("Dispositivo no registrado.")
    connector = item["connector"]
    if connector == "sky_agent":
        from . import dispositivos
        linked = next(
            (d for d in dispositivos.paired_devices()
             if d.get("name") == item["connection_ref"] and not d.get("revoked")),
            None,
        )
        if linked is None:
            return {"connected": False, "status": "agent_not_registered",
                    "verified": False, "commands_sent": 0}
        if len(device_token.strip()) < 32:
            raise PermissionError("Este agente requiere su token específico, sin guardarlo en SKY Hub.")
        result = dispositivos.call_device(linked["url"], device_token, "status", timeout=5)
        verified = bool(result.get("ok") and result.get("agent") == "SKY Desktop Agent")
        if verified:
            _mark_probed(ident)
        return {"connected": verified, "status": "authenticated_agent" if verified else "unexpected_service",
                "verified": verified, "commands_sent": 0, "control_permission_granted": False}
    if connector == "home_assistant":
        from . import sky_home_assistant as ha
        if not ha.configurado():
            return {"connected": False, "status": "home_assistant_not_configured",
                    "verified": False, "commands_sent": 0}
        from urllib.parse import quote
        row = ha._peticion("GET", "/api/states/" + quote(item["connection_ref"], safe="."), timeout=5)
        verified = (isinstance(row, dict)
                    and row.get("entity_id") == item["connection_ref"]
                    and row.get("state") not in ("unavailable", "unknown", None))
        if verified:
            _mark_probed(ident)
        return {"connected": verified, "status": "authenticated_entity" if verified else "entity_unavailable",
                "verified": verified, "commands_sent": 0, "control_permission_granted": False}
    if connector == "adb_readonly":
        from . import sky_mobile_unlock
        response = sky_mobile_unlock.diagnose_usb(owner_attested=True)
        verified = bool(response.get("ok"))
        if verified:
            _mark_probed(ident)
        return {"connected": verified, "status": response.get("status"),
                "verified": verified, "commands_sent": 0,
                "read_only_diagnostics": response.get("device", {}) if verified else None,
                "control_permission_granted": False}
    return {"connected": False, "verified": False, "status": "pair_in_operating_system",
            "commands_sent": 0, "control_permission_granted": False,
            "reason": "Bluetooth requiere emparejamiento en el sistema y un adaptador específico para el servicio solicitado."}


async def discover_ble(*, owner_network_confirmed: bool, seconds: float = 3.0) -> dict:
    """BLE advertisements only; never connects, pairs or persists nearby device IDs."""
    if owner_network_confirmed is not True:
        raise PermissionError("La exploración Bluetooth debe autorizarla el propietario.")
    if not 2 <= seconds <= 6:
        raise ValueError("Duración permitida: 2 a 6 segundos.")
    try:
        from bleak import BleakScanner
    except ImportError:
        return {"available": False, "detected": 0, "devices": [],
                "status": "install_bleak_opt_in",
                "paired": False, "commands_sent": 0}
    found = await BleakScanner.discover(timeout=seconds)
    output = []
    for obj in found[:25]:
        name = (getattr(obj, "name", None) or "").strip()
        if name and 2 <= len(name) <= 70:
            output.append({"advertised_name": name[:70], "paired": False,
                           "control_available": False})
    return {"available": True, "detected": len(output), "devices": output,
            "paired": False, "commands_sent": 0,
            "note": "Exploración temporal; no se guardan MAC, direcciones, UUID ni identificadores de terceros."}


def _mdns_scan(seconds: float) -> list[dict]:
    """Browse a small fixed set of mDNS service types, no device HTTP requests."""
    from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    types = ["_googlecast._tcp.local.", "_airplay._tcp.local.",
             "_matter._tcp.local.", "_hap._tcp.local."]
    discovered: list[dict] = []
    class Listener(ServiceListener):
        def add_service(self, zc, service_type, name):
            if len(discovered) >= 25:
                return
            safe_name = str(name).split("._", 1)[0].strip()[:70]
            if safe_name:
                discovered.append({"advertised_name": safe_name,
                                   "service_type": service_type,
                                   "connected": False})
        def update_service(self, zc, service_type, name):
            return None
        def remove_service(self, zc, service_type, name):
            return None
    with Zeroconf() as zc:
        browser = ServiceBrowser(zc, types, Listener())
        try:
            time.sleep(seconds)
        finally:
            browser.cancel()
    return discovered[:25]


async def discover_wifi(*, owner_network_confirmed: bool, seconds: float = 3.0) -> dict:
    """Local multicast discovery only, no IP/port probes and no persistence."""
    if owner_network_confirmed is not True:
        raise PermissionError("Solo descubrir dispositivos en una red propia o expresamente autorizada.")
    if not 2 <= seconds <= 6:
        raise ValueError("Duración permitida: 2 a 6 segundos.")
    if importlib.util.find_spec("zeroconf") is None:
        return {"available": False, "detected": 0, "devices": [],
                "status": "install_zeroconf_opt_in", "connected": False}
    found = await asyncio.to_thread(_mdns_scan, seconds)
    return {"available": True, "detected": len(found), "devices": found,
            "connected": False, "status": "advertisements_only"}



def validate_ir_command(ident: str, command: str) -> dict:
    """Only a previously declared TV via an approved Home Assistant IR bridge."""
    item = get(ident)
    if item is None:
        raise KeyError("Televisor no registrado.")
    if not (
        item["owner_attested"] and item["device_type"] == "television"
        and item["transport"] == "infrared" and item["connector"] == "home_assistant"
        and item["connection_ref"].startswith("remote.")
    ):
        raise PermissionError("El control IR exige un televisor y puente autorizado.")
    if command not in IR_TV_COMMANDS:
        raise ValueError("Comando IR no admitido por el perfil seguro de televisión.")
    return item


def send_ir_tv(ident: str, command: str) -> dict:
    """Dispatch ONE whitelisted command through the owner's configured IR bridge.

    A service call proves dispatch only, not that infrared physically arrived.
    Must be called AFTER consuming an owner approval token in the API route.
    """
    item = validate_ir_command(ident, command)
    from . import sky_home_assistant as ha
    if not ha.configurado():
        raise RuntimeError("Home Assistant no está configurado o no tiene token válido.")
    from urllib.parse import quote
    ref = item["connection_ref"]
    state = ha._peticion("GET", "/api/states/" + quote(ref, safe="."), timeout=5)
    if not isinstance(state, dict) or state.get("entity_id") != ref or state.get("state") in ("unavailable","unknown",None):
        raise RuntimeError("El puente infrarrojo no está disponible.")
    ha._peticion("POST", "/api/services/remote/send_command",
                {"entity_id": ref, "device": "television", "command": command}, timeout=7)
    return {
        "ok": True, "status": "SENT", "verified": False,
        "hub_id": ident, "command": command,
        "message": "SKY envió el comando por el puente IR autorizado. El televisor aún no confirmó la acción.",
    }


def catalogue() -> dict:
    from . import sky_home_assistant, dispositivos
    return {
        "owner": "SKY CORE",
        "modes": {
            "wifi": {"existing_agent_registry": len(dispositivos.paired_devices()),
                     "home_assistant_configured": sky_home_assistant.configurado(),
                     "mdns_optional_library": importlib.util.find_spec("zeroconf") is not None},
            "bluetooth_le": {"bleak_installed": importlib.util.find_spec("bleak") is not None,
                             "discovery_only": True, "os_pairing_required": True},
            "infrared": {"requires_physical_emitter_or_bridge": True,
                          "home_assistant_bridge_supported": True,
                          "direct_ir_emitter_implemented": False, "authenticated_bridge_tv_commands": sorted(IR_TV_COMMANDS)},
            "matter": {"commissioning_implemented_in_sky": False,
                       "existing_home_assistant_entities_supported": True},
            "usb": {"android_readonly_adb_available": __import__("shutil").which("adb") is not None},
        },
        "connectors": sorted(CONNECTORS),
        "types": sorted(DEVICES),
        "no_password_guessing": True,
        "no_unauthorized_scanning": True,
        "no_auto_pairing": True,
        "no_auto_commands": True,
        "note": "Solo SKY es la interfaz de usuario. El estado de descubrimiento nunca equivale a emparejamiento.",
    }


def security_audit_plan(*, asset_type: str, owner_attested: bool) -> dict:
    """Owner-approved defensive checklist; does not probe, exploit or scan a target."""
    if owner_attested is not True:
        raise PermissionError("La evaluación requiere autorización del propietario.")
    checks = {
        "website": ["Inventariar dominios propios y proveedores autorizados",
                    "Comprobar MFA, usuarios y permisos con los administradores",
                    "Revisar actualizaciones de CMS y dependencias",
                    "Analizar TLS, certificados y cabeceras mediante un verificador autorizado",
                    "Consultar registros y establecer copias de seguridad",
                    "Documentar hallazgos y plan de correcciones"],
        "phone": ["Verificar propiedad y actualizaciones oficiales",
                  "Comprobar cifrado, bloqueo de pantalla y MFA",
                  "Revisar permisos y aplicaciones instaladas con consentimiento",
                  "Respaldar datos y confirmar estado de recuperación de cuenta",
                  "No modificar IMEI ni evadir bloqueo de activación"],
        "computer": ["Confirmar autorización y alcance de equipos",
                     "Revisar parches, antivirus/EDR, cuentas y MFA",
                     "Verificar firewall, conexiones remotas permitidas y copias de seguridad",
                     "Revisar eventos locales con consentimiento",
                     "Entregar informe de endurecimiento y recuperación"],
        "iot": ["Inventariar cámaras y sensores autorizados",
                "Cambiar contraseñas predeterminadas por credenciales fuertes",
                "Actualizar firmware oficial",
                "Segmentar IoT de equipos personales mediante red invitada/VLAN",
                "Deshabilitar exposición pública innecesaria",
                "Comprobar copia de configuración y políticas de retención"],
    }
    if asset_type not in checks:
        raise ValueError("Tipo de auditoría admitido: website, phone, computer, iot.")
    return {"owner": "SKY", "asset_type": asset_type,
            "authorized": True, "steps": checks[asset_type],
            "network_probes_performed": False,
            "vulnerabilities_verified": False,
            "changes_made": False,
            "message": "Plan defensivo preparado. Las pruebas activas requieren alcance técnico y autorización específica."}
