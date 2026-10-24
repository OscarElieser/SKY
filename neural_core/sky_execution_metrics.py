"""KPIs reales del ciclo de ejecución del agente SKY. Sin valores simulados."""
from __future__ import annotations

from collections import Counter


def summarize_action_receipts(events: list[dict]) -> dict:
    """Devuelve los últimos estados de cada comando dentro de una muestra de eventos."""
    latest: dict[str, dict] = {}
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        cid = event.get('command_id')
        if not isinstance(cid, str) or not cid:
            # Registros sin ID no sirven para medir ejecución individual.
            continue
        latest[cid] = event

    counts = Counter(event.get('status', 'UNKNOWN') for event in latest.values())
    finished = counts['VERIFIED'] + counts['FAILED']
    durations = [
        item['execution_time_ms'] for item in latest.values()
        if item.get('status') in ('VERIFIED', 'FAILED')
        and isinstance(item.get('execution_time_ms'), (int, float))
        and not isinstance(item.get('execution_time_ms'), bool)
        and item['execution_time_ms'] >= 0
    ]
    return {
        'sample_events': len(events),
        'total_actions': len(latest),
        'verified': counts['VERIFIED'],
        'failed': counts['FAILED'],
        'sent': counts['SENT'],
        'pending': counts['PENDING'],
        'running': counts['RUNNING'],
        'dispatched': counts['DISPATCHED'],
        'needs_confirmation': counts['NEEDS_CONFIRMATION'],
        'received': counts['RECEIVED'],
        'completion_success_pct': round(100 * counts['VERIFIED'] / finished, 1) if finished else None,
        'average_finished_ms': round(sum(durations) / len(durations), 1) if durations else None,
        'measured_durations': len(durations),
        'scope': 'Últimos eventos disponibles del agente; no es el historial total.',
    }
