"""Lanzador unificado y supervisor autónomo de SKY-IA para Windows (v12.6: una sola instancia, preparación real).

Desacopla el núcleo de ejecución, el agente Windows (8766) y la voz continua
de la interfaz Streamlit (8501), evitando conflictos de puertos y procesos huérfanos.

Uso:
    python iniciar_sky_autonomo.py                 # SKY completo: Agente + API + Voz + interfaz HUD
    python iniciar_sky_autonomo.py --minimized     # Igual, sin abrir el navegador (inicio con Windows)
    python iniciar_sky_autonomo.py --with-ui       # Autónomo + Panel Streamlit opcional
    python iniciar_sky_autonomo.py --status        # Diagnóstico: estado, causa concreta y pasos por servicio
    python iniciar_sky_autonomo.py --stop          # Cierre limpio de la instancia que está corriendo
    python iniciar_sky_autonomo.py --kill-ports    # Libera puertos SÓLO de procesos que este supervisor inició
    python iniciar_sky_autonomo.py --install-startup   # Configurar inicio con Windows (sin admin)
    python iniciar_sky_autonomo.py --uninstall-startup # Desactivar inicio con Windows

Garantías (v12.6):
  * Una sola instancia: un candado del sistema operativo (~/.neuralt/sky_supervisor.lock). Un segundo arranque NO
    cierra la instancia sana: avisa, abre la interfaz y termina.
  * Nunca cierra un proceso por ocupar un puerto. Sólo administra procesos que él mismo inició (PID + hora de
    creación + línea de comandos registrados), y si hay un SKY sano de antes, lo adopta sin reiniciarlo.
  * Anuncia «listo» sólo cuando cada servicio pasa su comprobación de preparación.
  * Reinicia servicios caídos con espera progresiva (2, 4, 8, 16, 32 s; máximo 5 por hora y luego reintenta cada
    30 min). Las fallas permanentes (falta un modelo o una dependencia) no se reintentan en bucle.
  * Detecta procesos colgados con criterios que no confunden una inferencia lenta con un fallo: la salud de la API es
    asíncrona (responde aunque el modelo esté ocupado) y la voz late desde el hilo del micrófono, no del modelo.
  * Registros rotativos en local_data/logs y cierre limpio (CTRL+BREAK / SIGTERM antes de forzar).
  * Con PIN configurado, al iniciar bloquea la sesión del dueño: SKY pregunta «¿Cuál es tu PIN?».
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Dict, List, Optional

WORKSPACE = Path(__file__).resolve().parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))
VENV_PYTHON = WORKSPACE / ".venv" / "Scripts" / "python.exe"
VENV_PYTHONW = WORKSPACE / ".venv" / "Scripts" / "pythonw.exe"
PYTHON_EXE = str(VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable))

PORTS = {
    "api": 8765,
    "agent": 8766,
    "streamlit": 8501
}
WHATSAPP_PORT = int(os.getenv("SKY_WA_PORT", "8770") or 8770)

# Códigos de salida acordados con los servicios: 2 = falta configuración/dependencia (no reintentar en bucle),
# 3 = falta el micrófono (reintentar cada 5 minutos, por si lo conectás).
SALIDA_NO_CONFIGURADO = 2
SALIDA_SIN_MICROFONO = 3
ESPERA_TRAS_LIMITE = 30 * 60
MAX_REINICIOS_HORA = 5


def dir_estado() -> Path:
    return Path(os.getenv("SKY_SUPERVISOR_DIR") or (Path.home() / ".neuralt"))


def dir_logs() -> Path:
    return Path(os.getenv("SKY_LOG_DIR") or (WORKSPACE / "local_data" / "logs"))


def _ruta_candado() -> Path:
    return dir_estado() / "sky_supervisor.lock"


def _ruta_estado() -> Path:
    return dir_estado() / "sky_supervisor.json"


def _ruta_parar() -> Path:
    return dir_estado() / "sky_supervisor.parar"


log = logging.getLogger("sky.supervisor")


def _configurar_registro() -> None:
    if log.handlers:
        return
    log.setLevel(logging.INFO)
    try:
        dir_logs().mkdir(parents=True, exist_ok=True)
        h = RotatingFileHandler(dir_logs() / "supervisor.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(h)
    except OSError:
        pass


def _decir(msg: str) -> None:
    """A la consola (si existe) y al registro rotativo."""
    try:
        print(msg, flush=True)
    except (OSError, ValueError, AttributeError):
        pass
    log.info(msg)


# ------------------------------------------------------------------ puertos e identidad de procesos

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Comprueba si un puerto local está ocupado."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        try:
            return s.connect_ex((host, port)) == 0
        except OSError:
            return False


def es_servicio_sky(port: int) -> bool:
    """True sólo si quien ocupa el puerto es una instancia de SKY (API o agente)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/api/health", timeout=1.5) as resp:
            if "SKY" in json.loads(resp.read(4096).decode("utf-8", "replace")).get("service", ""):
                return True
    except urllib.error.HTTPError as err:
        if "SKY" in (err.headers.get("Server") or ""):
            return True
    except Exception:
        pass
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/status", timeout=1.5) as resp:
            return "SKY" in (resp.headers.get("Server") or "")
    except urllib.error.HTTPError as err:
        return "SKY" in (err.headers.get("Server") or "")
    except Exception:
        return False


def get_pid_using_port(port: int) -> Optional[int]:
    """PID que ESCUCHA en el puerto local (Windows, netstat). v12.6: sólo líneas LISTENING del puerto local;
    antes podía devolver el PID de un cliente conectado o de una conexión TIME_WAIT."""
    if os.name != "nt":
        return None
    try:
        out = subprocess.check_output(['netstat', '-ano', '-p', 'tcp'], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and parts[3].upper() == "LISTENING" and parts[1].endswith(f":{int(port)}"):
                pid = int(parts[-1])
                return pid if pid > 4 else None
    except Exception:
        pass
    return None


def kill_process_by_pid(pid: int) -> bool:
    """Finaliza un proceso de manera forzada (sólo se usa con procesos verificados como propios)."""
    if not pid or pid <= 4:
        return False
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(int(pid))], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(int(pid), signal.SIGKILL)
        return True
    except Exception:
        return False


