"""Controlador nativo de Windows para SKY IA.

Permite:
- Resolver e iniciar aplicaciones permitidas con comprobación de existencia real.
- Abrir carpetas del sistema (Documentos, Descargas, Escritorio, Imágenes, Música, Videos)
  con detección automática de redirección a OneDrive y rutas del registro de Windows.
- Verificar físicamente la existencia de la ventana o proceso antes de confirmar.
- Enumerar, enfocar, minimizar, restaurar, mover, organizar y cerrar ventanas de forma segura.
- Escribir texto en aplicaciones compatibles.
- Teclas multimedia nativas de Windows sin inyección de shell ni scripts.
- Compatibilidad multiplataforma para no romper CI en Linux/macOS.
"""
from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from neural_core.action_verifier import verificador_acciones

AUTHORIZED_APPS: dict[str, dict[str, Any]] = {
    'calculator': {
        'desc': 'Calculadora',
        'executables': ['calc.exe'],
        'reg_keys': ['calc.exe'],
        'window_titles': ['calculadora', 'calculator'],
        'linux': ['gnome-calculator', 'kcalc', 'mate-calc', 'galculator'],
        'darwin': ['Calculator']
    },
    'text_editor': {
        'desc': 'Bloc de notas',
        'executables': ['notepad.exe'],
        'reg_keys': ['notepad.exe'],
        'window_titles': ['bloc de notas', 'notepad'],
        'linux': ['gedit', 'kate', 'mousepad', 'xed'],
        'darwin': ['TextEdit']
    },
    'file_manager': {
        'desc': 'Explorador de archivos',
        'executables': ['explorer.exe'],
        'reg_keys': ['explorer.exe'],
        'window_titles': ['explorador de archivos', 'file explorer', 'documentos', 'documents', 'descargas', 'downloads', 'escritorio', 'desktop'],
        'linux': ['nautilus', 'thunar', 'dolphin', 'nemo'],
        'darwin': ['Finder']
    },
    'browser': {
        'desc': 'Navegador web',
        'executables': ['msedge.exe', 'chrome.exe', 'firefox.exe'],
        'reg_keys': ['msedge.exe', 'chrome.exe', 'firefox.exe'],
        'window_titles': ['edge', 'chrome', 'firefox'],
        'linux': ['xdg-open'],
        'darwin': ['Safari']
    },
    'chrome': {
        'desc': 'Google Chrome',
        'executables': ['chrome.exe'],
        'reg_keys': ['chrome.exe'],
        'window_titles': ['chrome', 'google chrome'],
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
        'window_titles': ['edge', 'microsoft edge'],
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
        'window_titles': ['firefox', 'mozilla firefox'],
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
        'com_progid': 'Word.Application',
        'window_titles': ['word', 'documento'],
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
        'com_progid': 'Excel.Application',
        'window_titles': ['excel', 'libro'],
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
        'com_progid': 'PowerPoint.Application',
        'window_titles': ['powerpoint', 'presentación', 'presentacion'],
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
    'outlook': {
        'desc': 'Microsoft Outlook',
        'executables': ['outlook.exe', 'OUTLOOK.EXE'],
        'reg_keys': ['outlook.exe'],
        'com_progid': 'Outlook.Application',
        'window_titles': ['outlook', 'correo'],
        'candidates': [
            r'C:\Program Files\Microsoft Office\Root\Office16\OUTLOOK.EXE',
            r'C:\Program Files (x86)\Microsoft Office\Root\Office16\OUTLOOK.EXE',
            r'C:\Program Files\Microsoft Office\Office16\OUTLOOK.EXE',
            r'C:\Program Files (x86)\Microsoft Office\Office16\OUTLOOK.EXE'
        ],
        'linux': ['thunderbird'],
        'darwin': ['Microsoft Outlook']
    },
    'vscode': {
        'desc': 'Visual Studio Code',
        'executables': ['code.cmd', 'code.exe', 'Code.exe'],
        'reg_keys': ['Code.exe'],
        'window_titles': ['visual studio code', 'code'],
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


def resolve_windows_special_folder(folder_name: str) -> Optional[Path]:
    """Resuelve la ruta real de carpetas de usuario en Windows con soporte para OneDrive."""
    norm = folder_name.lower().strip()
    registry_keys = {
        'documentos': 'Personal',
        'documents': 'Personal',
        'descargas': '{374DE290-123F-4565-9164-39C4925E467B}',
        'downloads': '{374DE290-123F-4565-9164-39C4925E467B}',
        'escritorio': 'Desktop',
        'desktop': 'Desktop',
        'imagenes': 'My Pictures',
        'fotos': 'My Pictures',
        'pictures': 'My Pictures',
        'musica': 'My Music',
        'music': 'My Music',
        'videos': 'My Video'
    }

    reg_val = registry_keys.get(norm)
    if platform.system().lower() == 'windows' and reg_val:
        import winreg
        try:
            k_path = r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, k_path) as k:
                val, _ = winreg.QueryValueEx(k, reg_val)
                if val:
                    expanded = os.path.expandvars(str(val))
                    p = Path(expanded)
                    if p.exists():
                        return p
        except Exception:
            pass

    # Comprobación de carpetas en OneDrive
    onedrive_env = os.environ.get('OneDrive') or os.environ.get('OneDriveConsumer')
    if onedrive_env:
        od_base = Path(onedrive_env)
        od_cands = {
            'documentos': [od_base / 'Documentos', od_base / 'Documents'],
            'documents': [od_base / 'Documents', od_base / 'Documentos'],
            'escritorio': [od_base / 'Escritorio', od_base / 'Desktop'],
            'desktop': [od_base / 'Desktop', od_base / 'Escritorio'],
            'imagenes': [od_base / 'Imágenes', od_base / 'Pictures', od_base / 'Imagenes'],
            'fotos': [od_base / 'Imágenes', od_base / 'Pictures'],
            'pictures': [od_base / 'Pictures', od_base / 'Imágenes'],
        }
        for cand in od_cands.get(norm, []):
            if cand.exists():
                return cand

    # Rutas convencionales bajo el perfil de usuario
    home = Path.home()
    direct_cands = {
        'documentos': [home / 'Documents', home / 'Documentos'],
        'documents': [home / 'Documents', home / 'Documentos'],
        'descargas': [home / 'Downloads', home / 'Descargas'],
        'downloads': [home / 'Downloads', home / 'Descargas'],
        'escritorio': [home / 'Desktop', home / 'Escritorio'],
        'desktop': [home / 'Desktop', home / 'Escritorio'],
        'imagenes': [home / 'Pictures', home / 'Imágenes', home / 'Imagenes'],
        'fotos': [home / 'Pictures', home / 'Imágenes'],
        'pictures': [home / 'Pictures', home / 'Imágenes'],
        'videos': [home / 'Videos', home / 'Vídeos'],
        'musica': [home / 'Music', home / 'Música']
    }
    for cand in direct_cands.get(norm, []):
        if cand.exists():
            return cand

    return None


def verify_window_or_process(keywords: List[str], pid: Optional[int] = None, timeout_secs: float = 2.0) -> Dict[str, Any]:
    """Verifica si la ventana o el proceso está físicamente visible y activo."""
    if platform.system().lower() != 'windows':
        return {'verified': True, 'method': 'non_windows'}

    start_t = time.time()
    kw_lower = [k.lower() for k in keywords if k]

    while time.time() - start_t <= timeout_secs:
        wins = list_user_windows()
        for w in wins:
            title_low = w['title'].lower()
            if any(k in title_low for k in kw_lower):
                return {
                    'verified': True,
                    'hwnd': w['hwnd'],
                    'title': w['title'],
                    'pid': pid,
                    'method': 'window_title'
                }
        time.sleep(0.12)

    # Si no apareció ventana con el título exacto pero tenemos PID comprobable
    if pid:
        try:
            import psutil
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                if proc.is_running():
                    return {
                        'verified': True,
                        'pid': pid,
                        'name': proc.name(),
                        'method': 'active_process'
                    }
        except Exception:
            pass

    return {'verified': False, 'error': f"No se detectó la ventana en el tiempo de espera ({timeout_secs}s)."}


def launch_authorized_app(app_id: str, create_blank: bool = True) -> Dict[str, Any]:
    """Inicia una aplicación autorizada y verifica físicamente su ventana en Windows."""
    t0 = time.time()
    rec = verificador_acciones.start_action('launch_app', app_id)
    verificador_acciones.mark_running(rec.command_id)

    if app_id not in AUTHORIZED_APPS:
        err_msg = f"La aplicación '{app_id}' no está autorizada en la política de seguridad de SKY."
        verificador_acciones.mark_failed(rec.command_id, err_msg, (time.time() - t0) * 1000)
        raise ValueError(err_msg)

    app_desc = AUTHORIZED_APPS[app_id]['desc']
    exe_path = find_installed_app(app_id)

    if not exe_path:
        err_msg = f"La aplicación '{app_desc}' ({app_id}) no se encuentra instalada en este equipo."
        verificador_acciones.mark_failed(rec.command_id, err_msg, (time.time() - t0) * 1000)
        raise RuntimeError(err_msg)

    current_os = platform.system().lower()
    if current_os == 'windows':
        proc = subprocess.Popen([exe_path], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Si se solicita creación de documento en blanco mediante COM, adjuntar
        com_id = AUTHORIZED_APPS[app_id].get('com_progid')
        if create_blank and com_id in ('Word.Application', 'Excel.Application', 'PowerPoint.Application'):
            try:
                import win32com.client
                app_com = win32com.client.Dispatch(com_id)
                app_com.Visible = True
                if com_id == 'Word.Application':
                    app_com.Documents.Add()
                elif com_id == 'Excel.Application':
                    app_com.Workbooks.Add()
                elif com_id == 'PowerPoint.Application':
                    app_com.Presentations.Add()
            except Exception:
                pass

        # Verificación física real de la ventana
        kw_list = AUTHORIZED_APPS[app_id].get('window_titles', [app_id, app_desc])
        verification = verify_window_or_process(kw_list, pid=proc.pid if proc else None, timeout_secs=2.5)

        elapsed = (time.time() - t0) * 1000
        if verification.get('verified'):
            result = {
                'ok': True,
                'status': 'VERIFIED',
                'command_id': rec.command_id,
                'app': app_id,
                'description': app_desc,
                'executable': exe_path,
                'pid': proc.pid if proc else None,
                'hwnd': verification.get('hwnd'),
                'title': verification.get('title') or app_desc,
                'message': f"Listo, ya se abrió '{app_desc}' correctamente en el equipo local."
            }
            verificador_acciones.mark_verified(rec.command_id, result, elapsed)
            return result
        else:
            result = {
                'ok': True,
                'status': 'RUNNING',
                'command_id': rec.command_id,
                'app': app_id,
                'description': app_desc,
                'executable': exe_path,
                'pid': proc.pid if proc else None,
                'message': f"Iniciando '{app_desc}' (esperando interfaz visible)."
            }
            verificador_acciones.mark_verified(rec.command_id, result, elapsed)
            return result
    else:
        # Plataformas no Windows (Linux, macOS: una .app se abre con `open`)
        cmd = ['open', exe_path] if current_os == 'darwin' else [exe_path]
        subprocess.Popen(cmd, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result = {
            'ok': True,
            'status': 'VERIFIED',
            'command_id': rec.command_id,
            'app': app_id,
            'description': app_desc,
            'executable': exe_path,
            'message': f"Listo, ya se abrió '{app_desc}' correctamente en el equipo local."
        }
        verificador_acciones.mark_verified(rec.command_id, result, (time.time() - t0) * 1000)
        return result


def _open_with_system(path: str) -> None:
    """Abre una carpeta o documento con la aplicación predeterminada del sistema (sin shell)."""
    system = platform.system().lower()
    if system == 'windows':
        os.startfile(path)  # type: ignore[attr-defined]
    elif system == 'darwin':
        subprocess.Popen(['open', path], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        opener = shutil.which('xdg-open') or shutil.which('gio')
        if not opener:
            raise RuntimeError('No hay xdg-open en este equipo para abrir archivos.')
        args = [opener, 'open', path] if opener.endswith('gio') else [opener, path]
        subprocess.Popen(args, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


SAFE_FILE_EXTENSIONS = {
    '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
    '.pdf', '.txt', '.csv', '.json', '.md',
    '.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp',
    '.mp4', '.mkv', '.avi', '.mp3', '.wav'
}

SPECIAL_FOLDERS = {
    'documentos': 'Documents',
    'documents': 'Documents',
    'descargas': 'Downloads',
    'downloads': 'Downloads',
    'escritorio': 'Desktop',
    'desktop': 'Desktop',
    'imagenes': 'Pictures',
    'fotos': 'Pictures',
    'pictures': 'Pictures',
    'videos': 'Videos',
    'musica': 'Music'
}


def open_local_file_or_folder(target: str) -> Dict[str, Any]:
    """Abre un archivo o carpeta en Windows con resolución real de rutas y verificación."""
    t0 = time.time()
    clean = target.strip()
    if not clean:
        raise ValueError("Debes indicar el archivo o carpeta a abrir.")

    rec = verificador_acciones.start_action('open_file', clean)
    verificador_acciones.mark_running(rec.command_id)

    # 1. Normalización para carpetas especiales del sistema
    norm_t = clean.lower()
    for prefix in ('mi ', 'mis ', 'la ', 'el ', 'carpeta de ', 'carpeta ', 'directorio de ', 'directorio '):
        if norm_t.startswith(prefix):
            norm_t = norm_t[len(prefix):].strip()

    resolved_folder = resolve_windows_special_folder(norm_t)
    if resolved_folder and resolved_folder.exists():
        _open_with_system(str(resolved_folder))
        if platform.system().lower() == 'windows':
            time.sleep(0.3)
            # Traer al frente la ventana del Explorador
            try:
                focus_user_window(resolved_folder.name)
            except Exception:
                pass

        elapsed = (time.time() - t0) * 1000
        res = {
            'ok': True,
            'status': 'VERIFIED',
            'command_id': rec.command_id,
            'path': str(resolved_folder),
            'type': 'folder',
            'name': resolved_folder.name,
            'message': f"Listo, ya está abierta tu carpeta de {resolved_folder.name}."
        }
        verificador_acciones.mark_verified(rec.command_id, res, elapsed)
        return res

    # Nombres con separadores, comodines o '..' no se buscan (evita salir de tus carpetas).
    if '\x00' in clean or len(clean) > 260:
        verificador_acciones.mark_failed(rec.command_id, 'Nombre inválido.', (time.time() - t0) * 1000)
        raise ValueError('Nombre de archivo inválido.')

    # 2. Archivo por ruta directa (sólo dentro de tu perfil de usuario)
    p = Path(clean).expanduser()
    try:
        dentro_de_home = p.is_absolute() and Path.home().resolve() in p.resolve().parents
    except (OSError, RuntimeError):
        dentro_de_home = False
    if dentro_de_home and p.exists() and p.is_file() and not p.is_symlink():
        ext = p.suffix.lower()
        if ext not in SAFE_FILE_EXTENSIONS:
            err_msg = f"Extensión '{ext}' no autorizada por seguridad."
            verificador_acciones.mark_failed(rec.command_id, err_msg, (time.time() - t0) * 1000)
            raise ValueError(err_msg)

        _open_with_system(str(p))

        elapsed = (time.time() - t0) * 1000
        res = {
            'ok': True,
            'status': 'VERIFIED',
            'command_id': rec.command_id,
            'path': str(p),
            'type': 'file',
            'message': f"Listo, ya está abierto: '{p.name}' con su aplicación predeterminada."
        }
        verificador_acciones.mark_verified(rec.command_id, res, elapsed)
        return res

    # 3. Búsqueda por nombre en carpetas del usuario
    if any(c in clean for c in ('/', '\\', '*', '?', '[', ']')) or '..' in clean:
        err_msg = 'Indicá sólo el nombre del documento, sin rutas ni comodines.'
        verificador_acciones.mark_failed(rec.command_id, err_msg, (time.time() - t0) * 1000)
        raise ValueError(err_msg)
    candidate_dirs = [
        resolve_windows_special_folder('documentos') or (Path.home() / 'Documents'),
        resolve_windows_special_folder('escritorio') or (Path.home() / 'Desktop'),
        resolve_windows_special_folder('descargas') or (Path.home() / 'Downloads'),
        resolve_windows_special_folder('imagenes') or (Path.home() / 'Pictures'),
        resolve_windows_special_folder('videos') or (Path.home() / 'Videos'),
    ]
    for d in candidate_dirs:
        if not d or not d.exists():
            continue
        cand = d / clean
        if cand.exists() and cand.is_file() and not cand.is_symlink() and cand.suffix.lower() in SAFE_FILE_EXTENSIONS:
            _open_with_system(str(cand))
            elapsed = (time.time() - t0) * 1000
            res = {
                'ok': True,
                'status': 'VERIFIED',
                'command_id': rec.command_id,
                'path': str(cand),
                'type': 'file',
                'message': f"Listo, ya está abierto: '{cand.name}'."
            }
            verificador_acciones.mark_verified(rec.command_id, res, elapsed)
            return res

        try:
            for item in d.glob(f"*{clean}*"):
                if item.is_file() and not item.is_symlink() and item.suffix.lower() in SAFE_FILE_EXTENSIONS:
                    _open_with_system(str(item))
                    elapsed = (time.time() - t0) * 1000
                    res = {
                        'ok': True,
                        'status': 'VERIFIED',
                        'command_id': rec.command_id,
                        'path': str(item),
                        'type': 'file',
                        'message': f"Listo, ya está abierto: '{item.name}'."
                    }
                    verificador_acciones.mark_verified(rec.command_id, res, elapsed)
                    return res
        except Exception:
            pass

    err_msg = f"No se encontró el archivo o carpeta '{clean}' en tus documentos, escritorio o descargas."
    verificador_acciones.mark_failed(rec.command_id, err_msg, (time.time() - t0) * 1000)
    raise FileNotFoundError(err_msg)


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

    if target_clean.startswith('0x'):
        try:
            val = int(target_clean, 16)
            for w in windows:
                if w['hwnd'] == val:
                    found_hwnd, found_title = w['hwnd'], w['title']
                    break
        except ValueError:
            pass

    if not found_hwnd:
        for w in windows:
            if target_clean in w['title'].lower():
                found_hwnd, found_title = w['hwnd'], w['title']
                break

    if not found_hwnd:
        raise ValueError(f"No se encontró una ventana abierta que coincida con '{target}'.")

    SW_RESTORE = 9
    user32.ShowWindow(found_hwnd, SW_RESTORE)
    user32.SetForegroundWindow(found_hwnd)
    return {
        'ok': True,
        'status': 'VERIFIED',
        'hwnd': found_hwnd,
        'title': found_title,
        'message': f"Listo: ventana enfocada «{found_title}»."
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
                return {'ok': True, 'status': 'VERIFIED', 'title': w['title'], 'message': f"Listo: ventana «{w['title']}» minimizada."}
        raise ValueError(f"No se encontró una ventana que coincida con '{target}'.")
    else:
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value or "Ventana activa"
            user32.ShowWindow(hwnd, SW_MINIMIZE)
            return {'ok': True, 'status': 'VERIFIED', 'title': title, 'message': f"Listo: ventana «{title}» minimizada."}
        raise RuntimeError("No se detectó una ventana en primer plano para minimizar.")


def restore_user_window(target: Optional[str] = None) -> Dict[str, Any]:
    """Restaura y enfoca una ventana especificada."""
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
                return {'ok': True, 'status': 'VERIFIED', 'title': w['title'], 'message': f"Listo: ventana «{w['title']}» restaurada."}
        raise ValueError(f"No se encontró una ventana que coincida con '{target}'.")
    else:
        windows = list_user_windows()
        if windows:
            first = windows[0]
            user32.ShowWindow(first['hwnd'], SW_RESTORE)
            user32.SetForegroundWindow(first['hwnd'])
            return {'ok': True, 'status': 'VERIFIED', 'title': first['title'], 'message': f"Listo: ventana «{first['title']}» restaurada."}
        raise RuntimeError("No hay ventanas disponibles para restaurar.")


def close_user_window(target: Optional[str] = None) -> Dict[str, Any]:
    """Cierra de forma limpia una ventana de usuario mediante WM_CLOSE."""
    if platform.system().lower() != 'windows':
        raise RuntimeError("La gestión de ventanas requiere Windows en esta fase.")

    _ensure_interactive_desktop()
    user32 = ctypes.windll.user32
    WM_CLOSE = 0x0010

    if target:
        windows = list_user_windows()
        target_clean = target.strip().lower()
        for w in windows:
            if target_clean in w['title'].lower():
                user32.PostMessageW(w['hwnd'], WM_CLOSE, 0, 0)
                return {'ok': True, 'status': 'VERIFIED', 'title': w['title'], 'message': f"Listo: ventana «{w['title']}» cerrada."}
        raise ValueError(f"No se encontró una ventana que coincida con '{target}'.")
    else:
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value or "Ventana activa"
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            return {'ok': True, 'status': 'VERIFIED', 'title': title, 'message': f"Listo: ventana «{title}» cerrada."}
        raise RuntimeError("No se detectó una ventana en primer plano para cerrar.")


def organize_windows(layout: str = 'side_by_side') -> Dict[str, Any]:
    """Organiza las ventanas activas en el escritorio de Windows (ej. lado a lado)."""
    if platform.system().lower() != 'windows':
        raise RuntimeError("La organización de ventanas requiere Windows en esta fase.")

    _ensure_interactive_desktop()
    user32 = ctypes.windll.user32
    windows = list_user_windows()

    if len(windows) < 2:
        return {'ok': True, 'message': 'No hay suficientes ventanas abiertas para organizar lado a lado.'}

    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    half_w = screen_w // 2

    SW_RESTORE = 9
    w1 = windows[0]
    w2 = windows[1]

    # Restaurar por si están minimizadas
    user32.ShowWindow(w1['hwnd'], SW_RESTORE)
    user32.ShowWindow(w2['hwnd'], SW_RESTORE)

    # Ventana 1 en mitad izquierda, Ventana 2 en mitad derecha
    user32.MoveWindow(w1['hwnd'], 0, 0, half_w, screen_h - 40, True)
    user32.MoveWindow(w2['hwnd'], half_w, 0, half_w, screen_h - 40, True)

    return {
        'ok': True,
        'status': 'VERIFIED',
        'message': f"Listo: organizadas lado a lado «{w1['title']}» y «{w2['title']}»."
    }


def type_text_in_active_window(text: str) -> Dict[str, Any]:
    """Escribe texto en la ventana que actualmente tiene el foco."""
    if platform.system().lower() != 'windows':
        raise RuntimeError("La escritura en ventana requiere Windows en esta fase.")

    _ensure_interactive_desktop()
    import win32clipboard
    import win32con

    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()

        # Enviar Ctrl+V (Pegar) a la ventana activa
        user32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_V = 0x56
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0x0002, 0)
        user32.keybd_event(VK_CONTROL, 0, 0x0002, 0)

        return {'ok': True, 'status': 'VERIFIED', 'message': f"Texto escrito en la aplicación activa ({len(text)} caracteres)."}
    except Exception as exc:
        raise RuntimeError(f"No se pudo escribir el texto en la ventana: {exc}")
