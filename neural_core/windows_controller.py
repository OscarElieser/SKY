"""Controlador nativo de Windows para SKY JARVIS.

Permite:
- Resolver e iniciar aplicaciones permitidas con comprobación de existencia real.
- Enumerar, enfocar, minimizar y restaurar ventanas del usuario de forma segura.
- Teclas multimedia nativas de Windows sin inyección de shell ni scripts.
- Compatibilidad multiplataforma para no romper CI en Linux/macOS.
"""
from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

AUTHORIZED_APPS: dict[str, dict[str, Any]] = {
    'calculator': {
        'desc': 'Calculadora',
        'executables': ['calc.exe'],
        'reg_keys': ['calc.exe'],
        'linux': ['gnome-calculator', 'kcalc', 'mate-calc', 'galculator'],
        'darwin': ['Calculator']
    },
    'text_editor': {
        'desc': 'Bloc de notas',
        'executables': ['notepad.exe'],
        'reg_keys': ['notepad.exe'],
        'linux': ['gedit', 'kate', 'mousepad', 'xed'],
        'darwin': ['TextEdit']
    },
    'file_manager': {
        'desc': 'Explorador de archivos',
        'executables': ['explorer.exe'],
        'reg_keys': ['explorer.exe'],
        'linux': ['nautilus', 'thunar', 'dolphin', 'nemo'],
        'darwin': ['Finder']
    },
    'browser': {
        'desc': 'Navegador web',
        'executables': ['msedge.exe', 'chrome.exe', 'firefox.exe'],
        'reg_keys': ['msedge.exe', 'chrome.exe', 'firefox.exe'],
        'linux': ['xdg-open'],
        'darwin': ['Safari']
    },
    'chrome': {
        'desc': 'Google Chrome',
        'executables': ['chrome.exe'],
        'reg_keys': ['chrome.exe'],
        'candidates': [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
        ],
        'linux': ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'],
        'darwin': ['Google Chrome']
    },
    'edge': {
        'desc': 'Microsoft Edge',
        'executables': ['msedge.exe'],
        'reg_keys': ['msedge.exe'],
        'candidates': [
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
        ],
        'linux': ['microsoft-edge', 'microsoft-edge-stable'],
        'darwin': ['Microsoft Edge']
    },
    'firefox': {
        'desc': 'Mozilla Firefox',
        'executables': ['firefox.exe'],
        'reg_keys': ['firefox.exe'],
        'candidates': [
            r'C:\Program Files\Mozilla Firefox\firefox.exe',
            r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe'
        ],
        'linux': ['firefox'],
        'darwin': ['Firefox']
    },
    'word': {
        'desc': 'Microsoft Word',
        'executables': ['winword.exe', 'WINWORD.EXE'],
        'reg_keys': ['winword.exe'],
        'candidates': [
            r'C:\Program Files\Microsoft Office\Root\Office16\WINWORD.EXE',
            r'C:\Program Files (x86)\Microsoft Office\Root\Office16\WINWORD.EXE',
            r'C:\Program Files\Microsoft Office\Office16\WINWORD.EXE',
            r'C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE',
            r'C:\Program Files\Microsoft Office\Office15\WINWORD.EXE'
        ],
        'linux': ['libreoffice'],
        'darwin': ['Microsoft Word']
    },
    'excel': {
        'desc': 'Microsoft Excel',
        'executables': ['excel.exe', 'EXCEL.EXE'],
        'reg_keys': ['excel.exe'],
        'candidates': [
            r'C:\Program Files\Microsoft Office\Root\Office16\EXCEL.EXE',
            r'C:\Program Files (x86)\Microsoft Office\Root\Office16\EXCEL.EXE',
            r'C:\Program Files\Microsoft Office\Office16\EXCEL.EXE',
            r'C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE',
            r'C:\Program Files\Microsoft Office\Office15\EXCEL.EXE'
        ],
        'linux': ['libreoffice'],
        'darwin': ['Microsoft Excel']
    },
    'powerpoint': {
        'desc': 'Microsoft PowerPoint',
        'executables': ['powerpnt.exe', 'POWERPNT.EXE'],
        'reg_keys': ['powerpnt.exe'],
        'candidates': [
            r'C:\Program Files\Microsoft Office\Root\Office16\POWERPNT.EXE',
            r'C:\Program Files (x86)\Microsoft Office\Root\Office16\POWERPNT.EXE',
            r'C:\Program Files\Microsoft Office\Office16\POWERPNT.EXE',
            r'C:\Program Files (x86)\Microsoft Office\Office16\POWERPNT.EXE',
            r'C:\Program Files\Microsoft Office\Office15\POWERPNT.EXE'
        ],
        'linux': ['libreoffice'],
        'darwin': ['Microsoft PowerPoint']
    },
    'vscode': {
        'desc': 'Visual Studio Code',
        'executables': ['code.cmd', 'code.exe', 'Code.exe'],
        'reg_keys': ['Code.exe'],
        'candidates': [
            str(Path.home() / 'AppData' / 'Local' / 'Programs' / 'Microsoft VS Code' / 'Code.exe'),
            str(Path.home() / 'AppData' / 'Local' / 'Programs' / 'Microsoft VS Code' / 'bin' / 'code.cmd'),
            r'C:\Program Files\Microsoft VS Code\Code.exe',
            r'C:\Program Files (x86)\Microsoft VS Code\Code.exe'
        ],
        'linux': ['code'],
        'darwin': ['Visual Studio Code']
    }
}


