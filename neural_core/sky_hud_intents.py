"""Pure, bounded recognition for owner-requested HUD-only window actions.

This module never executes a device action. Only one explicitly allowlisted UI
intent is emitted; all other words fall through to SKY's existing interpreter.
"""
from __future__ import annotations

import re
import unicodedata


def _normalized(text: str) -> str:
    value = unicodedata.normalize('NFD', str(text or '')[:250])
    value = ''.join(c for c in value if not unicodedata.combining(c))
    value = value.lower().strip()
    value = re.sub(r'^[\s¿¡.,:;!?]+|[\s¿¡.,:;!?]+$', '', value)
    value = re.sub(r'\s+', ' ', value)
    return value


def panel_chat(text: str) -> dict | None:
    """Translate direct requests to open SKY's conversation pane.

    Greeting, unrelated dialogue, or commands to close/erase/send are ignored.
    """
    value = _normalized(text)
    value = re.sub(r'^(?:(?:oye|hey|ok|okay)\s+)?(?:sky|esquai|escai)[\s,.:;-]+', '', value)
    match = re.fullmatch(
        r'(?:abre|abri|abrir|abrime|abreme|muestra|mostra|mostrar|'
        r'mostrame|muestrame|ensena|ensen[aá]me)\s+'
        r'(?:(?:el|la|un|una)\s+)?'
        r'(?:(?:panel|ventana|cuadro)\s+(?:(?:de|del)\s+)?)?'
        r'(?:chat|conversacion|texto)'
        r'(?:\s+de\s+sky)?'
        r'(?:\s+por favor)?',
        value,
    )
    # "Abrí el panel de SKY" is explicitly scoped to the HUD, not a web search.
    if not match and not re.fullmatch(
        r'(?:abre|abri|abrir|muestra|mostra|mostrar)\s+'
        r'(?:(?:el|la)\s+)?panel\s+de\s+sky(?:\s+por favor)?',
        value,
    ):
        return None
    return {
        'action': 'holographic_window',
        'params': {'subaction': 'open_chat'},
        'description': 'Abrir el panel de conversación de SKY',
    }
