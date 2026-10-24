"""SKY Mobile Unlock Assistant — legal carrier-lock diagnosis, not lock bypass.

Works only on a phone the owner may lawfully service. Read-only ADB on
explicitly USB-authorized Android devices. Does not execute any unlock code,
flash firmware, modify IMEI, FRP, activation lock or SIM network restrictions.
Real SIM/network unlock generally requires the original carrier's approval.
"""
from __future__ import annotations

import platform
import re
import shutil
import subprocess
from typing import Any

ADVISORIES = {
    "ATT": {
        "display_name": "AT&T (Estados Unidos)",
        "unlock_url": "https://www.att.com/deviceunlock/",
        "instructions": "Consultar elegibilidad y enviar solicitud al portal de AT&T; seguir instrucciones emitidas por el operador.",
    },
    "T_MOBILE": {
        "display_name": "T-Mobile US",
        "unlock_url": "https://es.t-mobile.com/support/devices/unlock-your-mobile-wireless-device",
        "instructions": "Comprobar estado en la cuenta de T-Mobile y ejecutar desbloqueo oficial si cumple sus requisitos.",
    },
    "VERIZON": {
        "display_name": "Verizon US",
        "unlock_url": "https://espanol.verizon.com/support/device-unlocking-policy/",
        "instructions": "Consultar la política vigente y comprobar si el equipo ya puede recibir otras SIM.",
    },
    "UNKNOWN": {
        "display_name": "Operador no identificado",
        "unlock_url": None,
        "instructions": "Identificar el operador que vendió o financió el teléfono y solicitarle su liberación.",
    },
}
TARGETS = {
    "CLARO_NI": "Claro Nicaragua",
    "TIGO_NI": "Tigo Nicaragua",
}
CARRIER_STATES = {
    "unknown": "Bloqueo de red no comprobado.",
    "sim_not_supported": "El mensaje de SIM no admitida puede indicar bloqueo de operador.",
    "network_unlock_requested": "El teléfono solicita una clave de desbloqueo de red; no introducir códigos no autorizados.",
    "no_service": "No hay servicio: puede deberse a bloqueo, incompatibilidad, cobertura, activación o SIM defectuosa.",
    "sim_accepted": "El teléfono acepta la SIM, pero falta comprobar llamadas y datos.",
    "no_sim_restrictions": "El propietario indica que el equipo muestra ausencia de restricciones SIM; verificar red y compatibilidad.",
}
_SAFE_SERIAL = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_PROPS = {
    "manufacturer": "ro.product.manufacturer",
    "model": "ro.product.model",
    "android_version": "ro.build.version.release",
    "device": "ro.product.device",
    "sim_state": "gsm.sim.state",
}


def _check_owner(attested: bool) -> None:
    if attested is not True:
        raise PermissionError("Confirmá que tenés autorización para diagnosticar este dispositivo.")


def _adb_binary() -> str | None:
    return shutil.which("adb")


