"""SKY Workbench: planes, memoria y entregables persistentes del propietario.

No ejecuta instrucciones de sistema. Los flujos sólo usan herramientas incluidas
con un catálogo fijo; la fase de planificación no tiene efectos secundarios.
"""
from __future__ import annotations
import json,sqlite3,os,uuid,time,re,hashlib
from datetime import datetime,timezone
from pathlib import Path
from .sky_roles import plan_for

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/'local_data'

def _db_path():
    val=os.environ.get('SKY_WORKBENCH_DB','').strip()
    p=Path(val) if val else STORE/'sky_workbench.sqlite3'
    p.parent.mkdir(exist_ok=True,parents=True)
    return p

def _conn():
    c=sqlite3.connect(_db_path(),timeout=15)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA busy_timeout=15000')
    c.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS work_items (
      id TEXT PRIMARY KEY,task TEXT NOT NULL,plan TEXT NOT NULL,action TEXT NOT NULL,
      params TEXT NOT NULL,status TEXT NOT NULL,output TEXT,
      error TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS personal_notes (
      id TEXT PRIMARY KEY,label TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS experiences (
      id TEXT PRIMARY KEY,title TEXT NOT NULL,spec TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,event TEXT NOT NULL,
      item_id TEXT,metadata TEXT NOT NULL);
    ''')
    return c

def _now():return datetime.now(timezone.utc).isoformat()

def _audit(c,event,item_id=None,metadata=None):
    # No incluir claves de API, el texto del usuario ni contraseñas en el registro.
    c.execute('INSERT INTO audit(at,event,item_id,metadata) VALUES(?,?,?,?)',
              (_now(),event,item_id,json.dumps(metadata or {},ensure_ascii=False)))

def _json(value,limit=25000):
    result=json.dumps(value,ensure_ascii=False,allow_nan=False)
    if len(result)>limit:raise ValueError('Parámetros demasiado largos')
    return result

ALLOWED_ACTIONS={
 'plan': 'Elaborar plan técnico (sin cambios en sistemas)',
 'world': 'Crear un mundo 3D local guardado',
 'document': 'Generar un archivo de Office Studio y guardarlo en una carpeta privada',
 'experience': 'Guardar un diseño web editable y exportable',
 'memory': 'Guardar una nota privada del propietario',
}

def create_item(task:str,action:str='plan',params:dict|None=None)->dict:
    if not isinstance(task,str) or not (6<=len(task.strip())<=6000):raise ValueError('Describí una tarea entre 6 y 6000 caracteres')
    if action not in ALLOWED_ACTIONS:raise ValueError('Acción no admitida')
    params=params or {}
    if not isinstance(params,dict):raise ValueError('Parámetros inválidos')
    raw=_json(params,70000)
    plan=plan_for(task)
    if action!='plan': plan['requires_approval']=True
    ident='sky-'+uuid.uuid4().hex[:16]
    now=_now()
    with _conn() as c:
        c.execute('INSERT INTO work_items VALUES(?,?,?,?,?,?,?,?,?,?)',
            (ident,task,_json(plan),action,raw,'pendiente',None,None,now,now))
        _audit(c,'created',ident,{'action':action,'roles':[r['id'] for r in plan['roles']]})
    return get_item(ident)

def get_item(ident:str):
    with _conn() as c:
        row=c.execute('SELECT * FROM work_items WHERE id=?',(ident,)).fetchone()
    return _unpack(row) if row else None

def _unpack(row):
    d=dict(row)
    for key in ('plan','params','output'):
        if d[key]:d[key]=json.loads(d[key])
    return d

def list_items(limit=30):
    with _conn() as c:
        rows=c.execute('SELECT * FROM work_items ORDER BY created_at DESC LIMIT ?',(max(1,min(100,limit)),)).fetchall()
    return [_unpack(r) for r in rows]

def _safe_filename(name:str)->str:
    slug=re.sub('[^a-z0-9_-]+','_',str(name).casefold())[:65].strip('_')
    return slug or 'sky'

def _folder():
    dest=STORE/'sky_outputs';dest.mkdir(exist_ok=True,parents=True)
    return dest

def _design_from_params(task,params):
    from .sky_experience import make_experience
    return make_experience(task,params)

def _apply(task,action,params,ident):
    if action=='plan':
        # La planificación es estructurada y determinista: no fingir razonamiento de LLM.
        source=get_item(ident) or {}
        plan=source.get('plan') or {}
        roles=', '.join(r.get('title','') for r in plan.get('roles',[])[:3])
        stages='; '.join(s.get('name','') for s in plan.get('steps',[])[:5])
        outline=f'Objetivo: {task}. Especialidades: {roles}. Etapas recomendadas: {stages}.'[:2400]
        return {'kind':'plan','message':'Plan local estructurado guardado',
                'plan_summary':outline}
    if action=='world':
        from metaverse.store import create_world
        name=str(params.get('name') or task[:60])[:65]
        prompt=str(params.get('prompt') or task)[:1000]
        seed=int(params.get('seed',42))
        result=create_world(name,prompt,seed)
        return {'kind':'world','world_id':result['id'],'url':'/world','name':name,'version':result.get('version')}
    if action=='document':
        from .sky_office import create_document
        spec=params.get('document') or {}
        if not isinstance(spec,dict):raise ValueError('Necesitás un documento estructurado')
        # Requiere contenido real; nunca escribir una promesa en lugar de un archivo.
        if not (spec.get('content') or spec.get('csv') or spec.get('rows')):
            raise ValueError('Añadí contenido o datos reales antes de generar el documento')
        if str(spec.get('kind','docx')).lower() in {'xlsx','csv'} and not (spec.get('csv') or spec.get('headers')):
            raise ValueError('Para Excel o CSV, proporcioná datos tabulares CSV o encabezados y filas')
        if spec.get('ai_provider') not in (None,'none',''):
            raise ValueError('La generación mediante proveedor se activa por el editor Office, no desde una tarea automática')
        doc=create_document(spec)
        dest=_folder()/(ident+'_'+_safe_filename(Path(doc.filename).stem)+Path(doc.filename).suffix.lower())
        # Escritura exclusiva: no sobrescribir artefactos existentes.
        with dest.open('xb') as f:f.write(doc.data)
        return {'kind':'file','name':doc.filename,'file_id':ident,'size':len(doc.data),
                'sha256':hashlib.sha256(doc.data).hexdigest(),'download':f'/api/sky/files/{ident}'}
    if action=='experience':
        spec=_design_from_params(task,params)
        now=_now()
        with _conn() as c:
            c.execute('INSERT INTO experiences VALUES(?,?,?,?)',(ident,spec['title'],_json(spec,70000),now))
        return {'kind':'experience','id':ident,'title':spec['title'],'preview_url':f'/api/sky/experiences/{ident}/html',
                'json_url':f'/api/sky/experiences/{ident}'}
    if action=='memory':
        label=str(params.get('label','Nota de SKY'))[:100]
        content=str(params.get('content','')).strip()
        if not 1<=len(content)<=3000:raise ValueError('El contenido de memoria debe tener entre 1 y 3000 caracteres')
        with _conn() as c:
            c.execute('INSERT INTO personal_notes VALUES(?,?,?,?)',(ident,label,content,_now()))
        return {'kind':'memory','id':ident,'label':label}
    raise ValueError('Acción desconocida')

def execute_item(ident:str,approve:bool=False):
    if not approve:raise PermissionError('Confirmá esta acción explícitamente')
    item=get_item(ident)
    if not item:raise KeyError('Tarea inexistente')
    if item['status']!='pendiente':raise RuntimeError('La tarea ya se ejecutó o está en proceso')
    # Compare and swap previene duplicaciones durante solicitudes concurrentes.
    with _conn() as c:
        cursor=c.execute("UPDATE work_items SET status='ejecutando',updated_at=? WHERE id=? AND status='pendiente'",(_now(),ident))
        if not cursor.rowcount:raise RuntimeError('Tarea en proceso o ya completada')
        _audit(c,'approved',ident,{'action':item['action']})
    try:
        result=_apply(item['task'],item['action'],item['params'],ident)
    except Exception as exc:
        with _conn() as c:
            c.execute('UPDATE work_items SET status=?,error=?,updated_at=? WHERE id=?',
                       ('error',str(exc)[:250],_now(),ident))
            _audit(c,'failed',ident,{'error_type':type(exc).__name__})
        raise
    with _conn() as c:
        c.execute('UPDATE work_items SET status=?,output=?,updated_at=? WHERE id=?',
                  ('completada',_json(result),_now(),ident))
        _audit(c,'completed',ident,{'kind':result['kind']})
    return get_item(ident)

def read_file(ident):
    item=get_item(ident)
    if not item or item['status']!='completada' or not item['output'] or item['output'].get('kind')!='file':
        raise KeyError('Archivo no encontrado')
    files=[p for p in _folder().iterdir() if p.is_file() and p.name.startswith(ident+'_')]
    if len(files)!=1:raise KeyError('Archivo no disponible')
    from .sky_office import FORMATS
    file=files[0];ext=file.suffix.lstrip('.')
    return file,FORMATS.get(ext,('archivo','application/octet-stream'))[1]

def list_notes():
    with _conn() as c:return [dict(r) for r in c.execute('SELECT * FROM personal_notes ORDER BY created_at DESC LIMIT 100')]

def forget_note(ident):
    with _conn() as c:
        n=c.execute('DELETE FROM personal_notes WHERE id=?',(ident,)).rowcount
        if n:_audit(c,'memory_deleted',ident)
    return bool(n)

def get_experience(ident):
    with _conn() as c:row=c.execute('SELECT * FROM experiences WHERE id=?',(ident,)).fetchone()
    return json.loads(row['spec']) if row else None

def list_experiences():
    with _conn() as c:return [dict(r) for r in c.execute('SELECT id,title,created_at FROM experiences ORDER BY created_at DESC LIMIT 100')]

def audit_events(limit=35):
    with _conn() as c:return [dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT ?',(max(1,min(100,limit)),))]