def _identidad(pid: int) -> Optional[dict]:
    """Hora de creación y línea de comandos de un PID (psutil). None si no existe o no se puede verificar."""
    try:
        import psutil
        p = psutil.Process(int(pid))
        return {"create_time": p.create_time(), "cmdline": p.cmdline()}
    except Exception:
        return None


def _registro_estado() -> dict:
    try:
        from neural_core.sky_archivo_seguro import leer_json
        d = leer_json(_ruta_estado(), {})
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _es_propio(reg: dict) -> bool:
    """El PID registrado sigue siendo EL proceso que este supervisor inició (no un PID reutilizado por otro programa)."""
    ident = _identidad(reg.get("pid", 0)) if reg else None
    if not ident:
        return False
    if abs(float(ident["create_time"]) - float(reg.get("create_time") or 0)) > 1.0:
        return False
    linea = " ".join(ident["cmdline"])
    return bool(reg.get("firma")) and reg["firma"] in linea


def clean_port_conflicts(ports: List[int]) -> Dict[int, bool]:
    """Libera puertos SÓLO si los ocupa un proceso que este supervisor registró como propio (y no hay otra instancia
    del supervisor en marcha). Nunca toca otros programas ni otras instancias de SKY que no inició."""
    results: Dict[int, bool] = {}
    supervisor_activo = _supervisor_en_marcha()
    registro = _registro_estado().get("servicios", {})
    for p in ports:
        if not is_port_in_use(p):
            results[p] = True
            continue
        if not es_servicio_sky(p):
            _decir(f"[SKY] El puerto {p} lo usa otro programa; no se toca.")
            results[p] = False
            continue
        if supervisor_activo:
            _decir(f"[SKY] El puerto {p} pertenece a la instancia de SKY en marcha. Usá --stop para cerrarla limpio.")
            results[p] = False
            continue
        pid = get_pid_using_port(p)
        propio = next((r for r in registro.values() if r.get("pid") == pid and _es_propio(r)), None) if pid else None
        if propio:
            _decir(f"[SKY] Cerrando proceso huérfano propio en el puerto {p} (PID {pid})...")
            results[p] = kill_process_by_pid(pid)
        else:
            _decir(f"[SKY] El puerto {p} lo ocupa un SKY que este supervisor no inició (PID {pid or '?'}); no se cierra. "
                   "Cerralo desde el Administrador de tareas si es necesario.")
            results[p] = False
    return results


# ------------------------------------------------------------------ comprobaciones (salud y preparación)

