"""SKY v12 — Capacidades del Asistente Personal sobre tu dispositivo.

Cada capacidad es una función concreta y acotada (multimedia, volumen, apps,
archivos en carpetas permitidas, notificaciones, capturas, portapapeles...).
El DUEÑO decide qué se activa en su archivo local de política:

    ~/.neuralt/device_agent_policy.json

La política sólo se modifica en el propio equipo (CLI del agente), nunca por
red. Por defecto sólo están activas las capacidades de bajo riesgo (estado, webs,
apps, multimedia, volumen, reproducir, avisos y tareas). Ventanas, escritura de
texto, archivos, notas, capturas, portapapeles y bloqueo exigen activarlas.

Compatibilidad con SKY JARVIS (v11.x): las variables de entorno del equipo
SKY_WINDOW_ACTIONS=1, SKY_ALL_CAPABILITIES=1 y SKY_NOTES_ENABLED=1 también cuentan
como autorización del dueño.

Lo que SKY nunca hace, ni con el perfil completo: ejecutar comandos de shell
arbitrarios, abrir ejecutables/scripts, descargar e instalar programas ni
realizar pagos. Así el token de tu agente no se convierte en control remoto
total de tu PC si alguien llegara a obtenerlo.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlsplit

CONFIG_DIR = Path.home() / '.neuralt'
POLICY_PATH = CONFIG_DIR / 'device_agent_policy.json'
CAPTURE_DIR = CONFIG_DIR / 'capturas'


@dataclass(frozen=True)
class Capacidad:
    id: str
    nombre: str
    descripcion: str
    acciones: tuple[str, ...]
    riesgo: str  # 'bajo' | 'medio' | 'alto' — guía para confirmaciones


CAPACIDADES: dict[str, Capacidad] = {c.id: c for c in [
    Capacidad('status', 'Estado del equipo', 'Consultar nombre, sistema, batería y recursos', ('status',), 'bajo'),
    Capacidad('open_url', 'Abrir sitios web', 'Abrir páginas HTTPS en el navegador', ('open_url',), 'bajo'),
    Capacidad('launch_app', 'Abrir aplicaciones básicas', 'Calculadora, editor de texto, archivos y navegador', ('launch_app',), 'bajo'),
    Capacidad('apps_extra', 'Más aplicaciones', 'Spotify, VLC, Chrome, Firefox, VS Code, Word, Excel, PowerPoint, WhatsApp, Telegram, cámara, ajustes y tus apps personalizadas', ('launch_app',), 'bajo'),
    Capacidad('media', 'Control multimedia', 'Reproducir/pausar, siguiente, anterior y detener', ('media_control', 'media_key'), 'bajo'),
    Capacidad('volume', 'Volumen', 'Subir, bajar, silenciar o fijar el volumen', ('volume',), 'bajo'),
    Capacidad('play_media', 'Reproducir música y video', 'Buscar y reproducir en YouTube, YouTube Music o Spotify, o un archivo multimedia de tus carpetas', ('play_media',), 'bajo'),
    Capacidad('notify', 'Notificaciones', 'Mostrar avisos en el escritorio', ('notify',), 'bajo'),
    Capacidad('tasks', 'Tareas en segundo plano', 'Preparar presentaciones y documentos mientras seguís trabajando', ('task_action',), 'bajo'),
    Capacidad('files', 'Archivos y carpetas', 'Abrir tus carpetas (Documentos, Descargas… incluso en OneDrive) y documentos; listar y abrir dentro de las carpetas que autorices', ('open_path', 'list_path', 'open_file'), 'medio'),
    Capacidad('windows', 'Ventanas del escritorio', 'Listar, enfocar, minimizar, restaurar, organizar y cerrar ventanas; atajo Ctrl+F4 en Word solo con confirmación', ('window_action', 'organize_windows', 'keyboard_shortcut'), 'medio'),
    Capacidad('notes', 'Notas locales', 'Crear notas, agregarles texto y enviarlas a una papelera recuperable (~/.neuralt/notes)', ('note_create', 'note_append', 'note_trash'), 'medio'),
    Capacidad('type_text', 'Escribir en la app activa', 'Teclear un texto dictado dentro de la ventana que está al frente', ('type_text',), 'alto'),
    Capacidad('screenshot', 'Capturas de pantalla', 'Guardar una captura en ~/.neuralt/capturas', ('screenshot',), 'medio'),
    Capacidad('clipboard', 'Portapapeles', 'Leer o escribir texto del portapapeles', ('clipboard_get', 'clipboard_set'), 'alto'),
    Capacidad('lock', 'Bloquear equipo', 'Bloquear la sesión de inmediato', ('lock_screen',), 'bajo'),
]}

ACCION_A_CAPACIDAD: dict[str, str] = {}
for _c in CAPACIDADES.values():
    for _a in _c.acciones:
        ACCION_A_CAPACIDAD.setdefault(_a, _c.id)

DESCRIPCION_ACCIONES = {
    'status': 'Consultar estado del dispositivo',
    'open_url': 'Abrir un sitio web en el dispositivo',
    'launch_app': 'Abrir una aplicación permitida en el dispositivo',
    'media_control': 'Controlar la reproducción multimedia',
    'volume': 'Ajustar el volumen',
    'play_media': 'Reproducir música o video',
    'notify': 'Mostrar una notificación',
    'open_path': 'Abrir un archivo o carpeta autorizada',
    'list_path': 'Listar una carpeta autorizada',
    'screenshot': 'Tomar una captura de pantalla',
    'clipboard_get': 'Leer el portapapeles',
    'clipboard_set': 'Copiar texto al portapapeles',
    'lock_screen': 'Bloquear el equipo',
    'media_key': 'Enviar tecla multimedia (reproducir, pista, volumen)',
    'open_file': 'Abrir una carpeta del usuario o un documento',
    'window_action': 'Gestionar ventanas abiertas del escritorio',
    'keyboard_shortcut': 'Enviar un atajo autorizado a Word en primer plano',
    'organize_windows': 'Organizar las ventanas lado a lado',
    'type_text': 'Escribir texto en la aplicación activa',
    'note_create': 'Crear nota local',
    'note_append': 'Agregar texto a una nota local',
    'note_trash': 'Enviar una nota a la papelera recuperable',
    'task_action': 'Tarea en segundo plano (presentación, documento)',
}

# Acciones que aplica la propia interfaz de SKY (reproductor interno, ventanas
# holográficas, flujo de voz, borradores para redes). El agente las reconoce
# pero no actúa sobre el sistema operativo ni las reporta como verificadas.
ACCIONES_INTERFAZ = frozenset({'player_control', 'voice_control', 'holographic_window', 'social_action'})
TECLAS_VOLUMEN = frozenset({'volume_up', 'volume_down', 'mute'})

_BAJO_RIESGO = ['status', 'open_url', 'launch_app', 'apps_extra', 'media', 'volume', 'play_media', 'notify', 'tasks']
PERFILES = {
    'basico': list(_BAJO_RIESGO),
    'multimedia': list(_BAJO_RIESGO),
    'completo': list(CAPACIDADES),
}
# Acciones que el asistente puede ejecutar sin pedir clic de confirmación
# cuando el dueño eligió ese perfil (siempre quedan en auditoría). Ventanas,
# archivos, notas, escritura y portapapeles SIEMPRE piden confirmación.
AUTO_POR_PERFIL = {
    'basico': ['status', 'media', 'volume'],
    'multimedia': ['status', 'open_url', 'launch_app', 'apps_extra', 'media', 'volume', 'play_media', 'notify', 'tasks'],
    'completo': ['status', 'open_url', 'launch_app', 'apps_extra', 'media', 'volume', 'play_media', 'notify', 'tasks', 'lock'],
}

DEFAULT_FOLDERS = ['~/Music', '~/Videos', '~/Documents', '~/Downloads', '~/Pictures',
                   '~/Música', '~/Vídeos', '~/Documentos', '~/Descargas', '~/Imágenes']

# Extensiones que JAMÁS se abren: abrirlas equivale a ejecutar programas.
EXTENSIONES_BLOQUEADAS = {
    '.exe', '.bat', '.cmd', '.com', '.ps1', '.psm1', '.vbs', '.vbe', '.js', '.jse', '.wsf', '.wsh',
    '.msi', '.msp', '.scr', '.pif', '.lnk', '.url', '.reg', '.hta', '.cpl', '.jar', '.sh', '.bash',
    '.zsh', '.command', '.app', '.pkg', '.dmg', '.py', '.pyw', '.pl', '.rb', '.php', '.desktop',
    '.appimage', '.run', '.bin', '.deb', '.rpm', '.apk', '.dll', '.so', '.dylib', '.scpt', '.workflow',
}
EXTENSIONES_MEDIA = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus',
                     '.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv', '.m4v'}


# ---------------------------------------------------------------- política

def politica_por_defecto() -> dict:
    return {'perfil': 'basico', 'enabled': list(PERFILES['basico']), 'auto_confirm': list(AUTO_POR_PERFIL['basico']),
            'allowed_folders': [], 'custom_apps': {}}


def _autorizaciones_por_entorno() -> list[str]:
    """Variables que el dueño fija en SU equipo (compatibilidad SKY JARVIS)."""
    extra = []
    if os.getenv('SKY_WINDOW_ACTIONS') == '1':
        extra.append('windows')
    if os.getenv('SKY_ALL_CAPABILITIES') == '1':
        extra += ['files', 'windows', 'type_text']
    if os.getenv('SKY_NOTES_ENABLED') == '1':
        extra.append('notes')
    return extra


def _con_entorno(pol: dict) -> dict:
    for cap in _autorizaciones_por_entorno():
        if cap not in pol['enabled']:
            pol['enabled'].append(cap)
    return pol


def cargar_politica(path: Path | None = None) -> dict:
    """Lee la política local del dueño; si falta o está dañada, usa la básica."""
    path = Path(path or POLICY_PATH)
    base = politica_por_defecto()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return _con_entorno(base)
    if not isinstance(data, dict):
        return _con_entorno(base)
    enabled = [c for c in data.get('enabled', []) if c in CAPACIDADES]
    auto = [c for c in data.get('auto_confirm', []) if c in enabled]
    folders = [str(f)[:400] for f in data.get('allowed_folders', []) if isinstance(f, str)][:30]
    apps = {}
    for name, spec in (data.get('custom_apps') or {}).items():
        if isinstance(name, str) and isinstance(spec, dict) and len(apps) < 40:
            key = name.strip().lower()[:40]
            if key and key.replace('_', '').replace('-', '').isalnum():
                apps[key] = {k: v for k, v in spec.items() if k in ('windows', 'darwin', 'linux')}
    return _con_entorno({'perfil': str(data.get('perfil', 'personalizado'))[:30], 'enabled': enabled or base['enabled'],
                         'auto_confirm': auto, 'allowed_folders': folders, 'custom_apps': apps})


def guardar_politica(politica: dict, path: Path | None = None) -> dict:
    path = Path(path or POLICY_PATH)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    clean = _sin_entorno(politica)
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding='utf-8')
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return clean


def _sin_entorno(data: dict) -> dict:
    """Normaliza un dict de política sin mezclar autorizaciones por variable de entorno."""
    enabled = [c for c in data.get('enabled', []) if c in CAPACIDADES]
    auto = [c for c in data.get('auto_confirm', []) if c in enabled]
    folders = [str(f)[:400] for f in data.get('allowed_folders', []) if isinstance(f, str)][:30]
    apps = {}
    for name, spec in (data.get('custom_apps') or {}).items():
        if isinstance(name, str) and isinstance(spec, dict) and len(apps) < 40:
            key = name.strip().lower()[:40]
            if key and key.replace('_', '').replace('-', '').isalnum():
                apps[key] = {k: v for k, v in spec.items() if k in ('windows', 'darwin', 'linux')}
    return {'perfil': str(data.get('perfil', 'personalizado'))[:30], 'enabled': enabled or list(PERFILES['basico']),
            'auto_confirm': auto, 'allowed_folders': folders, 'custom_apps': apps}


def cargar_politica_guardada(path: Path | None = None) -> dict:
    """La política tal como está en disco (sin variables de entorno), para editarla."""
    try:
        data = json.loads(Path(path or POLICY_PATH).read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return _sin_entorno(data)
    except (OSError, ValueError):
        pass
    return politica_por_defecto()


def aplicar_perfil(perfil: str, carpetas: list[str] | None = None, path: Path | None = None) -> dict:
    if perfil not in PERFILES:
        raise ValueError('Perfil desconocido. Usá: ' + ', '.join(PERFILES))
    actual = cargar_politica_guardada(path)
    folders = carpetas if carpetas is not None else (actual['allowed_folders'] or
                                                       [f for f in DEFAULT_FOLDERS if Path(f).expanduser().is_dir()])
    return guardar_politica({'perfil': perfil, 'enabled': PERFILES[perfil], 'auto_confirm': AUTO_POR_PERFIL[perfil],
                             'allowed_folders': folders, 'custom_apps': actual['custom_apps']}, path)


def capacidad_de(accion: str) -> str:
    if accion not in ACCION_A_CAPACIDAD:
        raise ValueError('Acción no permitida.')
    return ACCION_A_CAPACIDAD[accion]


def capacidad_para(accion: str, params: dict | None = None) -> str:
    """Capacidad concreta que exige una acción con sus parámetros."""
    params = params or {}
    if accion == 'launch_app':
        return 'launch_app' if params.get('app', '') in APPS_BASICAS else 'apps_extra'
    if accion == 'media_key' and params.get('key') in TECLAS_VOLUMEN:
        return 'volume'
    return capacidad_de(accion)


def accion_habilitada(accion: str, politica: dict, params: dict | None = None) -> bool:
    if accion not in ACCION_A_CAPACIDAD:
        return False
    return capacidad_para(accion, params) in politica['enabled']


def acciones_habilitadas(politica: dict) -> list[str]:
    out = []
    for cap in politica['enabled']:
        for a in CAPACIDADES[cap].acciones:
            if a not in out:
                out.append(a)
    return out


# ---------------------------------------------------------------- parada de emergencia
# Un archivo local que el agente revisa en cada acción: mientras exista, no ejecuta nada (salvo «status»).
# Se activa al instante por voz («SKY, para todo»); levantarla siempre exige un clic del dueño.

def _parada_path() -> Path:
    return Path.home() / '.neuralt' / 'sky_parada.json'


def parada_activa() -> dict | None:
    try:
        datos = json.loads(_parada_path().read_text(encoding='utf-8'))
        return datos if isinstance(datos, dict) else {'motivo': 'parada'}
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {'motivo': 'parada (archivo ilegible)'}


def activar_parada(motivo: str = 'Orden del dueño') -> dict:
    datos = {'motivo': ' '.join(str(motivo).split())[:200], 'desde': datetime.now().isoformat(timespec='seconds')}
    p = _parada_path()
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    p.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
    return datos


def levantar_parada() -> bool:
    try:
        _parada_path().unlink()
        return True
    except FileNotFoundError:
        return False


# Niveles de riesgo (prompt maestro §9): 1 consultar/borradores · 2 modificar o reversible · 3 irreversible/externo.
NIVEL_1 = frozenset({'status', 'list_path', 'open_url', 'launch_app', 'media_control', 'media_key', 'volume', 'play_media',
                     'notify', 'open_file', 'open_path', 'lock_screen', 'player_control', 'voice_control', 'holographic_window'})
NIVEL_3 = frozenset({'note_trash', 'social_action', 'keyboard_shortcut'})
NIVELES_TEXTO = {1: 'bajo riesgo', 2: 'riesgo moderado', 3: 'alto riesgo'}


def nivel_riesgo(accion: str, params: dict | None = None) -> int:
    params = params or {}
    if accion in NIVEL_3:
        return 3
    if accion == 'window_action':
        return 2 if str(params.get('subaction', '')) in ('close', 'minimize', 'organize') else 1
    if accion in NIVEL_1:
        return 1
    return 2


def requiere_confirmacion(accion: str, params: dict, politica: dict) -> bool:
    if nivel_riesgo(accion, params) >= 3:
        return True   # alto riesgo: confirmación expresa por acción, siempre
    return capacidad_para(accion, params) not in politica.get('auto_confirm', [])


# ---------------------------------------------------------------- utilidades

def _sistema() -> str:
    return platform.system().lower()


def _run(cmd: list[str], env_extra: dict | None = None, input_text: str | None = None, timeout: int = 8) -> str:
    """Ejecuta un binario fijo con argumentos en lista (shell=False)."""
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=timeout,
                          env=env, input=input_text)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or 'El sistema rechazó la operación.').strip()[:200])
    return proc.stdout


def _popen(cmd: list[str]):
    subprocess.Popen(cmd, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _primero_disponible(candidatos: list[list[str]]) -> list[str] | None:
    for cmd in candidatos:
        if shutil.which(cmd[0]):
            return cmd
    return None


def _abrir_con_sistema(target: str):
    system = _sistema()
    if system == 'windows':
        os.startfile(target)  # type: ignore[attr-defined]  # sin shell
    elif system == 'darwin':
        _popen(['open', target])
    else:
        _popen(['xdg-open', target])


# ---------------------------------------------------------------- apps

APPS_BASICAS = ['calculator', 'text_editor', 'file_manager', 'browser']

# windows: destino para os.startfile (exe registrado o URI); darwin: nombre para
# `open -a`; linux: comandos candidatos; web: alternativa si no está instalada.
CATALOGO_APPS: dict[str, dict] = {
    'spotify': {'nombre': 'Spotify', 'windows': 'spotify:', 'darwin': 'Spotify', 'linux': [['spotify']], 'web': 'https://open.spotify.com'},
    'vlc': {'nombre': 'VLC', 'windows': 'vlc.exe', 'darwin': 'VLC', 'linux': [['vlc']]},
    'chrome': {'nombre': 'Google Chrome', 'windows': 'chrome.exe', 'darwin': 'Google Chrome', 'linux': [['google-chrome'], ['chromium'], ['chromium-browser']]},
    'firefox': {'nombre': 'Firefox', 'windows': 'firefox.exe', 'darwin': 'Firefox', 'linux': [['firefox']]},
    'edge': {'nombre': 'Microsoft Edge', 'windows': 'msedge.exe', 'darwin': 'Microsoft Edge', 'linux': [['microsoft-edge']]},
    'vscode': {'nombre': 'Visual Studio Code', 'windows': 'vscode:', 'darwin': 'Visual Studio Code', 'linux': [['code']]},
    'word': {'nombre': 'Word', 'windows': 'winword.exe', 'darwin': 'Microsoft Word', 'linux': [['libreoffice', '--writer']], 'web': 'https://www.office.com/launch/word'},
    'excel': {'nombre': 'Excel', 'windows': 'excel.exe', 'darwin': 'Microsoft Excel', 'linux': [['libreoffice', '--calc']], 'web': 'https://www.office.com/launch/excel'},
    'powerpoint': {'nombre': 'PowerPoint', 'windows': 'powerpnt.exe', 'darwin': 'Microsoft PowerPoint', 'linux': [['libreoffice', '--impress']], 'web': 'https://www.office.com/launch/powerpoint'},
    'whatsapp': {'nombre': 'WhatsApp', 'windows': 'whatsapp:', 'darwin': 'WhatsApp', 'linux': [], 'web': 'https://web.whatsapp.com'},
    'telegram': {'nombre': 'Telegram', 'windows': 'tg:', 'darwin': 'Telegram', 'linux': [['telegram-desktop']], 'web': 'https://web.telegram.org'},
    'camera': {'nombre': 'Cámara', 'windows': 'microsoft.windows.camera:', 'darwin': 'Photo Booth', 'linux': [['cheese'], ['guvcview']]},
    'settings': {'nombre': 'Configuración', 'windows': 'ms-settings:', 'darwin': 'System Settings', 'linux': [['gnome-control-center'], ['systemsettings']]},
    'paint': {'nombre': 'Paint', 'windows': 'mspaint.exe', 'darwin': 'Preview', 'linux': [['pinta'], ['kolourpaint']]},
    'music': {'nombre': 'Música', 'windows': 'mswindowsmusic:', 'darwin': 'Music', 'linux': [['rhythmbox'], ['elisa']]},
    'mail': {'nombre': 'Correo', 'windows': 'outlookmail:', 'darwin': 'Mail', 'linux': [['thunderbird'], ['evolution']], 'web': 'https://mail.google.com'},
    'calendar': {'nombre': 'Calendario', 'windows': 'outlookcal:', 'darwin': 'Calendar', 'linux': [['gnome-calendar']], 'web': 'https://calendar.google.com'},
}


def apps_disponibles(politica: dict) -> list[str]:
    apps = []
    if 'launch_app' in politica['enabled']:
        apps += APPS_BASICAS
    if 'apps_extra' in politica['enabled']:
        apps += list(CATALOGO_APPS) + [a for a in politica.get('custom_apps', {}) if a not in CATALOGO_APPS]
    return apps


def abrir_app(app: str, politica: dict) -> str:
    system = _sistema()
    custom = politica.get('custom_apps', {}).get(app)
    if custom and 'apps_extra' in politica['enabled']:
        spec = custom.get(system)
        if not spec:
            raise RuntimeError(f'La app personalizada {app} no tiene comando para este sistema.')
        cmd = spec if isinstance(spec, list) else [spec]
        if not all(isinstance(x, str) for x in cmd):
            raise ValueError('Comando de app personalizada inválido.')
        _popen([os.path.expanduser(cmd[0]), *cmd[1:]])
        return app
    entry = CATALOGO_APPS.get(app)
    if not entry:
        raise ValueError('Esta aplicación no está permitida en el agente.')
    try:
        if system == 'windows':
            os.startfile(entry['windows'])  # type: ignore[attr-defined]
        elif system == 'darwin':
            _run(['open', '-a', entry['darwin']])
        else:
            cmd = _primero_disponible(entry.get('linux', []))
            if not cmd:
                raise FileNotFoundError(app)
            _popen(cmd)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        if entry.get('web'):
            webbrowser.open(entry['web'], new=2)
            return entry['nombre'] + ' (versión web)'
        raise RuntimeError(f'{entry["nombre"]} no está instalada en este equipo.')
    return entry['nombre']


# ---------------------------------------------------------------- multimedia y volumen

_VK = {'play_pause': 0xB3, 'next': 0xB0, 'previous': 0xB1, 'stop': 0xB2,
       'mute': 0xAD, 'down': 0xAE, 'up': 0xAF}


def _tecla_windows(code: int, veces: int = 1):
    import ctypes  # sólo Windows
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    for _ in range(max(1, min(veces, 60))):
        user32.keybd_event(code, 0, 0, 0)
        user32.keybd_event(code, 0, 2, 0)


def control_multimedia(comando: str) -> str:
    if comando not in ('play_pause', 'next', 'previous', 'stop'):
        raise ValueError('Comando multimedia inválido.')
    system = _sistema()
    if system == 'windows':
        _tecla_windows(_VK[comando])
    elif system == 'darwin':
        verbo = {'play_pause': 'playpause', 'next': 'next track', 'previous': 'previous track', 'stop': 'pause'}[comando]
        ok = False
        for app in ('Spotify', 'Music'):
            try:
                corre = _run(['osascript', '-e', f'application "{app}" is running']).strip() == 'true'
                if corre:
                    _run(['osascript', '-e', f'tell application "{app}" to {verbo}'])
                    ok = True
                    break
            except (RuntimeError, OSError, subprocess.SubprocessError):
                continue
        if not ok:
            raise RuntimeError('No hay Spotify ni Música reproduciendo.')
    else:
        if not shutil.which('playerctl'):
            raise RuntimeError('Instalá playerctl para controlar la música en Linux.')
        _run(['playerctl', {'play_pause': 'play-pause', 'next': 'next', 'previous': 'previous', 'stop': 'stop'}[comando]])
    return comando


def volumen(comando: str, nivel: int | None = None) -> str:
    if comando not in ('up', 'down', 'mute', 'set'):
        raise ValueError('Comando de volumen inválido.')
    paso = 10
    if comando == 'set':
        if not isinstance(nivel, int) or not 0 <= nivel <= 100:
            raise ValueError('El nivel de volumen debe estar entre 0 y 100.')
    system = _sistema()
    if system == 'windows':
        if comando == 'set':
            _tecla_windows(_VK['down'], 50)       # cada pulsación ≈ 2 %
            _tecla_windows(_VK['up'], round(nivel / 2)) if nivel else None
        else:
            _tecla_windows(_VK[comando], 1 if comando == 'mute' else paso // 2)
    elif system == 'darwin':
        script = {'up': 'set volume output volume ((output volume of (get volume settings)) + 10)',
                  'down': 'set volume output volume ((output volume of (get volume settings)) - 10)',
                  'mute': 'set volume output muted (not (output muted of (get volume settings)))',
                  'set': f'set volume output volume {nivel}'}[comando]
        _run(['osascript', '-e', script])
    else:
        if shutil.which('pactl'):
            arg = {'up': '+10%', 'down': '-10%', 'set': f'{nivel}%'}.get(comando)
            _run(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', 'toggle'] if comando == 'mute'
                 else ['pactl', 'set-sink-volume', '@DEFAULT_SINK@', arg])
        elif shutil.which('amixer'):
            arg = {'up': '10%+', 'down': '10%-', 'set': f'{nivel}%', 'mute': 'toggle'}[comando]
            _run(['amixer', '-q', 'sset', 'Master', arg])
        else:
            raise RuntimeError('Instalá pactl o amixer para controlar el volumen.')
    return comando if comando != 'set' else f'{nivel}%'


SERVICIOS_MEDIA = {
    'youtube': 'https://www.youtube.com/results?search_query={q}',
    'youtube_music': 'https://music.youtube.com/search?q={q}',
    'spotify': 'https://open.spotify.com/search/{q}',
}


def url_busqueda_media(consulta: str, servicio: str = 'youtube') -> str:
    consulta = ' '.join(str(consulta).split())[:200]
    if not consulta:
        raise ValueError('Decime qué querés reproducir.')
    if servicio not in SERVICIOS_MEDIA:
        raise ValueError('Servicio no soportado: youtube, youtube_music o spotify.')
    q = quote_plus(consulta) if servicio != 'spotify' else quote_plus(consulta).replace('+', '%20')
    return SERVICIOS_MEDIA[servicio].format(q=q)


# ---------------------------------------------------------------- archivos

def resolver_ruta_permitida(ruta: str, politica: dict) -> Path:
    """Resuelve la ruta real y exige que esté dentro de una carpeta autorizada."""
    if not isinstance(ruta, str) or not ruta.strip() or len(ruta) > 1000 or '\x00' in ruta:
        raise ValueError('Ruta inválida.')
    raices = []
    for f in politica.get('allowed_folders', []):
        try:
            raices.append(Path(f).expanduser().resolve(strict=True))
        except (OSError, RuntimeError):
            continue
    if not raices:
        raise ValueError('No autorizaste ninguna carpeta. Usá: python agente_dispositivo.py --carpeta RUTA')
    candidato = Path(ruta.strip()).expanduser()
    if not candidato.is_absolute():
        candidato = raices[0] / candidato
    try:
        real = candidato.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError('El archivo o carpeta no existe.')
    if not any(real == r or r in real.parents for r in raices):
        raise ValueError('Esa ruta está fuera de las carpetas que autorizaste.')
    if real.is_file() and real.suffix.lower() in EXTENSIONES_BLOQUEADAS:
        raise ValueError('Por seguridad SKY no abre programas ni scripts.')
    return real


def abrir_ruta(ruta: str, politica: dict, solo_media: bool = False) -> str:
    real = resolver_ruta_permitida(ruta, politica)
    if solo_media and (not real.is_file() or real.suffix.lower() not in EXTENSIONES_MEDIA):
        raise ValueError('Sólo se reproducen archivos de audio o video.')
    _abrir_con_sistema(str(real))
    return str(real)


def listar_ruta(ruta: str, politica: dict, limite: int = 200) -> dict:
    real = resolver_ruta_permitida(ruta, politica)
    if not real.is_dir():
        raise ValueError('La ruta no es una carpeta.')
    items = []
    for p in sorted(real.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if p.name.startswith('.'):
            continue
        items.append({'nombre': p.name[:120], 'carpeta': p.is_dir()})
        if len(items) >= limite:
            break
    return {'carpeta': str(real), 'elementos': items}


# ---------------------------------------------------------------- notificación, captura, portapapeles, bloqueo

def notificar(titulo: str, mensaje: str) -> str:
    titulo = ' '.join(str(titulo or 'SKY').split())[:80]
    mensaje = ' '.join(str(mensaje or '').split())[:300]
    if not mensaje:
        raise ValueError('La notificación necesita un mensaje.')
    env = {'SKY_TITLE': titulo, 'SKY_MSG': mensaje}  # el texto viaja por entorno, nunca dentro del script
    system = _sistema()
    if system == 'windows':
        ps = ('Add-Type -AssemblyName System.Windows.Forms;$n=New-Object System.Windows.Forms.NotifyIcon;'
              '$n.Icon=[System.Drawing.SystemIcons]::Information;$n.Visible=$true;'
              '$n.ShowBalloonTip(6000,$env:SKY_TITLE,$env:SKY_MSG,"Info");Start-Sleep -s 7;$n.Dispose()')
        env_full = dict(os.environ, **env)
        subprocess.Popen(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], shell=False, env=env_full,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif system == 'darwin':
        _run(['osascript', '-e', 'display notification (system attribute "SKY_MSG") with title (system attribute "SKY_TITLE")'], env)
    else:
        if not shutil.which('notify-send'):
            raise RuntimeError('Instalá notify-send (libnotify) para notificaciones.')
        _run(['notify-send', titulo, mensaje])
    return mensaje


def captura_pantalla() -> dict:
    CAPTURE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    destino = CAPTURE_DIR / f'sky_{datetime.now():%Y%m%d_%H%M%S}.png'
    try:
        from PIL import ImageGrab
        ImageGrab.grab().save(destino)
    except Exception:
        system = _sistema()
        if system == 'darwin':
            _run(['screencapture', '-x', str(destino)])
        else:
            cmd = _primero_disponible([['gnome-screenshot', '-f', str(destino)], ['scrot', str(destino)],
                                       ['grim', str(destino)]])
            if not cmd:
                raise RuntimeError('No hay herramienta de captura disponible.')
            _run(cmd, timeout=15)
    if not destino.exists():
        raise RuntimeError('No se pudo guardar la captura.')
    try:
        destino.chmod(0o600)
    except OSError:
        pass
    return {'archivo': str(destino), 'bytes': destino.stat().st_size}


def portapapeles_leer() -> str:
    system = _sistema()
    if system == 'windows':
        out = _run(['powershell', '-NoProfile', '-NonInteractive', '-Command', 'Get-Clipboard -Raw'])
    elif system == 'darwin':
        out = _run(['pbpaste'])
    else:
        cmd = _primero_disponible([['wl-paste', '--no-newline'], ['xclip', '-selection', 'clipboard', '-o'],
                                   ['xsel', '--clipboard', '--output']])
        if not cmd:
            raise RuntimeError('Instalá wl-clipboard o xclip.')
        out = _run(cmd)
    return out[:10000]


def portapapeles_escribir(texto: str) -> int:
    texto = str(texto or '')
    if not texto or len(texto) > 10000:
        raise ValueError('El texto debe tener entre 1 y 10000 caracteres.')
    system = _sistema()
    if system == 'windows':
        _run(['powershell', '-NoProfile', '-NonInteractive', '-Command', 'Set-Clipboard -Value $env:SKY_CLIP'],
             {'SKY_CLIP': texto})
    elif system == 'darwin':
        _run(['pbcopy'], input_text=texto)
    else:
        cmd = _primero_disponible([['wl-copy'], ['xclip', '-selection', 'clipboard'], ['xsel', '--clipboard', '--input']])
        if not cmd:
            raise RuntimeError('Instalá wl-clipboard o xclip.')
        _run(cmd, input_text=texto)
    return len(texto)


def bloquear_pantalla() -> str:
    system = _sistema()
    if system == 'windows':
        import ctypes
        if not ctypes.windll.user32.LockWorkStation():  # type: ignore[attr-defined]
            raise RuntimeError('Windows no permitió bloquear la sesión.')
    elif system == 'darwin':
        _run(['pmset', 'displaysleepnow'])
    else:
        cmd = _primero_disponible([['loginctl', 'lock-session'], ['xdg-screensaver', 'lock'], ['gnome-screensaver-command', '-l']])
        if not cmd:
            raise RuntimeError('No se encontró un bloqueador de sesión.')
        _run(cmd)
    return 'bloqueado'


def info_sistema() -> dict:
    data = {}
    try:
        import psutil  # opcional
        data['cpu_percent'] = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        data['memoria_percent'] = mem.percent
        bat = psutil.sensors_battery() if hasattr(psutil, 'sensors_battery') else None
        if bat:
            data['bateria_percent'] = round(bat.percent)
            data['cargando'] = bool(bat.power_plugged)
    except Exception:
        pass
    return data


# ---------------------------------------------------------------- validación de URL

def validar_url_https(url: str) -> str:
    url = str(url or '')
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or len(url) > 2000:
        raise ValueError('Sólo se admiten páginas HTTPS normales.')
    return url
