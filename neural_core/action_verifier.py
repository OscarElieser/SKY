"""Motor de Verificación Real de Acciones para SKY Desktop Agent.

Registra y audita el ciclo de vida de cada orden ejecutada en Windows:
Estados:
- RECEIVED: Orden recibida e interpretada.
- RUNNING: En proceso de ejecución en el sistema operativo.
- VERIFIED: Ejecución física comprobada (proceso o ventana visible confirmado).
- FAILED: Rechazada por el sistema operativo, error de permisos o recurso no encontrado.
- NEEDS_CONFIRMATION: Acción sensible que requiere confirmación explícita del usuario.
"""
from __future__ import annotations

import json
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
    status: str  # RECEIVED, RUNNING, VERIFIED, FAILED, NEEDS_CONFIRMATION
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
        return self._records.get(command_id)

    def get_recent_actions(self, limit: int = 25) -> List[Dict[str, Any]]:
        if not self.ledger_file.exists():
            return [r.to_dict() for r in list(self._records.values())[-limit:]]
        try:
            lines = self.ledger_file.read_text(encoding='utf-8').strip().splitlines()
            records = []
            for l in lines[-limit:]:
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