def _get_json(url: str, timeout: float = 2.0, headers: Optional[dict] = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            try:
                return resp.status, json.loads(resp.read(65536).decode("utf-8", "replace"))
            except ValueError:
                return resp.status, {}
    except urllib.error.HTTPError as err:
        try:
            return err.code, json.loads(err.read(65536).decode("utf-8", "replace"))
        except Exception:
            return err.code, {}


def sonda_api(port: int = PORTS["api"]) -> tuple[bool, str]:
    try:
        code, data = _get_json(f"http://127.0.0.1:{port}/api/health", 3.0)
    except Exception as exc:
        return False, f"no responde ({type(exc).__name__})"
    if code != 200 or "SKY" not in str(data.get("service", "")):
        return False, f"respuesta inesperada (HTTP {code})"
    return True, "responde"


def preparacion_api(port: int = PORTS["api"]) -> tuple[bool, str]:
    ok, det = sonda_api(port)
    if not ok:
        return ok, det
    try:
        code, data = _get_json(f"http://127.0.0.1:{port}/api/health/listo", 5.0)
    except Exception as exc:
        return False, f"preparación sin respuesta ({type(exc).__name__})"
    if code == 404:
        return True, "responde (versión sin comprobación de preparación)"
    if code != 200:
        fallos = [k for k, v in (data.get("componentes") or {}).items() if not v.get("ok")]
        return False, "no está lista: " + (", ".join(fallos) or f"HTTP {code}")
    return True, "lista"


def _token_agente() -> str:
    try:
        from neural_core.sky_voice_actions import local_agent_credentials
        return local_agent_credentials()[1] or ""
    except Exception:
        return ""


def sonda_agente(port: int = PORTS["agent"]) -> tuple[bool, str]:
    token = _token_agente()
    try:
        code, _ = _get_json(f"http://127.0.0.1:{port}/status", 3.0,
                            {"Authorization": f"Bearer {token}"} if token else None)
    except Exception as exc:
        return False, f"no responde ({type(exc).__name__})"
    if code == 200:
        return True, "responde"
    if code == 401 and es_servicio_sky(port):
        return True, "responde (token de emparejamiento distinto)"
    return False, f"HTTP {code}"


def estado_escucha() -> dict:
    from neural_core.sky_archivo_seguro import leer_json
    d = leer_json(WORKSPACE / "local_data" / "sky_session_state.json", {})
    return d if isinstance(d, dict) else {}


def sonda_voz(pid: Optional[int] = None, max_latido: float = 15.0) -> tuple[bool, str]:
    d = estado_escucha()
    if pid and d.get("pid") not in (None, pid):
        return False, "todavía no informó su estado"
    try:
        edad = time.time() - float(d.get("last_seen") or 0)
    except (TypeError, ValueError):
        edad = 1e9
    if not d.get("hands_free_listening") or d.get("status") == "stopped":
        return False, "no está escuchando"
    if edad > max_latido:
        return False, f"sin latido hace {int(edad)} s"
    return True, "escuchando" + (" (sesión bloqueada: espera el PIN)" if d.get("sesion_bloqueada") else "")


def _pid_escucha_vivo() -> Optional[int]:
    """PID de la escucha manos libres que informó estado, si ese proceso sigue vivo y es la escucha de SKY."""
    pid = estado_escucha().get("pid")
    if not pid:
        return None
    ident = _identidad(int(pid))
    return int(pid) if ident and "sky_manos_libres.py" in " ".join(ident["cmdline"]) else None


def sonda_puerto(port: int, ruta: str = "") -> Callable[[], tuple[bool, str]]:
    def sonda() -> tuple[bool, str]:
        if not ruta:
            return (True, "puerto abierto") if is_port_in_use(port) else (False, "puerto cerrado")
        try:
            code, _ = _get_json(f"http://127.0.0.1:{port}{ruta}", 2.0)
        except Exception as exc:
            return False, f"no responde ({type(exc).__name__})"
        return (code == 200), f"HTTP {code}"
    return sonda


def requisitos_voz(model_dir: Path) -> List[str]:
    """Qué falta exactamente para la escucha manos libres (sin importar módulos pesados)."""
    import importlib.util
    faltan = []
    if not model_dir.is_dir():
        faltan.append(f"modelo Vosk en {model_dir} (descargá vosk-model-small-es y descomprimilo ahí)")
    for mod, pip in (("vosk", "vosk"), ("sounddevice", "sounddevice"), ("pyttsx3", "pyttsx3")):
        if importlib.util.find_spec(mod) is None:
            faltan.append(f"paquete {pip} (pip install {pip})")
    return faltan


# ------------------------------------------------------------------ diagnóstico

def _ultimas_lineas(nombre: str, n: int = 4) -> str:
    try:
        texto = (dir_logs() / f"{nombre}.log").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    acceso = re.compile(r'"(?:GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD) \S+ HTTP/')
    lineas = [l for l in texto.splitlines() if l.strip() and not acceso.search(l) and not l.startswith("=====")][-n:]
    limpio = re.sub(r"[A-Za-z0-9_\-]{32,}", "[oculto]", " | ".join(lineas))   # nunca mostrar tokens
    return limpio[-400:]


def _supervisor_en_marcha() -> bool:
    try:
        from neural_core.sky_archivo_seguro import CandadoInstancia
        return CandadoInstancia(_ruta_candado()).ocupado()
    except Exception:
        return False


PASOS = {
    "api": "Revisá local_data/logs/api.log. Si el puerto 8765 lo usa otro programa, cerralo o cambiá el puerto.",
    "agent": "Revisá local_data/logs/agent.log y la política con: python agente_dispositivo.py --ver-politica",
    "voice": "Conectá un micrófono, instalá vosk/sounddevice/pyttsx3 y el modelo en modelos/vosk-model-es.",
    "whatsapp": "Revisá .env (SKY_WA_*) y docs/guias/SKY_WHATSAPP.md.",
    "streamlit": "Instalá streamlit (pip install streamlit) y revisá local_data/logs/streamlit.log.",
}


def check_system_status() -> Dict[str, dict]:
    """Diagnóstico detallado de los componentes de SKY-IA, con causa concreta y pasos de recuperación."""
    status: Dict[str, dict] = {}
    registro = _registro_estado()
    servicios = registro.get("servicios", {}) if _supervisor_en_marcha() else {}

    # 1. Agente Windows (8766)
    agent_port = PORTS["agent"]
    agent_up = is_port_in_use(agent_port)
    agent_info = {"port": agent_port, "listening": agent_up, "status": "offline"}
    if agent_up:
        ok, det = sonda_agente(agent_port)
        agent_info["status"] = "online" if ok else f"error: {det}"
        if ok:
            token = _token_agente()
            try:
                code, data = _get_json(f"http://127.0.0.1:{agent_port}/status", 2.0,
                                       {"Authorization": f"Bearer {token}"} if token else None)
                if code == 200:
                    agent_info["device"] = data.get("device", "Windows")
                    agent_info["capabilities"] = data.get("capabilities", [])
            except Exception:
                pass
    status["agent"] = agent_info

    # 2. Metaverso / API (8765). v12.6: si la salud falla, NO se informa «online».
    api_port = PORTS["api"]
    api_up = is_port_in_use(api_port)
    api_info = {"port": api_port, "listening": api_up, "status": "offline"}
    if api_up:
        ok, det = preparacion_api(api_port)
        if ok:
            api_info["status"] = "online"
        elif "no responde" in det or "inesperada" in det:
            api_info["status"] = "error: el puerto está ocupado pero " + det
        else:
            api_info["status"] = "degradado: " + det
    status["api"] = api_info

    # 3. Streamlit UI (8501)
    st_port = PORTS["streamlit"]
    st_up = is_port_in_use(st_port)
    status["streamlit"] = {"port": st_port, "listening": st_up, "status": "online" if st_up else "offline"}

    # 4. Voz: el modo «sesión activa» no prueba que el proceso siga escuchando; se exige latido reciente.
    voice_state_file = WORKSPACE / "local_data" / "voice_coordinator_state.json"
    voice_info = {"configured": False, "mode": "desconocido", "active": False}
    try:
        from neural_core.sky_archivo_seguro import leer_json
        v_data = leer_json(voice_state_file, None)
        if isinstance(v_data, dict):
            voice_info["configured"] = True
            voice_info["mode"] = v_data.get("active_mode", "MODO_A_NATURAL")
            voice_info["state"] = v_data.get("current_state", "ESPERANDO_ACTIVACION")
            voice_info["active"] = v_data.get("is_session_active", False)
    except Exception:
        pass
    from neural_core.sky_listening_status import resumen_escucha
    voice_info.update(resumen_escucha(estado_escucha()))
    faltan = requisitos_voz(WORKSPACE / "modelos" / "vosk-model-es")
    if faltan:
        voice_info["faltan"] = faltan
    status["voice"] = voice_info
    status["chat_texto"] = {
        "disponible": api_info["status"] == "online",
        "requiere_hud_abierto": False,
    }

    # 5. Supervisor y sesión del dueño
    status["supervisor"] = {"en_marcha": bool(servicios) or _supervisor_en_marcha(), "pid": registro.get("pid"),
                            "servicios": {n: {k: s.get(k) for k in ("estado", "causa", "reinicios", "pasos")}
                                          for n, s in servicios.items()}}
    try:
        from neural_core.sentinel_identidad import estado_sesion
        e = estado_sesion()
        status["sesion"] = {"pin": e["pin"], "bloqueada": e["bloqueada"], "motivo": e.get("motivo", "")}
    except Exception as exc:
        status["sesion"] = {"error": type(exc).__name__}

    # 6. Causa y pasos concretos para lo que no está bien
    problemas = []
    if not api_up:
        problemas.append({"servicio": "api", "causa": "la API no está corriendo en 127.0.0.1:8765",
                          "pasos": "Iniciá SKY: python iniciar_sky_autonomo.py"})
    elif api_info["status"] != "online":
        problemas.append({"servicio": "api", "causa": api_info["status"], "pasos": PASOS["api"]})
    if agent_up and agent_info["status"] != "online":
        problemas.append({"servicio": "agent", "causa": agent_info["status"], "pasos": PASOS["agent"]})
    if faltan:
        problemas.append({"servicio": "voice", "causa": "falta: " + "; ".join(faltan), "pasos": PASOS["voice"]})
    for n, s in servicios.items():
        if s.get("estado") not in ("activo", "externo", "cargando"):
            problemas.append({"servicio": n, "causa": s.get("causa") or s.get("estado"), "pasos": s.get("pasos") or PASOS.get(n, "")})
    status["problemas"] = problemas
    return status


# ------------------------------------------------------------------ inicio con Windows

def manage_windows_startup(install: bool = True) -> bool:
    """Configura o desactiva el inicio automático de SKY al iniciar sesión en Windows (sin admin).
    Corre en TU sesión (no como servicio) para tener micrófono, audio y apps de escritorio. v12.6: usa pythonw.exe
    (sin ventana de consola que cerrar por error); la salida va a local_data/logs."""
    if os.name != "nt":
        _decir("[SKY] El inicio automático solo está disponible en Windows.")
        return False

    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_bat = startup_dir / "SKY_IA_Autonomo.bat"

    if install:
        lanzador = str(VENV_PYTHONW if VENV_PYTHONW.exists() else PYTHON_EXE)
        content = f'@echo off\r\ncd /d "{WORKSPACE}"\r\nstart "" "{lanzador}" iniciar_sky_autonomo.py --minimized\r\n'
        try:
            startup_dir.mkdir(parents=True, exist_ok=True)
            shortcut_bat.write_text(content, encoding="ascii")
            _decir("[SKY] Inicio automático configurado con éxito en:")
            _decir(f"      {shortcut_bat}")
            return True
        except Exception as e:
            _decir(f"[SKY] Error al configurar inicio automático: {e}")
            return False
    else:
        try:
            if shortcut_bat.exists():
                shortcut_bat.unlink()
                _decir("[SKY] Inicio automático desactivado con éxito.")
            else:
                _decir("[SKY] El inicio automático no estaba configurado.")
            return True
        except Exception as e:
            _decir(f"[SKY] Error al eliminar inicio automático: {e}")
            return False


def _whatsapp_configurado() -> bool:
    try:
        from dotenv import load_dotenv
        load_dotenv(WORKSPACE / ".env", override=False)
    except Exception:
        pass
    try:
        from neural_core.sky_whatsapp import configurado
        return configurado()
    except Exception:
        return False


def _registrar_reinicio(name: str, codigo) -> None:
    try:
        from neural_core import sky_metricas
        sky_metricas.registrar("servicio", "reinicio", False, detalle=f"{name}: {codigo}")
    except Exception:
        pass


# ------------------------------------------------------------------ supervisor

@dataclass
class Servicio:
    nombre: str
    args: list
    env: Optional[dict] = None
    puerto: Optional[int] = None
    sonda: Optional[Callable[[], tuple]] = None          # vivo (liveness)
    preparado: Optional[Callable[[], tuple]] = None      # listo (readiness)
    espera_preparacion: float = 30.0
    colgado_tras: float = 90.0                           # sin respuesta durante este tiempo y vivo → colgado
    requerido: bool = False
    firma: str = ""
    # estado vivo
    proc: Optional[subprocess.Popen] = None
    externo: bool = False
    estado: str = "detenido"
    causa: str = ""
    reinicios: List[float] = field(default_factory=list)
    proximo_intento: float = 0.0
    fallas_sonda: int = 0
    primera_falla: float = 0.0
    ultima_sonda: float = 0.0
    iniciado: float = 0.0
    log_f: object = None


class SkySupervisor:
    """Supervisor unificado de procesos de SKY-IA."""

    def __init__(self, with_ui: bool = False, execute_safe: bool = True, with_voice: bool = True,
                 open_browser: bool = True):
        self.open_browser = open_browser
        self.reported: set[str] = set()
        self.with_ui = with_ui
        self.execute_safe = execute_safe
        self.with_voice = with_voice
        self.processes: Dict[str, subprocess.Popen] = {}
        self.specs: Dict[str, tuple] = {}
        self.reinicios: Dict[str, list] = {}
        self.servicios: Dict[str, Servicio] = {}
        self.running = False
        self._candado = None
        self.intervalo_sonda = 10.0

    # ---------------------------------------------------------- arranque
    def start_all(self) -> bool:
        _configurar_registro()
        from neural_core.sky_archivo_seguro import CandadoInstancia
        self._candado = CandadoInstancia(_ruta_candado())
        if not self._candado.adquirir():
            pid = _registro_estado().get("pid", "?")
            _decir(f"[SKY] SKY ya está en ejecución (supervisor PID {pid}). No se inicia otra instancia ni se "
                   "interrumpen sus servicios.")
            _decir(f"[SKY] Interfaz: http://127.0.0.1:{PORTS['api']}/   ·   Estado: python iniciar_sky_autonomo.py --status")
            if self.open_browser:
                self._abrir_interfaz()
            return False
        try:
            _ruta_parar().unlink()
        except OSError:
            pass

        _decir("==============================================================")
        _decir("               SKY IA — INICIO AUTÓNOMO DE ESCRITORIO          ")
        _decir("==============================================================")
        _decir(f"[SKY] Intérprete Python: {PYTHON_EXE}")
        _decir(f"[SKY] Directorio Base:   {WORKSPACE}")
        _decir(f"[SKY] Registros:         {dir_logs()}")

        # Sesión del dueño: al iniciar SKY, queda bloqueada hasta el PIN (si hay PIN configurado).
        try:
            from neural_core.sentinel_identidad import bloquear_sesion, pin_configurado
            if bloquear_sesion("inicio de SKY", "arranque"):
                _decir("[SKY] Sesión bloqueada hasta tu PIN: SKY va a preguntarte «¿Cuál es tu PIN?».")
            elif not pin_configurado():
                _decir("[AVISO] SKY no tiene PIN: cualquiera frente a tu PC o cerca del micrófono puede usarla. "
                       "Configuralo con: python sky_pin.py configurar")
        except Exception as exc:
            _decir(f"[AVISO] No pude comprobar la sesión del dueño: {type(exc).__name__}")

        for srv in self._definir_servicios():
            self.servicios[srv.nombre] = srv
        # La API es imprescindible: si su puerto lo usa otro programa, no se sigue.
        api = self.servicios["api"]
        if is_port_in_use(PORTS["api"]) and not es_servicio_sky(PORTS["api"]):
            _decir("[SKY] El puerto 8765 lo usa otro programa (no es SKY). No se cierra.")
            self._candado.liberar()
            sys.exit("[SKY] Liberá el puerto 8765 o cerrá ese programa y volvé a intentar.")

        for srv in self.servicios.values():
            self._arrancar_o_adoptar(srv)
        self._guardar_estado()
        self.running = True

        # Anunciar sólo lo que pasó la comprobación de preparación.
        listos = self._esperar_preparacion()
        if api.estado in ("activo", "externo") and self.open_browser:
            self._abrir_interfaz()
        _decir(f"\n[SKY] Interfaz HUD: http://127.0.0.1:{PORTS['api']}/")
        requeridos = [s for s in self.servicios.values() if s.requerido]
        if all(s.estado in ("activo", "externo") for s in requeridos):
            _decir(f"[SKY] Listo: {listos} de {len(self.servicios)} servicios preparados y supervisados.")
        else:
            caidos = ", ".join(f"{s.nombre} ({s.causa})" for s in requeridos if s.estado not in ("activo", "externo"))
            _decir(f"[AVISO] SKY arrancó con servicios esenciales sin preparar: {caidos}. Sigo intentando.")
        for s in self.servicios.values():
            if s.estado not in ("activo", "externo"):
                _decir(f"[SKY] {s.nombre}: {s.estado} — {s.causa}")
        _decir("[SKY] Cerrar el navegador o el HUD NO detiene a SKY. Para detenerla: python iniciar_sky_autonomo.py --stop")
        self._guardar_estado()
        return True

    def _abrir_interfaz(self) -> None:
        try:
            import webbrowser
            webbrowser.open(f"http://127.0.0.1:{PORTS['api']}/")
        except Exception:
            pass

    def _definir_servicios(self) -> List[Servicio]:
        agent_env = os.environ.copy()
        agent_env["SKY_DEVICE_PORT"] = str(PORTS["agent"])
        servicios = [
            Servicio("agent", [PYTHON_EXE, str(WORKSPACE / "agente_dispositivo.py")], agent_env, PORTS["agent"],
                     sonda=lambda: sonda_agente(PORTS["agent"]), preparado=lambda: sonda_agente(PORTS["agent"]),
                     espera_preparacion=20, colgado_tras=90, requerido=True, firma="agente_dispositivo.py"),
            # --no-access-log: las rutas pueden llevar tus consultas (?q=…); los KPIs ya miden cada llamada sin contenido.
            Servicio("api", [PYTHON_EXE, "-m", "uvicorn", "metaverse.api:app", "--host", "127.0.0.1", "--port", str(PORTS["api"]),
                             "--no-access-log"],
                     None, PORTS["api"], sonda=lambda: sonda_api(PORTS["api"]),
                     preparado=lambda: preparacion_api(PORTS["api"]), espera_preparacion=90, colgado_tras=90,
                     requerido=True, firma="metaverse.api:app"),
        ]
        # Motor cognitivo adicional integrado en SKY (opt-in). Nunca reemplaza el núcleo ni ocupa un puerto ajeno.
        try:
            from neural_core.sky_openjarvis_boot import launch_spec
            spec = launch_spec()
            if spec:
                from neural_core.sky_openjarvis import _base_url
                jarvis_port = int(_base_url().rsplit(":", 1)[1])
                servicios.append(Servicio("openjarvis", spec[0], None, jarvis_port, sonda=sonda_puerto(jarvis_port),
                                          preparado=sonda_puerto(jarvis_port), espera_preparacion=60,
                                          firma="openjarvis"))
        except (ValueError, FileNotFoundError, OSError, ImportError) as exc:
            _decir(f"[SKY] OpenJarvis opcional no iniciado: {exc}")
        if _whatsapp_configurado():
            servicios.append(Servicio("whatsapp", [PYTHON_EXE, str(WORKSPACE / "sky_whatsapp_puente.py")], None,
                                      WHATSAPP_PORT, sonda=sonda_puerto(WHATSAPP_PORT, "/salud"),
                                      preparado=sonda_puerto(WHATSAPP_PORT, "/salud"), firma="sky_whatsapp_puente.py"))
        try:
            from dotenv import load_dotenv
            load_dotenv(WORKSPACE / ".env", override=False)
        except Exception:
            pass
        if os.getenv("SKY_SOCIAL_WORKER_ENABLED", "0") == "1":
            # Nunca crea, aprueba ni publica borradores sin aprobación del dueño.
            servicios.append(Servicio("social_hub", [PYTHON_EXE, str(WORKSPACE / "sky_social_worker.py")],
                                      firma="sky_social_worker.py"))
        if self.with_voice:
            model_dir = WORKSPACE / "modelos" / "vosk-model-es"
            voice_args = [PYTHON_EXE, str(WORKSPACE / "sky_manos_libres.py"), "--model", str(model_dir)]
            if self.execute_safe:
                voice_args.append("--execute-safe")
            voz = Servicio("voice", voice_args, None, None, espera_preparacion=60, colgado_tras=90,
                           firma="sky_manos_libres.py")
            voz.sonda = lambda v=voz: sonda_voz(v.proc.pid if v.proc else _pid_escucha_vivo())
            voz.preparado = lambda v=voz: sonda_voz(v.proc.pid if v.proc else None)
            faltan = requisitos_voz(model_dir)
            if faltan:
                voz.estado, voz.causa = "no_configurado", "falta: " + "; ".join(faltan)
                _decir("[SKY] Voz manos libres no configurada: " + "; ".join(faltan))
                _decir("      La interfaz HUD igual escucha con el micrófono del navegador (botón del núcleo).")
            servicios.append(voz)
        if self.with_ui:
            servicios.append(Servicio("streamlit", [PYTHON_EXE, "-m", "streamlit", "run", "app.py", "--server.port",
                                                    str(PORTS["streamlit"]), "--server.address", "127.0.0.1",
                                                    "--server.headless", "true"],
                                      None, PORTS["streamlit"], sonda=sonda_puerto(PORTS["streamlit"], "/_stcore/health"),
                                      preparado=sonda_puerto(PORTS["streamlit"], "/_stcore/health"),
                                      espera_preparacion=60, firma="streamlit"))
        return servicios

    def _arrancar_o_adoptar(self, srv: Servicio) -> None:
        if srv.estado == "no_configurado":
            return
        if srv.nombre == "voice" and _pid_escucha_vivo() and sonda_voz()[0]:
            # Dos escuchas a la vez duplicarían órdenes: se adopta la que ya está viva.
            srv.externo, srv.estado, srv.causa = True, "externo", "la escucha ya estaba en marcha; se supervisa sin reiniciarla"
            _decir("[SKY] voice: ya había una escucha manos libres activa; la adopto sin duplicarla.")
            return
        if srv.puerto and is_port_in_use(srv.puerto):
            ok, det = srv.sonda() if srv.sonda else (False, "sin comprobación")
            if ok and (srv.nombre not in ("api", "agent") or es_servicio_sky(srv.puerto)):
                # Un SKY sano de una ejecución anterior: se adopta, no se interrumpe.
                srv.externo, srv.estado, srv.causa = True, "externo", "ya estaba en marcha; se supervisa sin reiniciarlo"
                _decir(f"[SKY] {srv.nombre}: ya estaba activo en el puerto {srv.puerto}; lo adopto sin reiniciarlo.")
                return
            reg = _registro_estado().get("servicios", {}).get(srv.nombre, {})
            if reg and get_pid_using_port(srv.puerto) in (reg.get("pid"), None) and _es_propio(reg):
                _decir(f"[SKY] {srv.nombre}: proceso propio anterior que no responde (PID {reg['pid']}); lo cierro.")
                self._terminar_pid(int(reg["pid"]))
            elif srv.nombre != "agent":   # el agente sabe usar otro puerto libre
                srv.estado = "error"
                srv.causa = f"el puerto {srv.puerto} está ocupado por un proceso que no responde y no es de este supervisor"
                srv.proximo_intento = time.time() + 60
                return
        self._iniciar(srv.nombre, srv.args, srv.env)

    def _iniciar(self, name: str, args: list, env: Optional[dict] = None) -> None:
        self.specs[name] = (args, env)
        srv = self.servicios.get(name)
        if srv is None:   # compatibilidad: llamado directamente sin definición de servicio
            srv = self.servicios[name] = Servicio(name, args, env)
        dir_logs().mkdir(parents=True, exist_ok=True)
        ruta = dir_logs() / f"{name}.log"
        if srv.log_f:   # cerrar antes de rotar (Windows no renombra archivos abiertos)
            try:
                srv.log_f.close()
            except Exception:
                pass
        _rotar(ruta)
        srv.log_f = open(ruta, "ab", buffering=0)
        srv.log_f.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} inicio de {name} =====\n".encode())
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        entorno = dict(env if env is not None else os.environ)
        entorno.setdefault("PYTHONIOENCODING", "utf-8")
        entorno.setdefault("PYTHONUNBUFFERED", "1")
        srv.proc = subprocess.Popen(args, cwd=str(WORKSPACE), env=entorno, stdout=srv.log_f, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, creationflags=flags)
        self.processes[name] = srv.proc
        srv.externo, srv.estado, srv.causa = False, "cargando", "iniciando"
        srv.iniciado = time.time()
        srv.fallas_sonda, srv.primera_falla = 0, 0.0

    def _esperar_preparacion(self) -> int:
        pendientes = {n: s for n, s in self.servicios.items() if s.estado == "cargando"}
        inicio = time.time()
        while pendientes:
            for n, s in list(pendientes.items()):
                if s.proc and s.proc.poll() is not None:
                    self._marcar_salida(s, s.proc.returncode)
                    pendientes.pop(n)
                    continue
                ok, det = s.preparado() if s.preparado else (s.proc is not None and s.proc.poll() is None, "proceso vivo")
                if ok:
                    s.estado, s.causa = "activo", det
                    _decir(f"[SKY] ✓ {n} preparado ({time.time() - s.iniciado:.1f} s): {det}")
                    pendientes.pop(n)
                elif time.time() - inicio > s.espera_preparacion:
                    s.estado, s.causa = "degradado", f"no estuvo listo en {s.espera_preparacion:.0f} s: {det}"
                    pendientes.pop(n)
            if pendientes:
                time.sleep(0.5)
        return sum(1 for s in self.servicios.values() if s.estado in ("activo", "externo"))

    # ---------------------------------------------------------- supervisión
    def _marcar_salida(self, s: Servicio, codigo) -> None:
        cola = _ultimas_lineas(s.nombre)
        if codigo == SALIDA_NO_CONFIGURADO:
            s.estado = "no_configurado"
            s.causa = "falta configuración o una dependencia" + (f": {cola}" if cola else "")
            s.proximo_intento = 0.0   # no se reintenta en bucle
        elif codigo == SALIDA_SIN_MICROFONO:
            s.estado, s.causa = "error", "no hay micrófono disponible; reintento en 5 minutos"
            s.proximo_intento = time.time() + 300
        elif s.nombre == "voice" and codigo == 42:
            # Otro Vosk ya captura el micrófono; conservarlo sin reinicios agresivos.
            s.estado, s.causa = "degradado", "otra instancia Vosk activa; reintento sin cerrar la existente"
            s.proximo_intento = time.time() + 30
        else:
            s.estado = "error"
            s.causa = f"terminó con código {codigo}" + (f": {cola}" if cola else "")
            self._programar_reinicio(s)
        s.proc = None
        _registrar_reinicio(s.nombre, s.causa[:120])
        _decir(f"[SKY] {s.nombre} se detuvo: {s.causa}")

    def _programar_reinicio(self, s: Servicio) -> None:
        ahora = time.time()
        s.reinicios = [t for t in s.reinicios if ahora - t < 3600]
        self.reinicios[s.nombre] = s.reinicios
        if len(s.reinicios) >= MAX_REINICIOS_HORA:
            s.proximo_intento = ahora + ESPERA_TRAS_LIMITE
            s.causa += f" — llegó al límite de {MAX_REINICIOS_HORA} reinicios por hora; reintento en 30 min"
            if s.nombre not in self.reported:
                self.reported.add(s.nombre)
                _decir(f"[AVISO] '{s.nombre}' falló demasiadas veces. Revisá: python iniciar_sky_autonomo.py --status")
        else:
            s.proximo_intento = ahora + min(120.0, 2.0 * (2 ** len(s.reinicios)))

    def revisar(self, ahora: Optional[float] = None) -> None:
        """Un ciclo de supervisión (no bloquea: los reinicios se programan, no se duermen)."""
        ahora = ahora or time.time()
        for s in self.servicios.values():
            if s.estado == "no_configurado":
                continue
            if s.proc is not None and s.proc.poll() is not None:
                self._marcar_salida(s, s.proc.returncode)
                continue
            if s.proc is None and not s.externo:
                if s.proximo_intento and ahora >= s.proximo_intento:
                    s.reinicios.append(ahora)
                    s.proximo_intento = 0.0
                    _decir(f"[SKY] Reiniciando '{s.nombre}' ({len(s.reinicios)}/{MAX_REINICIOS_HORA} esta hora)...")
                    self._iniciar(s.nombre, s.args, s.env)
                continue
            if not s.sonda or ahora - s.ultima_sonda < self.intervalo_sonda:
                continue
            s.ultima_sonda = ahora
            if s.estado == "cargando" and ahora - s.iniciado < s.espera_preparacion:
                ok, det = (s.preparado or s.sonda)()
                if ok:
                    s.estado, s.causa = "activo", det
                continue
            ok, det = s.sonda()
            if ok:
                if s.estado not in ("activo", "externo"):
                    _decir(f"[SKY] {s.nombre} se recuperó: {det}")
                s.estado = "externo" if s.externo else "activo"
                s.causa, s.fallas_sonda, s.primera_falla = det, 0, 0.0
                continue
            # La voz informa su identidad por PID. Si un segundo listener real
            # mantiene el micrófono y publica latidos recientes, el PID de este
            # subproceso no coincidirá. Eso es una discrepancia de propietarios,
            # NO prueba que el proceso esté colgado: nunca matar por ese motivo
            # a ciegas, ni reiniciar en bucle mientras el otro listener está sano.
            if s.nombre == "voice" and s.proc is not None and not s.externo:
                otro_pid = _pid_escucha_vivo()
                if otro_pid and otro_pid != s.proc.pid:
                    otro_ok, _ = sonda_voz(otro_pid)
                    if otro_ok:
                        s.estado = "degradado"
                        s.causa = (
                            f"escucha SKY activa en otro PID ({otro_pid}); "
                            f"el proceso supervisado ({s.proc.pid}) no informa estado propio"
                        )
                        s.fallas_sonda, s.primera_falla = 0, 0.0
                        continue
            s.fallas_sonda += 1
            s.primera_falla = s.primera_falla or ahora
            if s.externo:
                # El SKY adoptado dejó de responder: si liberó el puerto, arranca uno propio; si no, se informa.
                if (s.puerto and not is_port_in_use(s.puerto)) or (s.nombre == "voice" and not _pid_escucha_vivo()):
                    _decir(f"[SKY] {s.nombre} adoptado se detuvo; inicio uno propio.")
                    self._iniciar(s.nombre, s.args, s.env)
                else:
                    s.estado, s.causa = "degradado", f"el {s.nombre} adoptado no responde: {det}"
                continue
            if ahora - s.primera_falla >= s.colgado_tras:
                s.estado = "error"
                s.causa = f"colgado: {det} durante {int(ahora - s.primera_falla)} s con el proceso vivo"
                _decir(f"[SKY] {s.nombre} {s.causa}; lo reinicio.")
                self._terminar(s)
                s.proc = None
                _registrar_reinicio(s.nombre, "colgado")
                self._programar_reinicio(s)
            else:
                s.estado, s.causa = "degradado", f"no responde ({det}); espero antes de considerarlo colgado"

    def monitor(self):
        """Supervisa los procesos y maneja su cierre limpio."""
        try:
            while self.running:
                if _ruta_parar().exists():
                    _decir("[SKY] Pedido de cierre recibido (--stop).")
                    break
                self.revisar()
                self._guardar_estado()
                time.sleep(2.0)
        except KeyboardInterrupt:
            _decir("\n[SKY] Señal de interrupción recibida. Deteniendo servicios...")
        finally:
            self.stop_all()

    def _terminar(self, s: Servicio, espera: float = 8.0) -> None:
        proc = s.proc
        if proc is None or proc.poll() is not None:
            return
        try:
            if os.name == "nt":
                proc.send_signal(signal.CTRL_BREAK_EVENT)   # uvicorn y Python cierran ordenadamente
            else:
                proc.terminate()
            proc.wait(timeout=espera)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=3)
            except Exception:
                pass

    def _terminar_pid(self, pid: int) -> None:
        try:
            import psutil
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=8)
        except Exception:
            kill_process_by_pid(pid)

    def stop_all(self):
        """Detiene todos los subprocesos de manera ordenada (los adoptados no se tocan)."""
        self.running = False
        _decir("[SKY] Deteniendo procesos de SKY-IA...")
        orden = ["voice", "streamlit", "whatsapp", "social_hub", "openjarvis", "api", "agent"]
        for name in sorted(self.servicios, key=lambda n: orden.index(n) if n in orden else 0):
            s = self.servicios[name]
            if s.proc is not None and s.proc.poll() is None:
                self._terminar(s)
                _decir(f"[SKY] Servicio '{name}' detenido.")
            if s.log_f:
                try:
                    s.log_f.close()
                except Exception:
                    pass
            s.estado = "detenido" if not s.externo else s.estado
        for name, proc in self.processes.items():   # compatibilidad con procesos registrados sin servicio
            if name not in self.servicios and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=2.0)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        try:
            _ruta_estado().unlink()
        except OSError:
            pass
        try:
            _ruta_parar().unlink()
        except OSError:
            pass
        if self._candado:
            self._candado.liberar()
        _decir("[SKY] Todos los servicios fueron finalizados limpiamente.")

    def _guardar_estado(self) -> None:
        servicios = {}
        for n, s in self.servicios.items():
            reg = {"estado": s.estado, "causa": s.causa[:300], "reinicios": len(s.reinicios), "externo": s.externo,
                   "puerto": s.puerto, "firma": s.firma, "pasos": PASOS.get(n, "")}
            if s.proc is not None and s.proc.poll() is None:
                ident = _identidad(s.proc.pid)
                reg.update(pid=s.proc.pid, create_time=ident["create_time"] if ident else None)
            servicios[n] = reg
        try:
            from neural_core.sky_archivo_seguro import escribir_json
            escribir_json(_ruta_estado(), {"pid": os.getpid(), "inicio": time.time(), "servicios": servicios},
                          indent=2, privado=True)
        except Exception:
            pass


