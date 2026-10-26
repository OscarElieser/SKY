"""Single-process ownership of the SKY Vosk microphone listener.

Uses an OS-owned named mutex on Windows and a nonblocking advisory lock on
POSIX.  The handle remains held until the listener exits; a crashed process
releases it automatically.  Does not touch API, agent, or other SKY services.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import os

WINDOWS_MUTEX = "Local\\SKY_VOSK_MICROPHONE_LISTENER_V1"


@contextmanager
def single_voice_instance() -> Iterator[bool]:
    """Yield True if this process exclusively owns SKY's Vosk microphone.

    If another Vosk listener already owns the lock, yield False immediately.
    This does not prevent unrelated applications from using the microphone.
    """
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        create_mutex.restype = ctypes.c_void_p
        release_mutex = kernel32.ReleaseMutex
        release_mutex.argtypes = (ctypes.c_void_p,)
        release_mutex.restype = ctypes.c_bool
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (ctypes.c_void_p,)
        close_handle.restype = ctypes.c_bool

        handle = create_mutex(None, True, WINDOWS_MUTEX)
        if not handle:
            raise OSError(ctypes.get_last_error(), "No se pudo bloquear el micrófono de SKY")
        already_owned = ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS
        if already_owned:
            close_handle(handle)
            yield False
            return
        try:
            yield True
        finally:
            release_mutex(handle)
            close_handle(handle)
    else:
        import fcntl

        path = Path.home() / ".neuralt" / "sky_voice_listener.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
