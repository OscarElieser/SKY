"""SKY v12.1 — Correo: leer no leídos y enviar/responder SIEMPRE con tu confirmación.

Configuración (.env), con una CONTRASEÑA DE APLICACIÓN (no tu contraseña real):
    SKY_MAIL_USER=tu_correo@gmail.com
    SKY_MAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx      # o SKY_MAIL_APP_PASSWORD_FILE=ruta
    # Opcional (se deducen para Gmail, Outlook/Hotmail y Yahoo):
    SKY_MAIL_IMAP=imap.gmail.com   SKY_MAIL_SMTP=smtp.gmail.com

Gmail: activá la verificación en dos pasos y creá la contraseña en
myaccount.google.com/apppasswords. La lectura usa BODY.PEEK: no marca nada como leído.
Un correo enviado no se puede deshacer, por eso enviar siempre pide confirmación.
"""
from __future__ import annotations

import email
import email.header
import email.utils
import imaplib
import os
import re
import smtplib
import ssl
import unicodedata
from email.message import EmailMessage
from pathlib import Path

SERVIDORES = {
    'gmail.com': ('imap.gmail.com', 'smtp.gmail.com'),
    'googlemail.com': ('imap.gmail.com', 'smtp.gmail.com'),
    'outlook.com': ('outlook.office365.com', 'smtp.office365.com'),
    'hotmail.com': ('outlook.office365.com', 'smtp.office365.com'),
    'live.com': ('outlook.office365.com', 'smtp.office365.com'),
    'yahoo.com': ('imap.mail.yahoo.com', 'smtp.mail.yahoo.com'),
}
_EMAIL = re.compile(r'^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$')
_ULTIMOS: list[dict] = []


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s).lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def _clave() -> str:
    clave = os.getenv('SKY_MAIL_APP_PASSWORD', '').strip()
    archivo = os.getenv('SKY_MAIL_APP_PASSWORD_FILE', '').strip()
    if not clave and archivo:
        try:
            clave = Path(archivo).expanduser().read_text(encoding='utf-8').strip()
        except OSError:
            clave = ''
    return clave


def usuario() -> str:
    return os.getenv('SKY_MAIL_USER', '').strip()


def configurado() -> bool:
    return bool(_EMAIL.match(usuario()) and len(_clave()) >= 8)


def servidores() -> tuple[str, str]:
    dominio = usuario().rsplit('@', 1)[-1].lower()
    imap_d, smtp_d = SERVIDORES.get(dominio, (f'imap.{dominio}', f'smtp.{dominio}'))
    return os.getenv('SKY_MAIL_IMAP', imap_d).strip(), os.getenv('SKY_MAIL_SMTP', smtp_d).strip()


def _decodificar(valor: str) -> str:
    partes = []
    for texto, cod in email.header.decode_header(valor or ''):
        partes.append(texto.decode(cod or 'utf-8', 'replace') if isinstance(texto, bytes) else texto)
    return ' '.join(''.join(partes).split())


