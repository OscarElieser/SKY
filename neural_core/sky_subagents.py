"""SKY Subagent Manager: personalidades delegables SIN privilegios nuevos.

Los subagentes son perfiles persistentes de los cinco ejecutores seguros de
SKY Workflows. Cada delegación CREA un workflow a la espera de aprobación,
NO ejecuta acciones ni modifica el sistema por sí sola.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import sky_workflows as wf

ROOT = Path(__file__).resolve().parents[1]
MAX_AGENTS = 60
MAX_PENDING_PER_AGENT = 5
MAX_DAILY_DELEGATIONS = 30
ID_PATTERN = re.compile(r'^sub_[0-9a-f]{24}$')
ROLE_DESCRIPTIONS = {
    'planificador': 'Planificación e investigación estructurada sin acciones externas',
    'creador_3d': 'Crear mundos 3D mediante SKY Workbench autorizado',
    'diseñador': 'Crear experiencias y diseños mediante SKY Workbench autorizado',
    'documentalista': 'Crear documentos desde contenido proporcionado y aprobado',
    'memoria': 'Guardar notas en la memoria de proyectos con aprobación',
}



def parse_create_command(text: str) -> dict | None:
    """Reconoce una orden explícita; SOLO crea perfiles inactivos, no ejecuta tareas."""
    if not isinstance(text, str) or len(text) > 1800:
        return None
    expression = (
        r'^\s*(?:(?:oye|hey|ok)\s+)?(?:sky[,;:!\s-]+)?'
        r'(?:crea|creá|crear|agrega|agregá)\s+(?:un\s+)?'
        r'subagente\s+(?:llamado|llamada|con\s+nombre)\s+'
        r'(?P<name>.{3,80}?)\s+(?:para|que\s+se\s+encargue\s+de)\s+'
        r'(?P<mission>.{10,1200})\s*$'
    )
    match = re.match(expression, text, flags=re.IGNORECASE)
    if not match:
        return None
    name, mission = match.group('name').strip(), match.group('mission').strip()
    terms = (name + ' ' + mission).lower()
    if any(word in terms for word in ('documento', 'informe', 'redactor', 'word', 'pdf')):
        role = 'documentalista'
    elif any(word in terms for word in ('diseñ', 'diseñador', 'interfaz', 'web visual')):
        role = 'diseñador'
    elif any(word in terms for word in ('3d', 'escena', 'mundo virtual')):
        role = 'creador_3d'
    elif any(word in terms for word in ('memoria', 'recordar', 'guardar notas')):
        role = 'memoria'
    else:
        role = 'planificador'
    return {'name': name, 'mission': mission, 'role': role}


def db_path() -> Path:
    return Path(os.getenv('SKY_SUBAGENTS_DB') or ROOT / 'local_data' / 'sky_subagents.sqlite3')


def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=15000')
    conn.execute('''CREATE TABLE IF NOT EXISTS sky_subagents(
      id TEXT PRIMARY KEY, name TEXT NOT NULL, mission TEXT NOT NULL,
      role TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS sky_subagent_delegations(
      id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES sky_subagents(id),
      workflow_id TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL)''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sky_sub_delegations ON sky_subagent_delegations(agent_id,created_at)')
    return conn


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _output(row) -> dict | None:
    if row is None:
        return None
    value = dict(row)
    value['enabled'] = bool(value['enabled'])
    value['action'] = wf.ROLE_ACTION[value['role']]
    value['capabilities'] = [value['action']]
    value['can_create_subagents'] = False
    value['requires_workflow_approval'] = True
    return value


def catalogue() -> dict:
    return {
        'roles': [{'role': role, 'action': action, 'description': ROLE_DESCRIPTIONS[role]}
                  for role, action in wf.ROLE_ACTION.items()],
        'max_agents': MAX_AGENTS,
        'max_pending_per_agent': MAX_PENDING_PER_AGENT,
        'max_daily_delegations': MAX_DAILY_DELEGATIONS,
        'can_create_subagents_recursively': False,
        'runs_without_owner_approval': False,
    }


def create(name: str, mission: str, role: str) -> dict:
    name = name.strip()
    mission = mission.strip()
    if not 3 <= len(name) <= 80:
        raise ValueError('El nombre requiere entre 3 y 80 caracteres.')
    if not 10 <= len(mission) <= 1200:
        raise ValueError('La misión requiere entre 10 y 1200 caracteres.')
    if role not in wf.ROLE_ACTION:
        raise ValueError('Especialidad no autorizada en SKY Workflows.')
    ident = 'sub_' + uuid.uuid4().hex[:24]
    timestamp = now()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        count = c.execute('SELECT COUNT(*) AS total FROM sky_subagents').fetchone()['total']
        if count >= MAX_AGENTS:
            raise ValueError('Límite de subagentes alcanzado.')
        c.execute('INSERT INTO sky_subagents(id,name,mission,role,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                  (ident, name, mission, role, timestamp, timestamp))
        c.commit()
    return get(ident)


def get(ident: str) -> dict | None:
    if not ID_PATTERN.fullmatch(ident):
        return None
    with connect() as c:
        return _output(c.execute('SELECT * FROM sky_subagents WHERE id=?', (ident,)).fetchone())


def list_all(limit: int = 60) -> list[dict]:
    limit = max(1, min(limit, MAX_AGENTS))
    with connect() as c:
        rows = c.execute('SELECT * FROM sky_subagents ORDER BY created_at DESC, id DESC LIMIT ?',
                         (limit,)).fetchall()
    return [_output(row) for row in rows]


def set_enabled(ident: str, enabled: bool) -> dict:
    if not get(ident):
        raise KeyError('Subagente no encontrado.')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('UPDATE sky_subagents SET enabled=?,updated_at=? WHERE id=?',
                  (int(enabled), now(), ident))
        c.commit()
    return get(ident)


def history(ident: str) -> list[dict]:
    if not get(ident):
        raise KeyError('Subagente no encontrado.')
    with connect() as c:
        records = c.execute('''SELECT workflow_id,created_at FROM sky_subagent_delegations
                              WHERE agent_id=? ORDER BY created_at DESC LIMIT 100''', (ident,)).fetchall()
    return [{'workflow_id': x['workflow_id'], 'created_at': x['created_at'],
             'workflow_status': (wf.get(x['workflow_id']) or {}).get('status', 'unknown')}
            for x in records]


def delegate(ident: str, task: str, params: dict, project_id: str | None = None) -> dict:
    agent = get(ident)
    if not agent:
        raise KeyError('Subagente no encontrado.')
    if not agent['enabled']:
        raise PermissionError('El subagente está desactivado.')
    task = task.strip()
    if not 6 <= len(task) <= 3000:
        raise ValueError('La tarea debe tener entre 6 y 3000 caracteres.')
    if not isinstance(params, dict):
        raise ValueError('Los parámetros deben ser un objeto.')
    # Verificación idéntica a los workflows preexistentes: ningún agente puede
    # inventar nuevas herramientas o delegar en ejecutores no autorizados.
    step = wf._valid_step({'agent': agent['role'], 'action': agent['action'],
                           'task': task, 'params': params})
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        latest = c.execute('SELECT enabled FROM sky_subagents WHERE id=?', (ident,)).fetchone()
        if not latest or not latest['enabled']:
            raise PermissionError('El subagente se desactivó.')
        cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec='seconds')
        daily = c.execute('''SELECT COUNT(*) AS n FROM sky_subagent_delegations
                            WHERE agent_id=? AND created_at>=?''', (ident, cutoff)).fetchone()['n']
        if daily >= MAX_DAILY_DELEGATIONS:
            raise PermissionError('Límite diario de delegaciones alcanzado.')
        existing = c.execute('SELECT workflow_id FROM sky_subagent_delegations WHERE agent_id=?',
                             (ident,)).fetchall()
        active = sum((wf.get(x['workflow_id']) or {}).get('status') in (
            'awaiting_approval','scheduled','running','retry_wait','paused','needs_review'
        ) for x in existing)
        if active >= MAX_PENDING_PER_AGENT:
            raise PermissionError('Terminá o cancelá delegaciones anteriores antes de crear más.')
        flow = wf.create(
            f'{agent["name"]}: {task[:80]}',
            [step],
            project_id=project_id,
            max_attempts=1,
        )
        c.execute('''INSERT INTO sky_subagent_delegations(id,agent_id,workflow_id,created_at)
                     VALUES(?,?,?,?)''',
                  ('del_' + uuid.uuid4().hex[:24], ident, flow['id'], now()))
        c.commit()
    return {'subagent_id': ident, 'workflow_id': flow['id'], 'status': flow['status'],
            'requires_owner_approval': True, 'preview_url': f'/api/sky/workflows/{flow["id"]}/preview',
            'message': 'Delegación creada. El subagente NO empezó a trabajar; revisá y aprobá el flujo.'}
