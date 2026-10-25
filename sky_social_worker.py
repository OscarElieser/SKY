"""Worker de publicaciones YA APROBADAS. SKY mantiene el control del proceso."""
from __future__ import annotations
import os
import signal
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

_RUNNING = True


def stop(*_args):
    global _RUNNING
    _RUNNING = False


def main():
    if os.getenv("SKY_SOCIAL_WORKER_ENABLED", "0") != "1":
        print("[SKY Social] Desactivado; no se ejecuta ninguna publicación.")
        return
    from neural_core.sky_social_hub import worker_tick
    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)
    print("[SKY Social] Servicio local: solo publicaciones previamente aprobadas.")
    while _RUNNING:
        try:
            worker_tick()
        except Exception:
            # No filtrar tokens ni contenido a la consola.
            print("[SKY Social] Error interno; revisar diagnóstico y el estado de la cola.")
        # Interrumpible con señales; el supervisor gestiona el proceso.
        for _ in range(60):
            if not _RUNNING:
                break
            time.sleep(1)


if __name__ == "__main__":
    main()