def _rotar(ruta: Path, max_bytes: int = 2_000_000, copias: int = 3) -> None:
    try:
        if not ruta.exists() or ruta.stat().st_size < max_bytes:
            return
        for i in range(copias - 1, 0, -1):
            viejo = ruta.with_name(f"{ruta.name}.{i}")
            if viejo.exists():
                os.replace(viejo, ruta.with_name(f"{ruta.name}.{i + 1}"))
        os.replace(ruta, ruta.with_name(f"{ruta.name}.1"))
    except OSError:
        pass


def detener_instancia(espera: float = 30.0) -> bool:
    """--stop: pide al supervisor en marcha que cierre todo limpio. No mata nada por puerto."""
    if not _supervisor_en_marcha():
        _decir("[SKY] No hay ninguna instancia del supervisor en marcha.")
        return True
    dir_estado().mkdir(parents=True, exist_ok=True)
    _ruta_parar().write_text(str(time.time()), encoding="utf-8")
    limite = time.time() + espera
    while time.time() < limite:
        if not _supervisor_en_marcha():
            _decir("[SKY] SKY se detuvo limpiamente.")
            return True
        time.sleep(0.5)
    _decir("[SKY] El supervisor no terminó a tiempo. Revisá local_data/logs/supervisor.log.")
    return False