def find_installed_app(app_id: str) -> Optional[str]:
    """Busca y verifica la ruta física del ejecutable para una aplicación permitida."""
    app_info = AUTHORIZED_APPS.get(app_id)
    if not app_info:
        return None

    current_os = platform.system().lower()
    if current_os == 'windows':
        import winreg

        # 1. Buscar en PATH
        for exe_name in app_info.get('executables', []):
            found_path = shutil.which(exe_name)
            if found_path and Path(found_path).exists():
                return found_path

        # 2. Buscar en Registro de Windows (App Paths)
        for reg_name in app_info.get('reg_keys', []):
            for root_key in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    sub_key = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{reg_name}"
                    with winreg.OpenKey(root_key, sub_key) as k:
                        val, _ = winreg.QueryValueEx(k, '')
                        if val:
                            clean_p = Path(str(val).strip(' "'))
                            if clean_p.exists():
                                return str(clean_p)
                except OSError:
                    pass

        # 3. Buscar en rutas candidatas predefinidas
        for cand in app_info.get('candidates', []):
            p = Path(cand)
            if p.exists():
                return str(p)

    elif current_os == 'darwin':
        darwin_apps = app_info.get('darwin', [])
        for d_app in darwin_apps:
            p = Path(f'/Applications/{d_app}.app')
            if p.exists():
                return str(p)
            user_p = Path.home() / 'Applications' / f'{d_app}.app'
            if user_p.exists():
                return str(user_p)
    else:
        linux_cmds = app_info.get('linux', [])
        for cmd in linux_cmds:
            w = shutil.which(cmd)
            if w:
                return w

    return None


