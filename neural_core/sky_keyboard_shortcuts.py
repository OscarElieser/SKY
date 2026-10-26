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
    r"aprieta|apret[aá]|teclea|env[ií]a|pon|pon[eé]|ejecuta|ejecut[aá]|usa)"
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


def enviar_ctrl_f4_word() -> dict:
    """Dispatch only when the foreground window belongs to WINWORD.EXE.

    Returns SENT, never VERIFIED: Word may show a save confirmation instead of
    closing the document. ctypes imports deliberately happen only on Windows.
    """
    import os
    if os.name != "nt":
        raise RuntimeError("Los atajos de escritorio de SKY requieren Windows.")
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        raise RuntimeError("No hay una ventana activa. Enfocá Word y volvé a confirmar.")
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        raise RuntimeError("No pude identificar la ventana activa.")
    try:
        import psutil
        executable = psutil.Process(pid.value).name().lower()
    except (ImportError, OSError, Exception):
        raise RuntimeError("No pude verificar que Word sea la ventana activa.")
    if executable != "winword.exe":
        raise RuntimeError("No envié Ctrl+F4: la ventana activa no es Microsoft Word.")

    KEYEVENTF_KEYUP = 0x0002
    VK_CTRL = 0x11
    VK_F4 = 0x73
    keybd = user32.keybd_event
    keybd.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, wintypes.DWORD, ctypes.c_size_t]
    keybd.restype = None
    # Never dispatch if Word no longer owns foreground immediately beforehand.
    if hwnd != user32.GetForegroundWindow():
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
        "message": ("Envié Ctrl+F4 a Word. No puedo asegurar que el documento "
                    "se haya cerrado; Word podría pedir guardar cambios."),
    }