def _run_readonly(command: list[str], *, timeout: int = 7) -> str:
    try:
        result = subprocess.run(
            command, shell=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=timeout, encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        raise RuntimeError("Android Platform Tools no respondió de manera segura.") from exc
    if result.returncode != 0:
        # Never echo diagnostics: may contain serials and other private identifiers.
        raise RuntimeError("ADB devolvió un error al consultar el dispositivo.")
    return result.stdout[:12_000]


def diagnose_usb(*, owner_attested: bool) -> dict[str, Any]:
    """Inspect one USB-authorized Android device; no IMEI, MAC, photos or contacts."""
    _check_owner(owner_attested)
    adb = _adb_binary()
    if not adb:
        return {
            "ok": False, "status": "adb_not_installed", "platform": platform.system(),
            "message": "Instalá Android SDK Platform Tools desde Google y habilitá depuración USB bajo tu control.",
            "carrier_lock_state": "unknown", "changes_made": False,
            "unlock_performed": False,
        }
    output = _run_readonly([adb, "devices"])
    devices: list[tuple[str, str]] = []
    for line in output.splitlines()[1:]:
        parts = line.strip().split()
        if len(parts) >= 2 and _SAFE_SERIAL.fullmatch(parts[0]):
            if parts[1] in {"device", "unauthorized", "offline"}:
                devices.append((parts[0], parts[1]))
    if len(devices) != 1:
        return {
            "ok": False, "status": "one_device_required",
            "connected_device_count": len(devices),
            "message": "Conectá exactamente un teléfono Android autorizado por USB.",
            "carrier_lock_state": "unknown", "changes_made": False, "unlock_performed": False,
        }
    serial, state = devices[0]
    if state != "device":
        return {
            "ok": False, "status": f"adb_{state}",
            "message": ("Desbloqueá el teléfono y autorizá la depuración USB en su pantalla."
                        if state == "unauthorized" else "Reconectá el teléfono y verificá el cable USB."),
            "carrier_lock_state": "unknown", "changes_made": False, "unlock_performed": False,
        }
    props: dict[str, str] = {}
    for name, prop in _PROPS.items():
        value = _run_readonly([adb, "-s", serial, "shell", "getprop", prop]).strip()
        props[name] = re.sub(r"[\x00-\x1f]", "", value)[:120]
    return {
        "ok": True, "status": "android_usb_authorized",
        "platform": platform.system(),
        "device": props,
        "carrier_lock_state": "unknown",
        "carrier_lock_verified": False,
        "sim_state_is_not_carrier_unlock_proof": True,
        "message": ("SKY identificó el Android mediante ADB. Su bloqueo de operador no se "
                    "puede comprobar de forma universal por USB. Consultá también la pantalla y el operador."),
        "private_identifiers_collected": False,
        "changes_made": False,
        "unlock_performed": False,
    }


def plan(*, owner_attested: bool, source_carrier: str,
         target_carrier: str, os_family: str = "android",
         observed_state: str = "unknown") -> dict[str, Any]:
    """Guide an authorized carrier unlock with factual external dependencies."""
    _check_owner(owner_attested)
    if source_carrier not in ADVISORIES:
        raise ValueError("Operador estadounidense no reconocido.")
    if target_carrier not in TARGETS:
        raise ValueError("Seleccioná Claro Nicaragua o Tigo Nicaragua.")
    if os_family not in ("android", "iphone"):
        raise ValueError("Sistema operativo no reconocido.")
    if observed_state not in CARRIER_STATES:
        raise ValueError("Estado reportado no reconocido.")

    info = ADVISORIES[source_carrier]
    steps = [
        "Confirmar propiedad/consentimiento y comprobar que el dispositivo no tenga restricciones legales o reporte de pérdida o robo.",
        ("En iPhone: Configuración > General > Información > Bloqueo de operador. "
         "En Android: revisar ajustes de red o el mensaje mostrado al insertar otra SIM."),
        f"Solicitar o comprobar el desbloqueo oficial con {info['display_name']}.",
        "Una vez confirmado por el operador, usar la SIM o eSIM de destino y completar cualquier activación oficial indicada.",
        f"Comprobar compatibilidad de bandas y soporte VoLTE del modelo con {TARGETS[target_carrier]}; probar llamadas, SMS y datos móviles.",
    ]
    return {
        "handled_by": "SKY",
        "source_carrier": info["display_name"],
        "destination": TARGETS[target_carrier],
        "os_family": os_family,
        "owner_reported_state": observed_state,
        "state_explanation": CARRIER_STATES[observed_state],
        "official_unlock_url": info["unlock_url"],
        "official_instructions": info["instructions"],
        "instructions": steps,
        "unlock_performed": False,
        "carrier_unlock_verified": False,
        "usb_diagnostics_can_unlock": False,
        "can_bypass_activation_or_pin": False,
        "imei_rewrite_supported": False,
        "needs_original_carrier": True,
        "message": ("SKY puede diagnosticar y guiar la liberación del operador original, "
                    "pero no puede prometer eliminar bloqueos de red mediante USB."),
    }



def att_s23fe_tigo(*, owner_attested: bool,
                   observed_state: str = "unknown",
                   owner_reports_paid_off: bool | None = None,
                   att_unlock_confirmation: bool = False,
                   tigo_calls_work: bool = False,
                   tigo_data_work: bool = False,
                   tigo_sms_work: bool = False) -> dict[str, Any]:
    """Tailored S23 FE flow, never inventing carrier approval or a successful unlock.

    Optional flags are user reports, not evidence the SKY agent inspected.
    No IMEI or other secret identifier is accepted, stored or sent to a portal.
    """
    _check_owner(owner_attested)
    if observed_state not in CARRIER_STATES:
        raise ValueError("Estado de bloqueo no reconocido.")
    base = plan(
        owner_attested=True, source_carrier="ATT",
        target_carrier="TIGO_NI", os_family="android",
        observed_state=observed_state,
    )
    eligibility = (
        "AT&T exige normalmente: compra hace al menos 60 días, equipo totalmente "
        "pagado, no reportado como perdido/robado y cuenta sin restricciones."
    )
    checkpoints = [
        {
            "step":"diagnose",
            "status":"ready_for_owner_check",
            "action":"Con el S23 FE encendido, revisá Ajustes > Acerca del teléfono > Información de software > Versión de software del proveedor de servicio. AT&T publica la interpretación del sufijo ATT/ATT para Samsung de esta generación.",
        },
        {
            "step":"carrier_eligibility",
            "status":"owner_reports_paid_off" if owner_reports_paid_off is True
                     else "owner_reports_unpaid" if owner_reports_paid_off is False
                     else "not_verified",
            "action":"Comprobá los requisitos de elegibilidad directamente con AT&T.",
        },
        {
            "step":"request_unlock",
            "status":"owner_reports_carrier_confirmation" if att_unlock_confirmation
                     else "pending_official_carrier_decision",
            "action":"Abrí https://www.att.com/deviceunlock/; AT&T puede aceptar solicitudes de no clientes si el equipo es elegible. Introducí el IMEI solo en el portal oficial, no en SKY.",
        },
        {
            "step":"finish_on_device",
            "status":"pending_verification",
            "action":"Seguí las instrucciones de AT&T para Samsung. Si se entrega un código, no lo adivinés ni intentés múltiples códigos incorrectos. Probá con SIM Tigo tras la liberación.",
        },
        {
            "step":"tigo_network_test",
            "status":"owner_reports_full_service" if (
                att_unlock_confirmation and
                tigo_calls_work and tigo_data_work and tigo_sms_work
            ) else "needs_real_network_tests",
            "action":"Con Tigo, comprobá registro en red, llamadas, SMS y datos móviles. Revisá APN solo si la SIM ya es aceptada y faltan datos.",
        },
    ]
    reported_ready = bool(att_unlock_confirmation and tigo_calls_work
                          and tigo_data_work and tigo_sms_work)
    return {
        **base,
        "device":"Samsung Galaxy S23 FE",
        "device_family":"SM-S711 (confirmar la variante en Ajustes)",
        "origin_carrier":"AT&T US",
        "target_sim":"Tigo Nicaragua",
        "carrier_policy":eligibility,
        "checkpoints":checkpoints,
        "att_unlock_confirmation_owner_reported":bool(att_unlock_confirmation),
        "owner_reports_tigo_service":reported_ready,
        "sky_independently_verified_unlock":False,
        "carrier_unlock_verified":False,
        "unlock_performed":False,
        "usb_can_release_carrier_lock":False,
        "owner_guidance":(
            "Si AT&T aprueba la liberación, SKY puede verificar las señales que "
            "el equipo permita y ayudarte a configurar Tigo; no puede liberar "
            "el bloqueo impuesto por AT&T sin su autorización."
        ),
    }

def catalogue() -> dict[str, Any]:
    return {
        "product": "SKY Mobile Unlock Assistant",
        "scope": "authorized_carrier_unlock_diagnosis",
        "android_usb_readonly": True,
        "iphone_usb_unlock": False,
        "carrier_lock_readable_via_adb": False,
        "actual_network_unlock_implemented": False,
        "supports_claro_nicaragua": True,
        "supports_tigo_nicaragua": True,
        "supported_origins": list(ADVISORIES),
        "requires_owner_attestation": True,
        "no_imei_access": True,
        "no_bypass_pin_frp_icloud_blacklist": True,
        "official_platform_tools": "https://developer.android.com/tools/releases/platform-tools",
    }