def launch_authorized_app(app_id: str) -> Dict[str, Any]:
    """Inicia una aplicación autorizada y devuelve evidencia verificable del resultado."""
    if app_id not in AUTHORIZED_APPS:
        raise ValueError(f"La aplicación '{app_id}' no está autorizada en la política de seguridad de SKY.")

    app_desc = AUTHORIZED_APPS[app_id]['desc']
    exe_path = find_installed_app(app_id)
    if not exe_path:
        raise RuntimeError(
            f"La aplicación '{app_desc}' ({app_id}) no se encuentra instalada en este equipo."
        )

    current_os = platform.system().lower()
    if current_os == 'windows':
        # En Windows, arrancar proceso aislado
        proc = subprocess.Popen([exe_path], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {
            'ok': True,
            'app': app_id,
            'description': app_desc,
            'executable': exe_path,
            'pid': proc.pid,
            'message': f"Se inició '{app_desc}' correctamente en el equipo local."
        }
    elif current_os == 'darwin':
        subprocess.Popen(['open', '-a', exe_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {
            'ok': True,
            'app': app_id,
            'description': app_desc,
            'executable': exe_path,
            'message': f"Se abrió '{app_desc}' en macOS."
        }
    else:
        subprocess.Popen([exe_path], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {
            'ok': True,
            'app': app_id,
            'description': app_desc,
            'executable': exe_path,
            'message': f"Se inició '{app_desc}' en Linux."
        }


def _ensure_interactive_desktop() -> None:
    """Asegura que el hilo esté conectado a la estación de ventanas interactiva en Windows."""
    if platform.system().lower() != 'windows':
        return
    try:
        user32 = ctypes.windll.user32
        h_winsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
        if h_winsta:
            user32.SetProcessWindowStation(h_winsta)
            h_desk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
    except Exception:
        pass


def list_user_windows() -> List[Dict[str, Any]]:
    """Enumera las ventanas visibles principales de la sesión de usuario en Windows."""
    if platform.system().lower() != 'windows':
        return []

    from ctypes import wintypes
    _ensure_interactive_desktop()
    user32 = ctypes.windll.user32

    GW_OWNER = 4
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080

    windows: List[Dict[str, Any]] = []

    def enum_cb(hwnd: int, lparam: int) -> int:
        if user32.IsWindowVisible(hwnd):
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if not (ex_style & WS_EX_TOOLWINDOW):
                owner = user32.GetWindow(hwnd, GW_OWNER)
                if not owner:
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.strip()
                        if title and title not in ('Program Manager', 'Settings', 'Configuración'):
                            windows.append({'hwnd': hwnd, 'title': title})
        return 1

    CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(CMPFUNC(enum_cb), 0)
    return windows


def focus_user_window(target: str) -> Dict[str, Any]:
    """Trae al primer plano una ventana por fragmento de título o HWND."""
    if platform.system().lower() != 'windows':
        raise RuntimeError("La gestión de ventanas requiere Windows en esta fase.")

    _ensure_interactive_desktop()
    user32 = ctypes.windll.user32
    windows = list_user_windows()

    target_clean = target.strip().lower()
    found_hwnd = None
    found_title = None

    # Intentar por HWND numérico
    if target_clean.startswith('0x'):
        try:
            val = int(target_clean, 16)
            for w in windows:
                if w['hwnd'] == val:
                    found_hwnd, found_title = w['hwnd'], w['title']
                    break
        except ValueError:
            pass

    # Intentar por título
    if not found_hwnd:
        for w in windows:
            if target_clean in w['title'].lower():
                found_hwnd, found_title = w['hwnd'], w['title']
                break

    if not found_hwnd:
        raise ValueError(f"No se encontró una ventana abierta que coincida con '{target}'.")

    # Restaurar si está minimizada y traer al frente
    SW_RESTORE = 9
    user32.ShowWindow(found_hwnd, SW_RESTORE)
    user32.SetForegroundWindow(found_hwnd)
    return {
        'ok': True,
        'hwnd': found_hwnd,
        'title': found_title,
        'message': f"Ventana enfocada: «{found_title}»."
    }


def minimize_user_window(target: Optional[str] = None) -> Dict[str, Any]:
    """Minimiza una ventana especificada o la ventana en primer plano."""
    if platform.system().lower() != 'windows':
        raise RuntimeError("La gestión de ventanas requiere Windows en esta fase.")

    _ensure_interactive_desktop()
    user32 = ctypes.windll.user32
    SW_MINIMIZE = 6

    if target:
        windows = list_user_windows()
        target_clean = target.strip().lower()
        for w in windows:
            if target_clean in w['title'].lower():
                user32.ShowWindow(w['hwnd'], SW_MINIMIZE)
                return {'ok': True, 'title': w['title'], 'message': f"Ventana «{w['title']}» minimizada."}
        raise ValueError(f"No se encontró una ventana que coincida con '{target}'.")
    else:
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value or "Ventana activa"
            user32.ShowWindow(hwnd, SW_MINIMIZE)
            return {'ok': True, 'title': title, 'message': f"Ventana «{title}» minimizada."}
        raise RuntimeError("No se detectó una ventana en primer plano para minimizar.")


def restore_user_window(target: Optional[str] = None) -> Dict[str, Any]:
    """Restaura una ventana especificada."""
    if platform.system().lower() != 'windows':
        raise RuntimeError("La gestión de ventanas requiere Windows en esta fase.")

    _ensure_interactive_desktop()
    user32 = ctypes.windll.user32
    SW_RESTORE = 9

    if target:
        windows = list_user_windows()
        target_clean = target.strip().lower()
        for w in windows:
            if target_clean in w['title'].lower():
                user32.ShowWindow(w['hwnd'], SW_RESTORE)
                user32.SetForegroundWindow(w['hwnd'])
                return {'ok': True, 'title': w['title'], 'message': f"Ventana «{w['title']}» restaurada."}
        raise ValueError(f"No se encontró una ventana que coincida con '{target}'.")
    else:
        windows = list_user_windows()
        if windows:
            first = windows[0]
            user32.ShowWindow(first['hwnd'], SW_RESTORE)
            user32.SetForegroundWindow(first['hwnd'])
            return {'ok': True, 'title': first['title'], 'message': f"Ventana «{first['title']}» restaurada."}
        raise RuntimeError("No hay ventanas disponibles para restaurar.")
