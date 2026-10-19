"""Optional RFC 6238 TOTP + bounded short-lived server-side owner sessions.

Fail-closed when SKY_OWNER_MFA_SECRET is set.  Never generate or expose the
secret through a remotely callable enrollment endpoint. Provision out of band.
Not a clustered identity provider; sessions live in this process only.
"""
from __future__ import annotations
import base64, hashlib, hmac, os, secrets, struct, threading, time
from collections import defaultdict, deque

LOCK = threading.RLock()
LAST_TOTP_STEP = -1
SESSIONS: dict[str, float] = {}  # SHA-256 digests, never plaintext session tokens.
FAILURES: dict[str, deque[float]] = defaultdict(deque)
MAX_SESSIONS = 32
MAX_ATTEMPTS = 5
WINDOW = 300
LIFETIME = 20 * 60


def required() -> bool:
    return bool(os.getenv('SKY_OWNER_MFA_SECRET', '').strip())


def _key() -> bytes:
    raw = os.getenv('SKY_OWNER_MFA_SECRET', '').strip().replace(' ', '').upper()
    if not raw:
        raise RuntimeError('MFA no configurado')
    try:
        key = base64.b32decode(raw + '=' * ((-len(raw)) % 8), casefold=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise RuntimeError('SKY_OWNER_MFA_SECRET debe ser Base32') from exc
    if len(key) < 20:
        raise RuntimeError('SKY_OWNER_MFA_SECRET necesita al menos 20 bytes aleatorios')
    return key


def code_at(timestamp: int | float) -> str:
    step = int(timestamp) // 30
    digest = hmac.new(_key(), struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0f
    value = (struct.unpack('>I', digest[offset:offset+4])[0] & 0x7fffffff) % 1_000_000
    return f'{value:06d}'


def verify(code: str, now: float | None = None) -> bool:
    if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
        return False
    when = time.time() if now is None else now
    return any(secrets.compare_digest(code, code_at(when + offset * 30)) for offset in (-1, 0, 1))


def _digest(session: str) -> str:
    return hashlib.sha256(session.encode('ascii')).hexdigest()


def open_session(code: str, remote: str = 'unknown') -> tuple[str, int]:
    global LAST_TOTP_STEP
    if not required():
        raise RuntimeError('MFA no configurado')
    now = time.monotonic()
    remote = remote[:128]
    with LOCK:
        q = FAILURES[remote]
        while q and q[0] + WINDOW <= now:
            q.popleft()
        if len(q) >= MAX_ATTEMPTS:
            raise PermissionError('Demasiados intentos de segundo factor')
        if not verify(code):
            q.append(now)
            raise ValueError('Segundo factor incorrecto')
        # Prevent immediate reuse of a stolen code during the same TOTP window.
        # Per-process state only; production requires shared replay protection.
        absolute=int(time.time()//30)
        matching=[step for step in (absolute-1,absolute,absolute+1)
                  if secrets.compare_digest(code,code_at(step*30))]
        if not matching or max(matching)<=LAST_TOTP_STEP:
            q.append(now)
            raise ValueError('Código ya utilizado; esperá el siguiente código temporal')
        LAST_TOTP_STEP=max(matching)
        FAILURES.pop(remote, None)
        expired = [key for key, until in SESSIONS.items() if until <= now]
        for key in expired:
            del SESSIONS[key]
        if len(SESSIONS) >= MAX_SESSIONS:
            raise PermissionError('Límite de sesiones administrativas')
        token = secrets.token_urlsafe(32)
        SESSIONS[_digest(token)] = now + LIFETIME
        return token, LIFETIME


def valid(session: str | None) -> bool:
    if not required():
        return True
    if not isinstance(session, str) or len(session) > 128 or len(session) < 30:
        return False
    now = time.monotonic()
    key = _digest(session)
    with LOCK:
        until = SESSIONS.get(key, 0)
        if until <= now:
            SESSIONS.pop(key, None)
            return False
        return True


def revoke(session: str | None) -> None:
    if isinstance(session, str) and len(session) <= 128:
        with LOCK:
            SESSIONS.pop(_digest(session), None)


def validate_configuration() -> None:
    if required():
        _key()
