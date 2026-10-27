"""Read-only local checks for a prospective SKY Home Windows 11 server.

Does not install, start, stop or expose services; never reads secrets or .env.
Usage: python scripts/sky_home_preflight.py [--json]
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import shutil
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ram_gb() -> float | None:
    if os.name != "nt":
        return None
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    return round(status.ullTotalPhys / 2**30, 1) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) else None


def _listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def report() -> dict:
    disk = shutil.disk_usage(ROOT)
    return {
        "os": platform.system(), "windows_release": platform.release(),
        "ram_gib": _ram_gb(), "free_disk_gib": round(disk.free / 2**30, 1),
        "python": platform.python_version(),
        "api_local_port_open": _listening(8765),
        "agent_local_port_open": _listening(8766),
        "tailscale_installed": bool(shutil.which("tailscale")),
        "venv_present": (ROOT / ".venv").exists(),
        "offline_model_checked": False,
        "microphone_checked": False, "remote_access_checked": False,
        "warning": "Puertos abiertos no demuestran autenticación, salud ni identidad del servicio",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoría local sin cambios para SKY Home")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = report()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for key, value in data.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
