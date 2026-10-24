"""Autorizaciones efímeras para propuestas de acciones de SKY.

Una aprobación solo sirve para el tipo, los parámetros y el dispositivo mostrado.
Caduca, no se reutiliza y no persiste claves en disco. Requiere un solo worker
para este estado en memoria (o almacenamiento compartido al escalar).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time

_TTL_SECONDS = 180
_MAX_PENDING = 512


class ApprovalVault:
    def __init__(self, ttl: int = _TTL_SECONDS):
        self.ttl = ttl
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[float, str, str, str]] = {}

    @staticmethod
    def _fingerprint(payload: dict) -> str:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    @staticmethod
    def _identity(request) -> str:
        # El dueño ya está autenticado por require_key (+ MFA opcional). Atamos el
        # recibo a la misma sesión cuando existe; jamás guardamos los encabezados.
        session = request.headers.get('X-SKY-SESSION', '')
        key = request.headers.get('X-SKY-KEY', '')
        return hashlib.sha256((session or key).encode('utf-8')).hexdigest()

    def issue(self, kind: str, payload: dict, request) -> str:
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode('ascii')).hexdigest()
        expiry = time.monotonic() + self.ttl
        fp = self._fingerprint(payload)
        identity = self._identity(request)
        with self._lock:
            now = time.monotonic()
            self._pending = {k: v for k, v in self._pending.items() if v[0] > now}
            if len(self._pending) >= _MAX_PENDING:
                # No expulsar autorizaciones válidas para aceptar más trabajo.
                raise RuntimeError('Demasiadas operaciones pendientes de confirmación.')
            self._pending[digest] = (expiry, kind, fp, identity)
        return token

    def consume(self, token: str, kind: str, payload: dict, request) -> bool:
        if not isinstance(token, str) or len(token) > 100 or len(token) < 32:
            return False
        digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
        fp = self._fingerprint(payload)
        identity = self._identity(request)
        with self._lock:
            entry = self._pending.get(digest)
            if not entry:
                return False
            expiry, actual_kind, actual_fp, actual_identity = entry
            if expiry <= time.monotonic():
                del self._pending[digest]
                return False
            if not (hmac.compare_digest(actual_kind, kind)
                    and hmac.compare_digest(actual_fp, fp)
                    and hmac.compare_digest(actual_identity, identity)):
                return False
            del self._pending[digest]  # consumir ANTES de ejecutar: evita doble clic/replay
            return True


approvals = ApprovalVault()
