"""Cola local de propuestas de voz manos libres; nunca ejecuta por sí sola."""
from pathlib import Path
import json
from datetime import datetime,timezone
from uuid import uuid4

INBOX=Path(__file__).resolve().parent.parent/'local_data'/'voice_inbox.json'


def read_inbox():
    try:
        entries=json.loads(INBOX.read_text(encoding='utf-8'))
        return entries if isinstance(entries,list) else []
    except (OSError,ValueError): return []


def add_inbox(text,command):
    from .sky_capacidades import ACCION_A_CAPACIDAD, ACCIONES_INTERFAZ
    if not isinstance(command,dict) or (command.get('action') not in ACCION_A_CAPACIDAD and command.get('action') not in ACCIONES_INTERFAZ):
        raise ValueError('Propuesta de acción no admitida')
    entry={'id':str(uuid4()),'timestamp':datetime.now(timezone.utc).isoformat(),
           'text':str(text)[:500], 'action':command['action'],'params':command.get('params',{}) if isinstance(command.get('params',{}),dict) else {},
           'description':str(command.get('description',''))[:180]}
    INBOX.parent.mkdir(parents=True,exist_ok=True)
    INBOX.write_text(json.dumps((read_inbox()+[entry])[-40:],ensure_ascii=False,indent=2),encoding='utf-8')
    try: INBOX.chmod(0o600)
    except OSError: pass
    return entry


def dismiss_inbox(entry_id):
    entries=[x for x in read_inbox() if x.get('id')!=entry_id]
    INBOX.parent.mkdir(parents=True,exist_ok=True)
    INBOX.write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
