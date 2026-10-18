"""SKY v9.3: persistent owner-approved workflows and durable scheduler.

Only audited SKY Workbench actions may be executed. No arbitrary shell, bank
operations, deployment, untrusted URLs, or provider calls are permitted here.
Job progress and execution links persist in SQLite across restarts. Ambiguous
side effects are stopped for manual review rather than automatically replayed.
"""
from __future__ import annotations
import json, os, sqlite3, uuid, time, re, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from neural_core.sky_workbench import ALLOWED_ACTIONS, create_item, get_item, execute_item

ROOT=Path(__file__).resolve().parents[1]
SAFE_ACTIONS=set(ALLOWED_ACTIONS)
ALLOWED_AGENTS={'planificador','creador_3d','diseñador','documentalista','memoria'}
ROLE_ACTION={'planificador':'plan','creador_3d':'world','diseñador':'experience','documentalista':'document','memoria':'memory'}

def db_path():return Path(os.getenv('SKY_WORKFLOWS_DB') or ROOT/'local_data'/'sky_workflows.sqlite3')
def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def _timestamp(value):
    if not value:return time.time()
    dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError('La fecha debe incluir zona horaria UTC u offset')
    return dt.timestamp()

def connect():
    path=db_path();path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=15,isolation_level=None)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=15000')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS workflows(
      id TEXT PRIMARY KEY, name TEXT NOT NULL, project_id TEXT, steps TEXT NOT NULL,
      status TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0,
      next_run REAL NOT NULL, interval_minutes INTEGER, current_step INTEGER NOT NULL DEFAULT 0,
      current_item TEXT, results TEXT NOT NULL DEFAULT '[]', attempt INTEGER NOT NULL DEFAULT 0,
      max_attempts INTEGER NOT NULL DEFAULT 3, run_number INTEGER NOT NULL DEFAULT 1,
      lease_until REAL, last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      pause_requested INTEGER NOT NULL DEFAULT 0, project_snapshot TEXT);
    CREATE TABLE IF NOT EXISTS workflow_events(
      id INTEGER PRIMARY KEY AUTOINCREMENT, workflow_id TEXT NOT NULL
      REFERENCES workflows(id) ON DELETE CASCADE, at TEXT NOT NULL,
      event TEXT NOT NULL, detail TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_sky_flow_due ON workflows(status,next_run);
    ''')
    # Migración compatible con bases v9.3 existentes.
    columns={row['name'] for row in conn.execute('PRAGMA table_info(workflows)')}
    if 'pause_requested' not in columns:
        conn.execute('ALTER TABLE workflows ADD COLUMN pause_requested INTEGER NOT NULL DEFAULT 0')
    if 'project_snapshot' not in columns:
        conn.execute('ALTER TABLE workflows ADD COLUMN project_snapshot TEXT')
    return conn

def _event(c,ident,event,detail=''):
    c.execute('INSERT INTO workflow_events(workflow_id,at,event,detail) VALUES(?,?,?,?)',
              (ident,now(),event,str(detail)[:360]))

def _as_dict(row):
    if row is None:return None
    d=dict(row);d['steps']=json.loads(d['steps']);d['results']=json.loads(d['results']);d['approved']=bool(d['approved']);d['pause_requested']=bool(d.get('pause_requested',0));d['project_snapshot']=json.loads(d['project_snapshot']) if d.get('project_snapshot') else None
    d['next_run_at']=datetime.fromtimestamp(d['next_run'],timezone.utc).isoformat(timespec='seconds')
    return d

def get(ident):
    with connect() as c:return _as_dict(c.execute('SELECT * FROM workflows WHERE id=?',(ident,)).fetchone())

def list_all(limit=80):
    with connect() as c:
        return [_as_dict(r) for r in c.execute('SELECT * FROM workflows ORDER BY created_at DESC LIMIT ?',(min(100,max(1,limit)),))]

def history(ident):
    with connect() as c:
        if not c.execute('SELECT 1 FROM workflows WHERE id=?',(ident,)).fetchone():raise KeyError(ident)
        return [dict(r) for r in c.execute('SELECT at,event,detail FROM workflow_events WHERE workflow_id=? ORDER BY id DESC LIMIT 120',(ident,))]

# Continuidad segura: sólo metadatos explícitos de pasos PREVIOS.
TOKEN_RE=re.compile(r'\{\{([^{}]{1,80})\}\}')
ALLOWED_OUTPUT_FIELDS={'kind','world_id','name','title','file_name','download','id','message','label','plan_summary'}

def _tokens(value):
    if isinstance(value,str):
        return [m.group(1).strip() for m in TOKEN_RE.finditer(value)]
    if isinstance(value,dict):
        return [t for item in value.values() for t in _tokens(item)]
    if isinstance(value,list):
        return [t for item in value for t in _tokens(item)]
    return []

def _validate_tokens(steps, project_id):
    for idx,step in enumerate(steps):
        for key in _tokens({'task':step['task'],'params':step['params']}):
            if key in ('project.title','project.description'):
                if not project_id:raise ValueError('Las referencias project.* requieren un proyecto')
                continue
            match=re.fullmatch(r'step\.(\d{1,2})\.([a-z_]+)',key)
            if not match or not 1<=int(match.group(1))<=idx or match.group(2) not in ALLOWED_OUTPUT_FIELDS:
                raise ValueError('Referencia no permitida o hacia un paso futuro: '+key[:80])

def _resolve_value(value,lookup):
    if isinstance(value,str):
        def replace(m):
            key=m.group(1).strip()
            if key not in lookup:raise ValueError('El paso anterior no produjo el campo '+key[:80])
            return str(lookup[key])[:3000]
        return TOKEN_RE.sub(replace,value)
    if isinstance(value,dict):return {k:_resolve_value(v,lookup) for k,v in value.items()}
    if isinstance(value,list):return [_resolve_value(v,lookup) for v in value]
    return value

def resolve_step(flow):
    index=flow['current_step']
    step=flow['steps'][index]
    lookup={}
    if flow['project_id']:
        from neural_core.sky_projects import project
        p=project(flow['project_id'])
        if not p:raise ValueError('El proyecto asociado ya no está disponible')
        approved=flow.get('project_snapshot') or p
        lookup={'project.title':approved['title'],'project.description':approved['description']}
    for result in flow['results']:
        if result.get('run')!=flow['run_number']:continue
        num=result.get('step',0)
        if not 1<=num<=index:continue
        output=result.get('result') or {}
        for key in ALLOWED_OUTPUT_FIELDS:
            if key in output and isinstance(output[key],(str,int,float,bool)):
                lookup[f'step.{num}.{key}']=output[key]
        if output.get('kind')=='file' and output.get('name'):
            lookup[f'step.{num}.file_name']=output['name']
    resolved={'agent':step['agent'],'action':step['action'],
              'task':_resolve_value(step['task'],lookup),
              'params':_resolve_value(step['params'],lookup)}
    return _valid_step(resolved)

def fingerprint(flow):
    data={k:flow[k] for k in ('name','project_id','steps','interval_minutes','max_attempts','project_snapshot')}
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def preview(ident):
    flow=get(ident)
    if not flow:raise KeyError(ident)
    steps=[]
    for idx,step in enumerate(flow['steps'],1):
        steps.append({'number':idx,'agent':step['agent'],'action':step['action'],
                      'task':step['task'][:500],
                      'references':_tokens({'task':step['task'],'params':step['params']}),
                      'writes_data':step['action']!='plan'})
    return {'id':ident,'name':flow['name'],'status':flow['status'],
            'project_id':flow['project_id'],'project_snapshot':flow['project_snapshot'],
            'next_run_at':flow['next_run_at'],
            'fingerprint':fingerprint(flow),'steps':steps,
            'external_ai_calls':False,'automatic_payments':False,
            'requires_owner_approval':not flow['approved']}

def _valid_step(step):
    if not isinstance(step,dict):raise ValueError('Los pasos deben ser objetos')
    role=step.get('agent');action=step.get('action')
    if role not in ALLOWED_AGENTS or ROLE_ACTION[role]!=action or action not in SAFE_ACTIONS:
        raise ValueError('Agente y acción no coinciden con el catálogo seguro')
    prompt=step.get('task','')
    if not isinstance(prompt,str) or not 6<=len(prompt.strip())<=3000:raise ValueError('Descripción inválida del paso')
    params=step.get('params',{})
    if not isinstance(params,dict):raise ValueError('Parámetros de paso inválidos')
    raw=json.dumps(params,ensure_ascii=False,allow_nan=False)
    if len(raw)>40000:raise ValueError('Parámetros de paso demasiado largos')
    if action=='document':
        spec=params.get('document',{})
        if not isinstance(spec,dict) or not (spec.get('content') or spec.get('csv') or spec.get('rows')):
            raise ValueError('Los documentos necesitan contenido real, no solo una instrucción')
        if str(spec.get('ai_provider','none')) not in ('none',''):
            raise ValueError('Los flujos no envían automáticamente contenido a proveedores de IA')
    if action=='memory' and not str(params.get('content','')).strip():
        raise ValueError('La nota necesita contenido')
    return {'agent':role,'action':action,'task':prompt.strip(),'params':params}

def create(name,steps,project_id=None,run_at=None,interval_minutes=None,max_attempts=3):
    if not isinstance(name,str) or not 3<=len(name.strip())<=120:raise ValueError('Nombre de flujo entre 3 y 120 caracteres')
    if not isinstance(steps,list) or not 1<=len(steps)<=8:raise ValueError('Se admiten de 1 a 8 pasos')
    steps=[_valid_step(step) for step in steps]
    _validate_tokens(steps,project_id)
    if interval_minutes is not None and not 1<=int(interval_minutes)<=10080:
        raise ValueError('Intervalo válido: de 1 a 10080 minutos')
    if interval_minutes is not None and any(s['action']!='plan' for s in steps) and int(interval_minutes)<60:
        raise ValueError('Para crear archivos, mundos o notas de forma periódica, usá al menos 60 minutos')
    if not 1<=max_attempts<=5:raise ValueError('Se admiten 1 a 5 intentos para acciones idempotentes')
    snapshot=None
    if project_id is not None:
        from neural_core.sky_projects import project
        p=project(project_id)
        if not p:raise KeyError('Proyecto no encontrado')
        snapshot={'title':p['title'],'description':p['description'],'version':p['version']}
    start=_timestamp(run_at);ident='flow_'+uuid.uuid4().hex[:20]
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('INSERT INTO workflows(id,name,project_id,steps,status,next_run,interval_minutes,max_attempts,created_at,updated_at,project_snapshot) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                  (ident,name.strip(),project_id,json.dumps(steps,ensure_ascii=False),'awaiting_approval',start,interval_minutes,max_attempts,now(),now(),json.dumps(snapshot,ensure_ascii=False) if snapshot else None))
        _event(c,ident,'created','En espera de aprobación del propietario')
        c.commit()
    return get(ident)

def approve(ident,expected_fingerprint=None):
    if expected_fingerprint is not None:
        flow=get(ident)
        if not flow:raise KeyError(ident)
        if fingerprint(flow)!=expected_fingerprint:raise RuntimeError('La vista previa ya no coincide con el flujo aprobado')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        r=c.execute('SELECT status FROM workflows WHERE id=?',(ident,)).fetchone()
        if not r:raise KeyError(ident)
        if r['status']!='awaiting_approval':raise RuntimeError('El flujo ya fue aprobado o cambió de estado')
        c.execute('UPDATE workflows SET status=?,approved=1,updated_at=? WHERE id=?',('scheduled',now(),ident))
        _event(c,ident,'approved','Aprobado explícitamente por clave del propietario')
        c.commit()
    return get(ident)

def pause(ident):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT status FROM workflows WHERE id=?',(ident,)).fetchone()
        if not row:raise KeyError(ident)
        if row['status'] not in ('scheduled','retry_wait'):
            raise RuntimeError('Sólo se pueden pausar flujos entre pasos')
        c.execute("UPDATE workflows SET status='paused',pause_requested=1,updated_at=? WHERE id=?",(now(),ident))
        _event(c,ident,'paused','Pausado por el propietario antes del siguiente paso')
        c.commit()
    return get(ident)

def resume(ident):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT status,approved FROM workflows WHERE id=?',(ident,)).fetchone()
        if not row:raise KeyError(ident)
        if row['status']!='paused' or not row['approved']:
            raise RuntimeError('Sólo se reanudan flujos aprobados y pausados')
        c.execute("UPDATE workflows SET status='scheduled',pause_requested=0,updated_at=? WHERE id=?",(now(),ident))
        _event(c,ident,'resumed','Reanudado por el propietario; respeta su fecha programada')
        c.commit()
    return get(ident)

def project_continuity(project_id):
    from neural_core.sky_projects import brief
    base=brief(project_id)
    with connect() as c:
        rows=c.execute('SELECT * FROM workflows WHERE project_id=? ORDER BY created_at DESC LIMIT 100',(project_id,)).fetchall()
    flows=[]
    for row in rows:
        x=_as_dict(row)
        flows.append({'id':x['id'],'name':x['name'],'status':x['status'],
                      'progress':{'done':x['current_step'],'total':len(x['steps'])},
                      'next_run_at':x['next_run_at'],'delivered':len(x['results']),
                      'last_error':x['last_error']})
    return {'project':base['project'],'deliverables':base['items'],
            'workflows':flows,'notes_count':base['notes_count'],
            'messages_count':base['messages_count']}

def cancel(ident):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT status FROM workflows WHERE id=?',(ident,)).fetchone()
        if not row:raise KeyError(ident)
        if row['status']=='running':raise RuntimeError('El paso está ejecutándose: esperá su finalización')
        if row['status']=='cancelled':c.commit();return get(ident)
        c.execute('UPDATE workflows SET status=?,updated_at=? WHERE id=?',('cancelled',now(),ident))
        _event(c,ident,'cancelled','Cancelado por el propietario')
        c.commit()
    return get(ident)

def retry(ident, acknowledge_partial_effects=False):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM workflows WHERE id=?',(ident,)).fetchone()
        if not row:raise KeyError(ident)
        if row['status'] not in ('needs_review','failed'):
            raise RuntimeError('Solo se reintentan flujos fallidos o pendientes de revisión')
        steps=json.loads(row['steps']);step=steps[row['current_step']]
        if step['action']!='plan' and not acknowledge_partial_effects:
            raise PermissionError('Confirmá el riesgo de posibles efectos parciales')
        c.execute("UPDATE workflows SET status='scheduled',next_run=?,current_item=NULL,attempt=0,lease_until=NULL,last_error=NULL,updated_at=? WHERE id=?",
                  (time.time(),now(),ident))
        _event(c,ident,'retry_approved','Reintento manual autorizado')
        c.commit()
    return get(ident)

def _claim():
    current=time.time()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        # Una ejecución que perdió su lease no se duplica: se recupera comprobando el item asociado.
        row=c.execute("SELECT * FROM workflows WHERE approved=1 AND ((status IN ('scheduled','retry_wait') AND pause_requested=0 AND next_run<=?) OR (status='running' AND pause_requested=0 AND lease_until<?)) ORDER BY next_run,id LIMIT 1",
                      (current,current)).fetchone()
        if not row:c.commit();return None
        c.execute("UPDATE workflows SET status='running',lease_until=?,updated_at=? WHERE id=?",
                  (current+900,now(),row['id']))
        _event(c,row['id'],'claimed','Paso adquirido por motor local')
        c.commit()
        return row['id']

def _finish_step(ident,item):
    result=item.get('output') or {}
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM workflows WHERE id=?',(ident,)).fetchone()
        if not row or row['status']!='running':c.commit();return
        results=json.loads(row['results'])
        results.append({'run':row['run_number'],'step':row['current_step']+1,'action':item['action'],
                        'item_id':item['id'],'result':result})
        idx=row['current_step']+1;steps=json.loads(row['steps'])
        done=idx==len(steps)
        if done and row['interval_minutes']:
            nxt=max(time.time()+row['interval_minutes']*60, row['next_run']+row['interval_minutes']*60)
            c.execute("UPDATE workflows SET status='scheduled',current_step=0,current_item=NULL,results=?,attempt=0,run_number=run_number+1,next_run=?,lease_until=NULL,last_error=NULL,updated_at=? WHERE id=?",
                      (json.dumps(results[-80:],ensure_ascii=False),nxt,now(),ident))
            _event(c,ident,'run_completed','Próxima repetición programada')
        else:
            c.execute('UPDATE workflows SET status=?,current_step=?,current_item=NULL,results=?,attempt=0,lease_until=NULL,last_error=NULL,updated_at=? WHERE id=?',
                      ('completed' if done else 'scheduled',idx,json.dumps(results[-80:],ensure_ascii=False),now(),ident))
            _event(c,ident,'run_completed' if done else 'step_completed',item['id'])
        c.commit()
    # La asociación es secundaria y nunca debe volver a ejecutar un efecto ya completado.
    if row['project_id'] and result.get('kind') in ('world','experience','file'):
        try:
            from neural_core.sky_projects import link
            kind={'world':'world','experience':'experience','file':'task'}[result['kind']]
            ref=result.get('world_id') if kind=='world' else item['id']
            link(row['project_id'],kind,ref,item['task'][:130])
        except Exception as exc:
            with connect() as c:
                _event(c,ident,'link_warning',type(exc).__name__)

def _failure(ident, exc):
    kind=type(exc).__name__
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM workflows WHERE id=?',(ident,)).fetchone()
        if not row:c.commit();return
        steps=json.loads(row['steps'])
        action=steps[row['current_step']]['action']
        attempt=row['attempt']+1
        # Failures after attempting a side effect need human review, not blind retry.
        existing=get_item(row['current_item']) if row['current_item'] else None
        if action=='plan' and attempt<row['max_attempts']:
            state='retry_wait';next_run=time.time()+min(120,2**attempt)
        elif existing and action!='plan':
            state='needs_review';next_run=row['next_run']
        else:
            state='failed';next_run=row['next_run']
        c.execute("UPDATE workflows SET status=?,attempt=?,next_run=?,last_error=?,lease_until=NULL,current_item=CASE WHEN ?='retry_wait' THEN NULL ELSE current_item END,updated_at=? WHERE id=?",
                  (state,attempt,next_run,kind,state,now(),ident))
        _event(c,ident,state,kind)
        c.commit()

def run_once():
    """Runs at most one due step. Safe to call repeatedly or after a restart."""
    ident=_claim()
    if ident is None:return None
    try:
        flow=get(ident)
        if flow['current_step']>=len(flow['steps']):raise RuntimeError('Índice de paso inválido')
        step=flow['steps'][flow['current_step']]
        item=get_item(flow['current_item']) if flow['current_item'] else None
        if item and item['status']=='completada':
            _finish_step(ident,item);return get(ident)
        if item and item['status'] in ('ejecutando','error'):
            # Could have committed an external effect before crash; stop for inspection.
            with connect() as c:
                c.execute("UPDATE workflows SET status='needs_review',lease_until=NULL,last_error=?,updated_at=? WHERE id=?",('Estado anterior ambiguo',now(),ident))
                _event(c,ident,'needs_review','Tarea anterior ambigua; no se ejecuta dos veces')
            return get(ident)
        if item is None:
            resolved=resolve_step(flow)
            inputs=json.dumps({'task':resolved['task'],'params':resolved['params']},
                              sort_keys=True,ensure_ascii=False)
            with connect() as c:
                _event(c,ident,'inputs_resolved',hashlib.sha256(inputs.encode()).hexdigest()[:32])
            item=create_item(resolved['task'],resolved['action'],resolved['params'])
            with connect() as c:
                c.execute('UPDATE workflows SET current_item=?,updated_at=? WHERE id=? AND status=?',
                          (item['id'],now(),ident,'running'))
                _event(c,ident,'work_item_created',item['id'])
        finished=execute_item(item['id'],approve=True)
        _finish_step(ident,finished)
        return get(ident)
    except Exception as exc:
        _failure(ident,exc)
        return get(ident)

def status():
    with connect() as c:
        counts={r['status']:r['count'] for r in c.execute('SELECT status,count(*) AS count FROM workflows GROUP BY status')}
        return {'engine':'SKY Autonomous Workflow Engine','counts':counts,'catalogue':sorted(ALLOWED_AGENTS),
                'persistence':'SQLite','scheduler':'local; activo mientras el proceso servidor esté ejecutándose',
                'independent_external_services':False,
                'enabled':os.getenv('SKY_WORKFLOWS_ENABLED','1')=='1',
                'continuity':'project + prior-step output references; owner approved'}
