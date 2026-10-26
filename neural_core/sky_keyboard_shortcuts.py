"""Allowlisted keyboard shortcuts for the owner's Windows desktop.

Never let an LLM synthesize arbitrary key sequences. Ctrl+F4 closes the
active document/tab; Word must be foreground and the owner must approve.
The agent is authoritative on permission, target, emergency stop and dispatch.
"""
from __future__ import annotations

import re
import unicodedata

KEY = re.compile(r"(?<!\w)(?:ctrl|control)\s*\+\s*f\s*4(?!\w)", re.I)
IMPERATIVE = re.compile(
    r"^\s*(?:(?:oye|hey|sky)[\s,:.-]+)?"
    r"(?:haz\s+(?:el\s+)?intento\s+de\s+(?:poner|presionar|pulsar)|"
    r"(?:intenta|prueba|prob[aá])\s+(?:poner|presionar|pulsar|con)|"
    r"presiona|presion[aá]|pulsa|puls[aá]|"
    r"aprieta|apret[aá]|teclea|env[ií][aá]|pon|pon[eé]|ejecuta|ejecut[aá]|usa)"
    r"(?:\s+(?:la\s+combinaci[oó]n\s+de\s+teclas?|las?\s+teclas?|"
    r"el\s+atajo|la\s+combinaci[oó]n|el\s+comando))?\s*",
    re.I,
)


def solicitud(texto: str) -> dict | None:
    """Parse only an intentional owner request, never an explanation of keys."""
    if not isinstance(texto, str) or len(texto) > 300:
        return None
    t = unicodedata.normalize("NFKC", texto).strip()
    if not KEY.search(t):
        return None
    if not IMPERATIVE.match(t):
        return None
    # Do not execute extra key sequences that accompany the single allowlisted
    # command ("Ctrl+F4 y Alt+F4" must not mean just Ctrl+F4).
    remainder = KEY.sub("", t)
    if re.search(r"(?<!\w)(?:alt|shift|ctrl|control|win)\s*\+\s*\w+", remainder, re.I):
        return {
            "tipo": "respuesta",
            "mensaje": "No ejecuto combinaciones múltiples o no autorizadas. Solicitá una por vez.",
            "proveedor": "sky-teclado-seguro",
        }
    return {
        "tipo": "accion",
        "mensaje": ("Enviar Ctrl+F4 únicamente a Microsoft Word en primer plano, "
                    "con confirmación expresa."),
        "proveedor": "sky-teclado-seguro",
        "propuesta": {
            "action": "keyboard_shortcut",
            "params": {"shortcut": "ctrl+f4", "expected_app": "winword.exe"},
            "description": "Ctrl+F4 en Word (podría cerrar el documento activo)",
        },
    }


def propuesta(texto: str) -> dict | None:
    result = solicitud(texto)
    return result.get("propuesta") if result else None


def seleccionar_ventana_word(candidatas: list[int]) -> int:
    """Fail closed if there is no unambiguous Word document window."""
    if len(candidatas) != 1:
        raise RuntimeError(
            "Necesito exactamente una ventana principal de Word abierta "
            "para aplicar Ctrl+F4; no cerré ningún documento."
        )
    return candidatas[0]


def enviar_ctrl_f4_word() -> dict:
    """Focus the *only* visible WINWORD.EXE window and send one Ctrl+F4.

    The HUD's Confirm button naturally leaves Chrome in the foreground.
    We therefore select a unique, verified Word window instead of assuming
    the active browser belongs to Word. Failure to focus cancels the action.
    SENT never means the document was closed or saved.
    """
    import os
    if os.name != "nt":
        raise RuntimeError("Los atajos de escritorio de SKY requieren Windows.")
    import ctypes
    from ctypes import wintypes
    import time
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError("Para controlar ventanas necesitás psutil instalado.") from exc

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd_t = wintypes.HWND
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, hwnd_t, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [hwnd_t]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindow.argtypes = [hwnd_t, wintypes.UINT]
    user32.GetWindow.restype = hwnd_t
    user32.GetWindowTextLengthW.argtypes = [hwnd_t]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [
        hwnd_t, ctypes.POINTER(wintypes.DWORD)
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetForegroundWindow.restype = hwnd_t
    user32.ShowWindow.argtypes = [hwnd_t, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [hwnd_t]
    user32.SetForegroundWindow.restype = wintypes.BOOL

    windows = []

    @callback_type
    def enum_window(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindow(hwnd, 4):  # GW_OWNER; exclude owned dialogs
            return True
        if user32.GetWindowTextLengthW(hwnd) <= 0:
            return True
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return True
        try:
            if psutil.Process(pid.value).name().lower() == "winword.exe":
                windows.append(int(hwnd))
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass
        return True

    if not user32.EnumWindows(enum_window, 0):
        raise RuntimeError("No pude enumerar las ventanas de Word.")
    target = seleccionar_ventana_word(list(dict.fromkeys(windows)))
    # The user confirmed in the HUD; restore and focus Word before sending.
    user32.ShowWindow(target, 9)  # SW_RESTORE
    user32.SetForegroundWindow(target)
    for _ in range(3):
        if user32.GetForegroundWindow() == target:
            break
        time.sleep(0.12)
    if user32.GetForegroundWindow() != target:
        raise RuntimeError(
            "Windows no permitió enfocar Word. No envié Ctrl+F4. "
            "Activá Word manualmente y cerrá el documento desde allí."
        )

    KEYEVENTF_KEYUP = 0x0002
    VK_CTRL = 0x11
    VK_F4 = 0x73
    keybd = user32.keybd_event
    keybd.argtypes = [
        ctypes.c_ubyte, ctypes.c_ubyte, wintypes.DWORD, ctypes.c_size_t
    ]
    keybd.restype = None
    if user32.GetForegroundWindow() != target:
        raise RuntimeError("La ventana activa cambió. Atajo cancelado.")
    try:
        keybd(VK_CTRL, 0, 0, 0)
        keybd(VK_F4, 0, 0, 0)
    finally:
        keybd(VK_F4, 0, KEYEVENTF_KEYUP, 0)
        keybd(VK_CTRL, 0, KEYEVENTF_KEYUP, 0)
    return {
        "ok": True,
        "status": "SENT",
        "message": (
            "Envié Ctrl+F4 a la única ventana de Word. No puedo asegurar "
            "que el documento se haya cerrado: Word podría solicitar guardar."
        ),
    }
