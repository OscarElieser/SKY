"""Bounded, best-effort HTTP metrics sink for SKY's existing telemetry stores.

Never block a user response on optional SQLite measurement writes. Bounded queue
prevents accumulating unbounded requests when a database is slow. Metrics may be
dropped if the queue is full; expose this through queue_status().
"""
from __future__ import annotations

import queue
import threading
import time

_MAX_PENDING = 256
_PENDING: queue.Queue[tuple[str, str, str, float, int]] = queue.Queue(maxsize=_MAX_PENDING)
_LOCK = threading.Lock()
_THREAD: threading.Thread | None = None
_DROPPED = 0


def _consume() -> None:
    while True:
        path, method, route, elapsed_ms, status = _PENDING.get()
        try:
            try:
                from .sky_telemetry import record
                record(path, elapsed_ms, status)
            except Exception:
                # Metrics never affect the primary business request.
                pass
            if path.startswith('/api/'):
                try:
                    from . import sky_metricas
                    label = route or sky_metricas.ruta_plantilla(path)
                    sky_metricas.registrar(
                        'api', f'{method} {label}', status < 500,
                        elapsed_ms, codigo=status,
                    )
                except Exception:
                    pass
        finally:
            _PENDING.task_done()


def enqueue(path: str, method: str, route: str, elapsed_ms: float, status: int) -> bool:
    """Accept an HTTP measurement without waiting on SQLite.

    Only paths, statuses and durations are retained; no messages or credentials.
    A false result means a measurement was dropped due to overload.
    """
    global _THREAD, _DROPPED
    try:
        if _THREAD is None or not _THREAD.is_alive():
            with _LOCK:
                if _THREAD is None or not _THREAD.is_alive():
                    _THREAD = threading.Thread(
                        target=_consume, name='sky-http-metrics', daemon=True,
                    )
                    _THREAD.start()
        _PENDING.put_nowait((str(path)[:300], str(method)[:12],
                            str(route)[:300], max(0.0, float(elapsed_ms)), int(status)))
        return True
    except queue.Full:
        with _LOCK:
            _DROPPED += 1
        return False


def queue_status() -> dict:
    """Read-only operational counters; no private request content."""
    with _LOCK:
        dropped = _DROPPED
    return {'queued': _PENDING.qsize(), 'unfinished': _PENDING.unfinished_tasks,
            'capacity': _MAX_PENDING, 'dropped': dropped}


def flush(timeout_seconds: float = 3.0) -> bool:
    """Best-effort bounded drain at graceful shutdown; never wait forever."""
    limit = time.monotonic() + max(0.0, float(timeout_seconds))
    while _PENDING.unfinished_tasks and time.monotonic() < limit:
        time.sleep(0.025)
    return _PENDING.unfinished_tasks == 0
