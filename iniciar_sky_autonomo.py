"""Lanzador unificado y supervisor autónomo de SKY-IA para Windows.

Desacopla el núcleo de ejecución, el agente Windows (8766) y la voz continua
de la interfaz Streamlit (8501), evitando conflictos de puertos y procesos huérfanos.

Uso:
    python iniciar_sky_autonomo.py                 # SKY completo: Agente + API + Voz + interfaz HUD
    python iniciar_sky_autonomo.py --minimized     # Igual, sin abrir el navegador (inicio con Windows)
    python iniciar_sky_autonomo.py --with-ui       # Autónomo + Panel Streamlit opcional
    python iniciar_sky_autonomo.py --status        # Diagnóstico de puertos y servicios
    python iniciar_sky_autonomo.py --kill-ports    # Liberar puertos bloqueados
    python iniciar_sky_autonomo.py --install-startup   # Configurar inicio con Windows (sin admin)
    python iniciar_sky_autonomo.py --uninstall-startup # Desactivar inicio con Windows
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

WORKSPACE = Path(__file__).resolve().parent
VENV_PYTHON = WORKSPACE / ".venv" / "Scripts" / "python.exe"
PYTHON_EXE = str(VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable))

PORTS = {
    "api": 8765,
    "agent": 8766,
    "streamlit": 8501
}


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
    """Identifica el PID que ocupa un puerto en Windows usando netstat."""
    if os.name != "nt":
        return None
    try:
        out = subprocess.check_output(['netstat', '-ano', '-p', 'tcp'], text=True, stderr=subprocess.DEVNULL)
        out = "\n".join(l for l in out.splitlines() if f":{int(port)} " in l + " ")
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and "LISTENING" in parts:
                return int(parts[-1])
            elif len(parts) >= 4 and parts[1].endswith(f":{port}"):
                return int(parts[-1])
    except Exception:
        pass
    return None


def kill_process_by_pid(pid: int) -> bool:
    """Finaliza un proceso de manera forzada y limpia en Windows."""
    if not pid or pid <= 4:
        return False
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(int(pid))], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def clean_port_conflicts(ports: List[int]) -> Dict[int, bool]:
    """Libera los puertos ocupados por instancias previas de SKY (nunca por otros programas)."""
    results = {}
    for p in ports:
        if is_port_in_use(p):
            if not es_servicio_sky(p):
                print(f"[SKY] El puerto {p} lo usa otro programa; no se toca.")
                results[p] = False
                continue
            pid = get_pid_using_port(p)
            if pid:
                print(f"[SKY] Liberando puerto {p} (PID ocupante: {pid})...")
                results[p] = kill_process_by_pid(pid)
            else:
                results[p] = False
        else:
            results[p] = True
    return results


def check_system_status() -> Dict[str, dict]:
    """Diagnóstico detallado de los componentes de SKY-IA."""
    status = {}

    # 1. Agente Windows (8766)
    agent_port = PORTS["agent"]
    agent_up = is_port_in_use(agent_port)
    agent_info = {"port": agent_port, "listening": agent_up, "status": "offline"}
    if agent_up:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{agent_port}/status")
            try:
                from neural_core.sky_voice_actions import local_agent_credentials
                _, token = local_agent_credentials()
                if token:
                    req.add_header("Authorization", f"Bearer {token}")
            except Exception:
                pass
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                agent_info["status"] = "online"
                agent_info["device"] = data.get("device", "Windows")
                agent_info["capabilities"] = data.get("capabilities", [])
        except Exception as e:
            agent_info["status"] = f"error: {e}"
    status["agent"] = agent_info

    # 2. Metaverso / API (8765)
    api_port = PORTS["api"]
    api_up = is_port_in_use(api_port)
    api_info = {"port": api_port, "listening": api_up, "status": "offline"}
    if api_up:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{api_port}/api/health", timeout=2) as resp:
                api_info["status"] = "online" if resp.status == 200 else f"HTTP {resp.status}"
        except Exception:
            api_info["status"] = "online (sin endpoint /sky)"
    status["api"] = api_info

    # 3. Streamlit UI (8501)
    st_port = PORTS["streamlit"]
    st_up = is_port_in_use(st_port)
    status["streamlit"] = {"port": st_port, "listening": st_up, "status": "online" if st_up else "offline"}

    # 4. Estado de Coordinador de Voz
    voice_state_file = WORKSPACE / "local_data" / "voice_coordinator_state.json"
    voice_info = {"configured": False, "mode": "desconocido", "active": False}
    if voice_state_file.exists():
        try:
            v_data = json.loads(voice_state_file.read_text(encoding="utf-8"))
            voice_info["configured"] = True
            voice_info["mode"] = v_data.get("active_mode", "MODO_A_NATURAL")
            voice_info["state"] = v_data.get("current_state", "ESPERANDO_ACTIVACION")
            voice_info["active"] = v_data.get("is_session_active", False)
        except Exception:
            pass
    status["voice"] = voice_info

    return status


def manage_windows_startup(install: bool = True) -> bool:
    """Configura o desactiva el inicio automático de SKY al iniciar sesión en Windows (sin admin)."""
    if os.name != "nt":
        print("[SKY] El inicio automático solo está disponible en Windows.")
        return False

    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_bat = startup_dir / "SKY_IA_Autonomo.bat"

    if install:
        launcher_bat = WORKSPACE / "SKY_INICIAR.bat"
        content = f'@echo off\r\ncd /d "{WORKSPACE}"\r\nstart "" "{PYTHON_EXE}" iniciar_sky_autonomo.py --minimized\r\n'
        try:
            startup_dir.mkdir(parents=True, exist_ok=True)
            shortcut_bat.write_text(content, encoding="ascii")
            print(f"[SKY] Inicio automático configurado con éxito en:")
            print(f"      {shortcut_bat}")
            return True
        except Exception as e:
            print(f"[SKY] Error al configurar inicio automático: {e}")
            return False
    else:
        try:
            if shortcut_bat.exists():
                shortcut_bat.unlink()
                print("[SKY] Inicio automático desactivado con éxito.")
            else:
                print("[SKY] El inicio automático no estaba configurado.")
            return True
        except Exception as e:
            print(f"[SKY] Error al eliminar inicio automático: {e}")
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
        sky_metricas.registrar("servicio", "reinicio", False, detalle=f"{name} terminó con código {codigo}")
    except Exception:
        pass


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
        self.running = False

    def start_all(self):
        print("==============================================================")
        print("               SKY IA — INICIO AUTÓNOMO DE ESCRITORIO          ")
        print("==============================================================")
        print(f"[SKY] Intérprete Python: {PYTHON_EXE}")
        print(f"[SKY] Directorio Base:   {WORKSPACE}")

        # 1. Comprobar y resolver colisiones en puertos
        needed_ports = [PORTS["api"], PORTS["agent"]]
        if self.with_ui:
            needed_ports.append(PORTS["streamlit"])

        for p in needed_ports:
            if is_port_in_use(p):
                if not es_servicio_sky(p):
                    print(f"[AVISO] El puerto {p} está ocupado por otro programa (no es SKY). No se cierra.")
                    if p == PORTS["api"]:
                        sys.exit("[SKY] Liberá el puerto 8765 o cerrá ese programa y volvé a intentar.")
                    continue
                pid = get_pid_using_port(p)
                print(f"[SKY] Reiniciando instancia previa de SKY en el puerto {p} (PID {pid})...")
                if pid:
                    kill_process_by_pid(pid)
                    time.sleep(0.5)

        # 2. Iniciar Agente de Dispositivo Windows (Puerto 8766)
        print(f"[SKY] Iniciando Agente de Dispositivo en 127.0.0.1:{PORTS['agent']}...")
        agent_env = os.environ.copy()
        agent_env["SKY_DEVICE_PORT"] = str(PORTS["agent"])
        self._iniciar("agent", [PYTHON_EXE, str(WORKSPACE / "agente_dispositivo.py")], agent_env)

        # 3. Iniciar API del Metaverso / Servicios (Puerto 8765)
        print(f"[SKY] Iniciando API y Metaverso en 127.0.0.1:{PORTS['api']}...")
        self._iniciar("api", [PYTHON_EXE, "-m", "uvicorn", "metaverse.api:app", "--host", "127.0.0.1", "--port", str(PORTS["api"])])

        # 3a. Motor cognitivo adicional integrado en SKY (opt-in).
        # Se supervisa como servicio interno; nunca reemplaza el núcleo ni
        # ocupa un puerto ajeno, y tampoco instala paquetes al iniciar.
        try:
            from neural_core.sky_openjarvis_boot import launch_spec
            spec = launch_spec()
            if spec:
                from neural_core.sky_openjarvis import _base_url
                jarvis_port = int(_base_url().rsplit(":", 1)[1])
                if is_port_in_use(jarvis_port):
                    print(f"[SKY] Puerto OpenJarvis {jarvis_port} ocupado; no se cierra ni sustituye el proceso.")
                else:
                    print(f"[SKY] Iniciando motor consultivo interno en 127.0.0.1:{jarvis_port}...")
                    self._iniciar("openjarvis", spec[0])
        except (ValueError, FileNotFoundError, OSError) as exc:
            print(f"[SKY] OpenJarvis opcional no iniciado: {exc}")

        # 3b. Puente de WhatsApp (v12.3): sólo si está configurado en .env
        if _whatsapp_configurado():
            print("[SKY] Iniciando puente de WhatsApp en 127.0.0.1:8770 (publicalo con: tailscale funnel --bg 8770)...")
            self._iniciar("whatsapp", [PYTHON_EXE, str(WORKSPACE / "sky_whatsapp_puente.py")])

        # Social Hub de SKY: solo empieza si el propietario lo habilitó.
        # El servicio nunca crea, aprueba ni publica borradores sin aprobación.
        try:
            from dotenv import load_dotenv
            load_dotenv(WORKSPACE / ".env", override=False)
            if os.getenv("SKY_SOCIAL_WORKER_ENABLED", "0") == "1":
                print("[SKY] Iniciando programador de publicaciones previamente aprobadas...")
                self._iniciar("social_hub", [PYTHON_EXE, str(WORKSPACE / "sky_social_worker.py")])
        except (ImportError, OSError) as exc:
            print(f"[SKY] Programador social no iniciado: {type(exc).__name__}")

        # 4. Iniciar Escucha de Voz Continua (sky_manos_libres.py)
        model_dir = WORKSPACE / "modelos" / "vosk-model-es"
        if self.with_voice and not model_dir.is_dir():
            print("[SKY] Voz manos libres en pausa: falta el modelo Vosk en modelos/vosk-model-es.")
            print("      La interfaz HUD igual escucha con el micrófono del navegador (botón del núcleo).")
        if self.with_voice and model_dir.is_dir():
            voice_args = [PYTHON_EXE, str(WORKSPACE / "sky_manos_libres.py"), "--model", str(model_dir)]
            if self.execute_safe:
                voice_args.append("--execute-safe")

            print("[SKY] Iniciando escucha de voz continua en segundo plano...")
            self._iniciar("voice", voice_args)

        # 5. Iniciar Streamlit opcional (Puerto 8501)
        if self.with_ui:
            print(f"[SKY] Iniciando interfaz visual Streamlit en http://127.0.0.1:{PORTS['streamlit']}...")
            self._iniciar("streamlit", [PYTHON_EXE, "-m", "streamlit", "run", "app.py", "--server.port", str(PORTS["streamlit"]), "--server.address", "127.0.0.1"])

        self.running = True
        if self.open_browser:
            for _ in range(40):
                if is_port_in_use(PORTS["api"]):
                    break
                time.sleep(0.25)
            try:
                import webbrowser
                webbrowser.open(f"http://127.0.0.1:{PORTS['api']}/")
            except Exception:
                pass
        print(f"\n[SKY] Interfaz HUD: http://127.0.0.1:{PORTS['api']}/")
        print("[SKY] Todos los servicios requeridos están activos y supervisados.")
        print("[SKY] Podés hablarle a SKY (\"SKY, abrí Word\", \"SKY, reproducí Queen\")")
        print("[SKY] o interactuar mediante la API/Agente sin requerir Streamlit.")
        print("[SKY] Presioná Ctrl+C para finalizar de forma segura.\n")

    def _iniciar(self, name: str, args: list, env: Optional[dict] = None) -> None:
        self.specs[name] = (args, env)
        self.processes[name] = subprocess.Popen(args, cwd=str(WORKSPACE), env=env)

    def monitor(self):
        """Supervisa los procesos y maneja su cierre limpio."""
        try:
            while self.running:
                for name, proc in list(self.processes.items()):
                    ret = proc.poll()
                    if ret is None:
                        continue
                    # v12.3: reinicio controlado (máx. 5 por hora y proceso) para que SKY siga disponible.
                    ahora = time.time()
                    recientes = [t for t in self.reinicios.get(name, []) if ahora - t < 3600]
                    if len(recientes) < 5 and name in self.specs:
                        print(f"[SKY] '{name}' se detuvo (código {ret}); reiniciando ({len(recientes) + 1}/5 esta hora)...")
                        _registrar_reinicio(name, ret)
                        time.sleep(3)
                        self.reinicios[name] = recientes + [ahora]
                        args, env = self.specs[name]
                        self._iniciar(name, args, env)
                    elif name not in self.reported:
                        self.reported.add(name)
                        print(f"[AVISO] El proceso '{name}' falló demasiadas veces; queda detenido. Revisá: python sky_diagnostico.py")
                time.sleep(2.0)
        except KeyboardInterrupt:
            print("\n[SKY] Señal de interrupción recibida. Deteniendo servicios...")
        finally:
            self.stop_all()

    def stop_all(self):
        """Detiene todos los subprocesos de manera ordenada."""
        self.running = False
        print("[SKY] Deteniendo procesos de SKY-IA...")
        for name, proc in self.processes.items():
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=2.0)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                print(f"[SKY] Servicio '{name}' detenido.")
        print("[SKY] Todos los servicios fueron finalizados limpiamente.")


def main():
    parser = argparse.ArgumentParser(description="Lanzador unificado autónomo de SKY-IA.")
    parser.add_argument("--with-ui", action="store_true", help="Inicia también el panel Streamlit (8501).")
    parser.add_argument("--no-voice", action="store_true", help="No arranca el bucle de micrófono.")
    parser.add_argument("--minimized", action="store_true", help="No abre el navegador (inicio con Windows).")
    parser.add_argument("--status", action="store_true", help="Muestra el estado de salud de los servicios.")
    parser.add_argument("--kill-ports", action="store_true", help="Libera los puertos 8765, 8766 y 8501.")
    parser.add_argument("--install-startup", action="store_true", help="Configura inicio automático al iniciar sesión en Windows.")
    parser.add_argument("--uninstall-startup", action="store_true", help="Elimina el inicio automático de Windows.")
    args = parser.parse_args()

    if args.status:
        st = check_system_status()
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return

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

    supervisor.start_all()
    supervisor.monitor()


if __name__ == "__main__":
    main()