def main():
    parser = argparse.ArgumentParser(description="Lanzador unificado autónomo de SKY-IA.")
    parser.add_argument("--with-ui", action="store_true", help="Inicia también el panel Streamlit (8501).")
    parser.add_argument("--no-voice", action="store_true", help="No arranca el bucle de micrófono.")
    parser.add_argument("--minimized", action="store_true", help="No abre el navegador (inicio con Windows).")
    parser.add_argument("--status", action="store_true", help="Muestra el estado de salud de los servicios.")
    parser.add_argument("--stop", action="store_true", help="Detiene limpiamente la instancia en marcha.")
    parser.add_argument("--kill-ports", action="store_true", help="Libera puertos de procesos propios huérfanos.")
    parser.add_argument("--install-startup", action="store_true", help="Configura inicio automático al iniciar sesión en Windows.")
    parser.add_argument("--uninstall-startup", action="store_true", help="Elimina el inicio automático de Windows.")
    args = parser.parse_args()

    if args.status:
        st = check_system_status()
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return

    if args.stop:
        sys.exit(0 if detener_instancia() else 1)

    if args.kill_ports:
        res = clean_port_conflicts([PORTS["api"], PORTS["agent"], PORTS["streamlit"]])
        print(f"[SKY] Resultado de liberación de puertos: {res}")
        return

    if args.install_startup:
        manage_windows_startup(install=True)
        return

    if args.uninstall_startup:
        manage_windows_startup(install=False)
        return

    supervisor = SkySupervisor(
        with_ui=args.with_ui,
        execute_safe=True,
        with_voice=not args.no_voice,
        open_browser=not args.minimized
    )

    # Registrar manejadores de señales
    def handle_signal(sig, frame):
        supervisor.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, handle_signal)

    if supervisor.start_all() is False:
        return
    supervisor.monitor()


if __name__ == "__main__":
    main()
