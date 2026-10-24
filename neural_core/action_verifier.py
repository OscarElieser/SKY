"""Motor de Verificación Real de Acciones para SKY Desktop Agent.

Registra y audita el ciclo de vida de cada orden ejecutada en Windows:
Estados:
- RECEIVED: Orden recibida e interpretada.
- RUNNING: En proceso de ejecución en el sistema operativo.
- SENT: Orden enviada, efecto final no verificado.
- PENDING: Tarea en cola, aún no completada.
- VERIFIED: Ejecución física comprobada (proceso o ventana visible confirmado).
- FAILED: Rechazada por el sistema operativo, error de permisos o recurso no encontrado.
- NEEDS_CONFIRMATION: Acción sensible que requiere confirmación explícita del usuario.
"""
from __future__ import annotations

import json
from collections import deque
import os
import platform
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_DIR = Path.home() / '.neuralt'
LEDGER_PATH = CONFIG_DIR / 'actions_ledger.jsonl'


@dataclass
class ActionRecord:
    command_id: str
    action: str
    target: str
    device: str
    status: str  # RECEIVED, RUNNING, SENT, PENDING, VERIFIED, FAILED, NEEDS_CONFIRMATION
    created_at: str
    execution_time_ms: float = 0.0
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ActionVerifier:
    def __init__(self, ledger_file: Optional[Path] = None):
        self.ledger_file = ledger_file or LEDGER_PATH
        self.device_name = platform.node() or 'Windows-PC'
        self._records: Dict[str, ActionRecord] = {}

    def start_action(self, action: str, target: str, command_id: Optional[str] = None) -> ActionRecord:
        cid = command_id or f"cmd_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc).isoformat()
        rec = ActionRecord(
            command_id=cid,
            action=action,
            target=target,
            device=self.device_name,
            status="RECEIVED",
            created_at=now
        )
        self._records[cid] = rec
        self._persist(rec)
        return rec

    def mark_running(self, command_id: str) -> Optional[ActionRecord]:
        rec = self._records.get(command_id)
        if rec:
            rec.status = "RUNNING"
            self._persist(rec)
        return rec

    def mark_dispatched(self, command_id: str, status: str, result: Dict[str, Any],
                        duration_ms: float = 0.0) -> Optional[ActionRecord]:
        """Registra una acción aceptada sin afirmar que su efecto se verificó."""
        if status not in ('SENT', 'RUNNING', 'PENDING'):
            raise ValueError('Estado no final inválido.')
        rec = self._records.get(command_id)
        if rec:
            rec.status = status
            rec.result = result
            rec.execution_time_ms = round(duration_ms, 2)
            rec.error = None
            self._persist(rec)
        return rec

    def mark_verified(self, command_id: str, result: Dict[str, Any], duration_ms: float = 0.0) -> Optional[ActionRecord]:
        rec = self._records.get(command_id)
        if rec:
            rec.status = "VERIFIED"
            rec.result = result
            rec.execution_time_ms = round(duration_ms, 2)
            rec.error = None
            self._persist(rec)
        return rec

    def mark_failed(self, command_id: str, error: str, duration_ms: float = 0.0) -> Optional[ActionRecord]:
        rec = self._records.get(command_id)
        if rec:
            rec.status = "FAILED"
            rec.error = str(error)
            rec.execution_time_ms = round(duration_ms, 2)
            self._persist(rec)
        return rec

    def mark_needs_confirmation(self, command_id: str, reason: str) -> Optional[ActionRecord]:
        rec = self._records.get(command_id)
        if rec:
            rec.status = "NEEDS_CONFIRMATION"
            rec.error = reason
            self._persist(rec)
        return rec

    def get_action(self, command_id: str) -> Optional[ActionRecord]:
        """Busca primero en memoria y, tras reinicios, recupera el último estado del ledger."""
        record = self._records.get(command_id)
        if record:
            return record
        if not self.ledger_file.exists():
            return None
        last = None
        fields = set(ActionRecord.__dataclass_fields__)
        try:
            with self.ledger_file.open('r', encoding='utf-8') as log:
                for line in log:
                    try:
                        raw = json.loads(line)
                        if not isinstance(raw, dict) or raw.get('command_id') != command_id:
                            continue
                        last = ActionRecord(**{key: value for key, value in raw.items() if key in fields})
                    except (ValueError, TypeError, KeyError):
                        continue
        except OSError:
            return None
        if last:
            self._records[command_id] = last
        return last

    def get_recent_actions(self, limit: int = 25) -> List[Dict[str, Any]]:
        if not self.ledger_file.exists():
            return [r.to_dict() for r in list(self._records.values())[-limit:]]
        try:
            with self.ledger_file.open('r', encoding='utf-8') as log:
                lines = list(deque(log, maxlen=max(1, min(limit, 500))))
            records = []
            for l in lines:
                try:
                    records.append(json.loads(l))
                except Exception:
                    pass
            return records
        except Exception:
            return [r.to_dict() for r in list(self._records.values())[-limit:]]

    def _persist(self, record: ActionRecord) -> None:
        try:
            self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
            with self.ledger_file.open('a', encoding='utf-8') as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + '\n')
        except Exception:
            pass


# Instancia global del verificador
verificador_acciones = ActionVerifier()