def _texto_plano(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for parte in msg.walk():
            if parte.get_content_type() == 'text/plain' and 'attachment' not in str(parte.get('Content-Disposition', '')):
                carga = parte.get_payload(decode=True) or b''
                return carga.decode(parte.get_content_charset() or 'utf-8', 'replace')
        return ''
    carga = msg.get_payload(decode=True) or b''
    texto = carga.decode(msg.get_content_charset() or 'utf-8', 'replace')
    return re.sub(r'<[^>]+>', ' ', texto) if msg.get_content_type() == 'text/html' else texto


def no_leidos(maximo: int = 8) -> list[dict]:
    """Últimos correos no leídos de la bandeja de entrada (sin marcarlos como leídos)."""
    if not configurado():
        raise RuntimeError('Correo no configurado (SKY_MAIL_USER y SKY_MAIL_APP_PASSWORD en .env).')
    imap_host, _ = servidores()
    salida = []
    try:
        with imaplib.IMAP4_SSL(imap_host, 993, ssl_context=ssl.create_default_context(), timeout=15) as m:
            m.login(usuario(), _clave())
            m.select('INBOX', readonly=True)
            estado, datos = m.uid('search', None, 'UNSEEN')
            uids = (datos[0] or b'').split()[-max(1, min(maximo, 20)):]
            for uid in reversed(uids):
                estado, partes = m.uid('fetch', uid, '(BODY.PEEK[HEADER] BODY.PEEK[TEXT]<0.4000>)')
                cab, cuerpo = b'', b''
                for p in partes:
                    if isinstance(p, tuple):
                        if b'HEADER' in p[0]:
                            cab = p[1]
                        else:
                            cuerpo = p[1]
                msg = email.message_from_bytes(cab + b'\r\n' + cuerpo)
                nombre, direccion = email.utils.parseaddr(_decodificar(msg.get('From', '')))
                salida.append({'uid': uid.decode(), 'de': nombre or direccion, 'direccion': direccion,
                               'asunto': _decodificar(msg.get('Subject', '(sin asunto)'))[:200],
                               'fecha': msg.get('Date', '')[:40], 'message_id': msg.get('Message-ID', '')[:300],
                               'resumen': ' '.join(_texto_plano(msg).split())[:280]})
    except imaplib.IMAP4.error as exc:
        raise RuntimeError('El servidor de correo rechazó el acceso. Revisá la contraseña de aplicación.') from exc
    except (OSError, ssl.SSLError) as exc:
        raise RuntimeError('No se pudo conectar con el servidor de correo.') from exc
    _ULTIMOS[:] = salida
    return salida


def resumen_para_voz(maximo: int = 5) -> str:
    correos = no_leidos(maximo)
    if not correos:
        return 'No tenés correos nuevos.'
    partes = [f"de {c['de']}: {c['asunto']}" for c in correos[:maximo]]
    return f'Tenés {len(correos)} correos nuevos. ' + '; '.join(partes) + '.'


def validar_destinatario(direccion: str) -> str:
    direccion = str(direccion or '').strip()
    if not _EMAIL.match(direccion):
        raise ValueError('Dirección de correo inválida.')
    return direccion


def borrador(para: str, asunto: str, cuerpo: str, en_respuesta_a: str = '') -> dict:
    para = validar_destinatario(para)
    asunto = ' '.join(str(asunto or '').split())[:200] or '(sin asunto)'
    cuerpo = str(cuerpo or '').strip()
    if not cuerpo or len(cuerpo) > 20000:
        raise ValueError('El cuerpo del correo debe tener entre 1 y 20000 caracteres.')
    return {'para': para, 'asunto': asunto, 'cuerpo': cuerpo, 'en_respuesta_a': str(en_respuesta_a or '')[:300]}


def enviar(para: str, asunto: str, cuerpo: str, en_respuesta_a: str = '') -> dict:
    """Envía un correo ya confirmado por el dueño."""
    if not configurado():
        raise RuntimeError('Correo no configurado.')
    b = borrador(para, asunto, cuerpo, en_respuesta_a)
    msg = EmailMessage()
    msg['From'] = usuario()
    msg['To'] = b['para']
    msg['Subject'] = b['asunto']
    if b['en_respuesta_a']:
        msg['In-Reply-To'] = b['en_respuesta_a']
        msg['References'] = b['en_respuesta_a']
    msg.set_content(b['cuerpo'] + '\n')
    _, smtp_host = servidores()
    try:
        with smtplib.SMTP(smtp_host, 587, timeout=20) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(usuario(), _clave())
            s.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError('El servidor rechazó el envío: revisá la contraseña de aplicación.') from exc
    except (OSError, smtplib.SMTPException) as exc:
        raise RuntimeError('No se pudo enviar el correo: ' + type(exc).__name__) from exc
    return {'ok': True, 'message': f"Correo enviado a {b['para']}."}


def interpretar(texto: str) -> dict | None:
    """Leer correo o preparar un borrador. Nunca envía: sólo propone."""
    t = _norm(texto).strip(' .!?¿¡')
    t = re.sub(r'^(?:sky|oye sky|hey sky)[\s,]+', '', t)
    if re.search(r'\b(lee|leeme|revisa|revisame|chequea)\s+(?:mi\s+|mis\s+|el\s+)?(correo|correos|mails?|emails?|bandeja)\b'
                 r'|\btengo\s+(correos|mails?|emails?)\b|\bcorreos?\s+nuevos\b', t):
        return {'tipo': 'correo_leer', 'description': 'Leer tus correos no leídos'}
    m = re.match(r'^(?:responde|contesta|respondele|contestale)\s+(?:al\s+)?(?:ultimo\s+)?correo(?:\s+de\s+(.+?))?\s+(?:diciendo|que diga|con el texto|que)\s+(.+)$', t)
    if m:
        cuerpo = _recuperar(texto, m.group(2))
        origen = None
        if m.group(1):
            origen = next((c for c in _ULTIMOS if m.group(1) in _norm(c['de']) or m.group(1) in _norm(c['direccion'])), None)
        elif _ULTIMOS:
            origen = _ULTIMOS[0]
        if not origen:
            return {'tipo': 'correo_aviso', 'description': 'Primero decime "lee mis correos" para saber a cuál responder.'}
        asunto = origen['asunto'] if _norm(origen['asunto']).startswith('re:') else 'Re: ' + origen['asunto']
        return {'tipo': 'correo_enviar', 'borrador': borrador(origen['direccion'], asunto, cuerpo, origen.get('message_id', '')),
                'description': f"Responder a {origen['de']}"}
    m = re.match(r'^(?:envia|enviale|manda|mandale|escribe|escribile)\s+(?:un\s+)?(?:correo|mail|email)\s+a\s+(.+?)'
                 r'(?:\s+con\s+asunto\s+(.+?))?\s+(?:diciendo|que diga|con el texto|que)\s+(.+)$', t)
    if m:
        from .sky_contactos import buscar
        destino = m.group(1).strip()
        direccion = destino if '@' in destino else (buscar(destino) or {}).get('email')
        if not direccion:
            return {'tipo': 'correo_aviso', 'description': f'No tengo el correo de «{destino}». Agregalo en ~/.neuralt/contactos.json.'}
        cuerpo = _recuperar(texto, m.group(3))
        asunto = _recuperar(texto, m.group(2)) if m.group(2) else cuerpo[:60]
        return {'tipo': 'correo_enviar', 'borrador': borrador(direccion, asunto, cuerpo), 'description': f'Enviar correo a {destino}'}
    return None


def _recuperar(original: str, normalizado: str) -> str:
    o = _norm(original)
    i = o.find(normalizado)
    if i >= 0 and len(o) == len(original):
        return original[i:i + len(normalizado)]
    return normalizado
