"""SKY v12.1 — Contactos y WhatsApp.

Contactos en ~/.neuralt/contactos.json (sólo en tu equipo):
    {"mamá": {"whatsapp": "+50588887777", "email": "mama@gmail.com"},
     "Pedro trabajo": {"whatsapp": "+50577776666"}}

"mandale un whatsapp a mamá que llego tarde" abre WhatsApp con el mensaje ya
escrito (wa.me); vos tocás Enviar. SKY no envía mensajes de WhatsApp por su
cuenta: WhatsApp no ofrece una API oficial para cuentas personales.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote

CONTACTOS_PATH = Path.home() / '.neuralt' / 'contactos.json'


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s).lower())
    return ' '.join(''.join(c for c in s if unicodedata.category(c) != 'Mn').split())


def contactos() -> dict:
    try:
        data = json.loads(CONTACTOS_PATH.read_text(encoding='utf-8'))
        return {str(k)[:60]: v for k, v in data.items() if isinstance(v, dict)} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def buscar(nombre: str) -> dict | None:
    q = _norm(nombre)
    q = re.sub(r'^(?:a\s+|mi\s+|el\s+|la\s+)', '', q)
    todos = contactos()
    for k, v in todos.items():
        if _norm(k) == q:
            return {'nombre': k, **v}
    for k, v in todos.items():
        if q and (q in _norm(k) or _norm(k) in q):
            return {'nombre': k, **v}
    return None


def numero_valido(numero: str) -> str:
    digitos = re.sub(r'[^\d]', '', str(numero or ''))
    if not 8 <= len(digitos) <= 15:
        raise ValueError('Número de WhatsApp inválido: usá el formato internacional, ej. +50588887777.')
    return digitos


def enlace_whatsapp(numero: str, mensaje: str) -> str:
    mensaje = str(mensaje or '').strip()[:1500]
    return f'https://wa.me/{numero_valido(numero)}' + (f'?text={quote(mensaje)}' if mensaje else '')


def interpretar(texto: str) -> dict | None:
    t = _norm(texto).strip(' .!?¿¡')
    t = re.sub(r'^(?:sky|oye sky|hey sky)[\s,]+', '', t)
    m = re.match(r'^(?:manda|mandale|envia|enviale|escribe|escribele|escribile)\s+(?:un\s+)?(?:whatsapp|wasap|whats|mensaje\s+(?:de|por)\s+whatsapp)'
                 r'\s+a\s+(.+?)\s+(?:diciendo|que diga|que|con el texto)\s+(.+)$', t) \
        or re.match(r'^(?:manda|mandale|envia|enviale)\s+(?:un\s+)?mensaje\s+(?:por|de)\s+whatsapp\s+a\s+(.+?)\s+(?:diciendo|que diga|que)\s+(.+)$', t)
    if not m:
        return None
    contacto = buscar(m.group(1))
    original = texto.strip()
    mensaje = m.group(2)
    o = _norm(original)
    i = o.rfind(mensaje)
    if i >= 0 and len(o) == len(original):
        mensaje = original[i:i + len(mensaje)]
    if not contacto or not contacto.get('whatsapp'):
        return {'tipo': 'aviso', 'description': f'No tengo el WhatsApp de «{m.group(1)}». Agregalo en ~/.neuralt/contactos.json.'}
    try:
        url = enlace_whatsapp(contacto['whatsapp'], mensaje)
    except ValueError as exc:
        return {'tipo': 'aviso', 'description': str(exc)}
    return {'tipo': 'accion', 'propuesta': {'action': 'open_url', 'params': {'url': url},
            'description': f"WhatsApp a {contacto['nombre']}: «{mensaje[:80]}» (vos tocás Enviar)"}}
