"""SKY Intelligent Workspace v9.5.

Orquesta herramientas locales preexistentes mediante una conversación privada.
Plan local verificable -> aprobación explícita -> flujo duradero de v9.4.
No inventa investigaciones, no invoca modelos en secreto y nunca realiza pagos.
"""
from __future__ import annotations
import hashlib
import csv
import io
import unicodedata
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def db_path():
    return Path(os.getenv('SKY_INTELLIGENT_DB') or ROOT/'local_data'/'sky_intelligent.sqlite3')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connect():
    path=db_path(); path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15,isolation_level=None)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA busy_timeout=15000')
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS intelligent_requests (
        id TEXT PRIMARY KEY, user_request TEXT NOT NULL, title TEXT NOT NULL,
        project_id TEXT, stages TEXT NOT NULL, status TEXT NOT NULL,
        flow_id TEXT, fingerprint TEXT NOT NULL, error TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS ix_intelligent_status ON intelligent_requests(status,created_at);
      CREATE TABLE IF NOT EXISTS intelligent_revisions (
        id TEXT PRIMARY KEY, request_id TEXT NOT NULL, project_id TEXT NOT NULL,
        source_item_id TEXT NOT NULL, action TEXT NOT NULL,
        instruction TEXT NOT NULL, source_snapshot TEXT NOT NULL,
        spec TEXT NOT NULL, fingerprint TEXT NOT NULL, status TEXT NOT NULL,
        result_item_id TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      );
    ''')
    return db


def _row(row):
    if not row:return None
    data=dict(row)
    data['stages']=json.loads(data['stages'])
    return data


def get(ident):
    with connect() as db:
        return _row(db.execute('SELECT * FROM intelligent_requests WHERE id=?',(ident,)).fetchone())


def recent(limit=20):
    with connect() as db:
        return [_row(r) for r in db.execute('SELECT * FROM intelligent_requests ORDER BY created_at DESC LIMIT ?', (max(1,min(50,int(limit))),))]


def _title(message):
    cleaned=re.sub(r'^(sky[, :!]*|por favor\s+|quiero que\s+|necesito que\s+|cre[aá](?:me)?\s+|prepar[aá](?:me)?\s+|haz(?:me)?\s+)', '', message.strip(),flags=re.I)
    cleaned=re.sub(r'\s+', ' ', cleaned).strip(' .,:;')
    cleaned=cleaned or 'Nuevo proyecto SKY'
    return cleaned if len(cleaned)<=76 else cleaned[:76].rsplit(' ',1)[0]


def _plain(value):
    """Normalización para clasificar intención; el mensaje original nunca se pierde."""
    return ''.join(char for char in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(char))


def creation_intent(message):
    """Detecta solicitudes de creación explícitas, nunca preguntas exploratorias."""
    s=_plain(message).strip()
    if '?' in s or s.startswith(('como ', 'que ', 'por que ', 'puedo ', 'podria ', 'es posible ')):
        return False
    commands=('crea','creame','crear','construye','disena','disename','prepara','preparame',
              'haz','hazme','hace','genera','desarrolla','elabora','produce','arma','armame',
              'necesito crear','quiero crear','quiero que hagas','quiero que crees',
              'ayudame a crear','quisiera elaborar','elaborame','redacta','redactame')
    deliverables=('proyecto','presentacion','powerpoint','documento','word','pdf','excel','mundo',
                  'metaverso','escenario','sitio web','pagina web','landing','interfaz','diseno',
                  'academia','experiencia','curso','informe','material didactico','diapositiva',
                  'hoja de calculo','reporte','propuesta','sitio','pagina')
    return any(re.search(r'(?<!\w)'+re.escape(verb)+r'(?!\w)',s) for verb in commands) and any(term in s for term in deliverables)


def _context_brief(message, project_id=None):
    """Resume datos aportados, sin inferir cifras, fuentes o capacidades inexistentes."""
    normalized=_plain(message)
    audience=[]
    for term in ('ninos','jovenes','adultos','docentes','estudiantes','turistas','emprendedores','familias','clientes'):
        if re.search(r'(?<!\w)'+term+r'(?!\w)',normalized):audience.append(term)
    purpose=[]
    for term in ('educacion','turismo','negocios','ventas','salud','cultura','historia','ciencia','tecnologia','medio ambiente','musica'):
        if term in normalized:purpose.append(term)
    info={'objetivo':message.strip()[:3200],'publico_mencionado':audience,'areas_mencionadas':purpose,
          'suposiciones':'No hay datos externos verificados en la propuesta. Las cifras no proporcionadas quedan pendientes.'}
    if project_id:
        from .sky_projects import project,brief
        prj=project(project_id)
        if not prj:raise KeyError('Proyecto no encontrado')
        info['proyecto_existente']={'titulo':prj['title'],'descripcion':prj['description'][:600],
                                     'entregables_preexistentes':[(x['kind'],x['label']) for x in brief(project_id)['items'][-12:]]}
    return info


def _doc_content(message,title,brief,world_step=None):
    """Borrador útil por secciones; datos exclusivamente de la instrucción original."""
    target=', '.join(brief['publico_mencionado']) or 'Por definir con el usuario'
    fields=', '.join(brief['areas_mencionadas']) or 'A especificar'
    world=f'\nMundo 3D vinculado: {{{{step.{world_step}.world_id}}}}\n' if world_step else ''
    return (f'PROPUESTA INICIAL EDITABLE · BORRADOR CONTEXTUAL\n\n'
            f'## 1. Objetivo y contexto\n{message.strip()[:2600]}\n\n'
            f'## 2. Destinatarios\n{target}. Este apartado recoge únicamente destinatarios mencionados explícitamente.\n\n'
            f'## 3. Ejes de contenido\n{fields}. Deben validarse con las fuentes y requisitos del proyecto.\n\n'
            f'## 3A. Continuidad del proyecto\n{brief.get("proyecto_existente",{}).get("descripcion","Proyecto nuevo, sin antecedentes asociados.")[:600]}\n'
            f'Resultados previos: {str(brief.get("proyecto_existente",{}).get("entregables_preexistentes",[]))[:600]}\n\n'
            f'## 4. Entregables y organización\nProyecto: {{{{project.title}}}}. '
            f'SKY agrupa los resultados en el mismo espacio y conserva sus versiones.\n{world}\n'
            f'## 5. Propuesta de desarrollo\n- Revisar el objetivo y los criterios de calidad con el solicitante.\n'
            f'- Completar información, ejemplos y materiales específicos.\n'
            f'- Diseñar y comprobar la experiencia del usuario.\n'
            f'- Verificar accesibilidad, exactitud y coherencia de cada entregable.\n\n'
            f'## 6. Control de calidad y pendientes\n- Validar contenido especializado y referencias.\n'
            f'- Confirmar datos no proporcionados y recursos disponibles.\n'
            f'- Revisar esta versión antes de su publicación.\n\n'
            f'Este documento es un borrador estructurado, no investigación independiente ni material certificado.')


def _parse_inline_csv(message):
    """Admite ```csv ...``` en el mensaje; sin fabricar filas."""
    match=re.search(r'```csv\s*\n([\s\S]*?)```',message,re.I)
    if not match:return None
    text=match.group(1)
    if len(text)>15000:raise ValueError('Tabla demasiado extensa para este flujo')
    rows=list(csv.reader(io.StringIO(text)))
    if len(rows)<2 or not rows[0] or len(rows[0])>20 or len(rows)>200:
        raise ValueError('CSV: enviá encabezados y al menos una fila (máximo 20 columnas y 199 filas)')
    if any(len(row)>len(rows[0]) for row in rows[1:]):raise ValueError('CSV: filas con más columnas que el encabezado')
    return {'headers':rows[0],'rows':rows[1:]}

def _doc_kind(message):
    s=message.casefold()
    if 'powerpoint' in s or 'presentación' in s or 'diapositiva' in s:return 'pptx'
    if 'pdf' in s:return 'pdf'
    # Excel no se genera sin datos estructurados: no inventar cifras.
    if 'excel' in s or 'hoja de cálculo' in s:return 'xlsx'
    return 'docx'


def make_stages(message,title,project_id=None):
    s=_plain(message)
    brief=_context_brief(message,project_id)
    complete=any(x in s for x in ('proyecto completo','academia','experiencia completa','todo el proyecto'))
    include_world=complete or any(x in s for x in ('mundo','metaverso','escenario 3d','escenario virtual'))
    include_visual=complete or any(x in s for x in ('web','interfaz','landing','diseno','pantalla','visual'))
    include_document=complete or any(x in s for x in ('documento','word','pdf','excel','powerpoint','presentacion','informe','material didactico','hoja de calculo'))
    # En una edición de propuesta, la instrucción de retirar etapas tiene prioridad.
    include_world=include_world and not any(x in s for x in ('sin mundo 3d','sin mundo virtual','quita el mundo','elimina el mundo','no incluyas mundo'))
    include_visual=include_visual and not any(x in s for x in ('sin diseno web','quita el diseno','elimina el diseno','no incluyas web'))
    include_document=include_document and not any(x in s for x in ('sin documento','quita el documento','elimina el documento'))
    if not (include_world or include_visual or include_document) and not any(x in s for x in ('sin mundo','quita el mundo','sin documento','sin diseno')):include_visual=True
    kind=_doc_kind(message)
    dataset=_parse_inline_csv(message) if kind=='xlsx' else None
    if kind=='xlsx' and include_document and dataset is None:
        raise ValueError('Para Excel, incluí tus datos en un bloque ```csv ... ```; SKY no inventa cifras ni balances.')
    steps=[{'agent':'planificador','action':'plan','task':'Planificar el objetivo: '+message[:2400], 'params':{}}]
    if include_world:
        steps.append({'agent':'creador_3d','action':'world',
                      'task':'Crear mundo virtual inicial para: '+title,
                      'params':{'name':title[:60],'prompt':message[:950],'seed':42}})
    if include_visual:
        steps.append({'agent':'diseñador','action':'experience',
                      'task':'Crear diseño visual editable para: '+message[:2100], 'params':{}})
    if include_document:
        spec={'kind':kind,'title':title,'content':_doc_content(message,title,brief,2 if include_world else None),'ai_provider':'none'}
        if dataset:spec.update(dataset)
        steps.append({'agent':'documentalista','action':'document',
                      'task':'Preparar borrador editable de {{project.title}} usando etapas anteriores',
                      'params':{'document':spec}})
    return steps

def _fingerprint(request,title,project_id,stages):
    payload=json.dumps({'request':request,'title':title,'project_id':project_id,'stages':stages},
                       ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def prepare(message,project_id=None):
    if not isinstance(message,str) or not 8<=len(message.strip())<=5000:raise ValueError('Describí el objetivo entre 8 y 5000 caracteres')
    if project_id is not None:
        from .sky_projects import project
        if not project(project_id):raise KeyError('Proyecto no encontrado')
    title=_title(message)
    stages=make_stages(message,title,project_id)
    from .sky_workflows import _valid_step, _validate_tokens
    stages=[_valid_step(step) for step in stages]
    # El proyecto se crea después de la aprobación y permite referencias project.*.
    _validate_tokens(stages, project_id or 'pending_owner_project')
    digest=_fingerprint(message,title,project_id,stages)
    ident='skyreq_'+uuid.uuid4().hex[:20]
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('''INSERT INTO intelligent_requests
                     (id,user_request,title,project_id,stages,status,fingerprint,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?)''',
                   (ident,message.strip(),title,project_id,json.dumps(stages,ensure_ascii=False),
                    'awaiting_approval',digest,now(),now()))
        db.commit()
    return get(ident)


def revise_plan(ident, expected_fingerprint, instructions):
    """Edita SOLO propuestas no aprobadas; regeneración optimista y validada."""
    if not isinstance(instructions,str) or not 8<=len(instructions.strip())<=1500:
        raise ValueError('Indicá qué cambios querés entre 8 y 1500 caracteres')
    data=get(ident)
    if not data:raise KeyError('Solicitud no encontrada')
    if data['status']!='awaiting_approval' or data['fingerprint']!=expected_fingerprint:
        raise RuntimeError('La propuesta fue modificada o ya tiene aprobación')
    # Se conserva instrucción anterior para que las restricciones no desaparezcan.
    proposed=data['user_request'].strip()+'\nRequisitos adicionales del creador: '+instructions.strip()
    if len(proposed)>5000:raise ValueError('La propuesta supera 5000 caracteres')
    stages=make_stages(proposed,data['title'],data['project_id'])
    from .sky_workflows import _valid_step,_validate_tokens
    stages=[_valid_step(step) for step in stages]
    _validate_tokens(stages,data['project_id'] or 'pending_owner_project')
    digest=_fingerprint(proposed,data['title'],data['project_id'],stages)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        updated=db.execute("""UPDATE intelligent_requests SET user_request=?,stages=?,fingerprint=?,updated_at=?
              WHERE id=? AND status='awaiting_approval' AND fingerprint=?""",
              (proposed,json.dumps(stages,ensure_ascii=False),digest,now(),ident,expected_fingerprint)).rowcount
        db.commit()
    if not updated:raise RuntimeError('Conflicto de versión: revisá el plan actualizado')
    return status(ident)


def _revision_snapshot(source):
    """Localiza el artefacto existente como tarea finalizada, sin aceptar IDs arbitrarios."""
    from .sky_workbench import get_item
    item=get_item(source)
    if not item or item['status']!='completada' or item['action'] not in ('document','experience','world'):
        raise KeyError('Entregable no encontrado o no editable')
    return item


def prepare_revision(request_id,source_item_id,instruction):
    if not isinstance(instruction,str) or not 8<=len(instruction.strip())<=3000:
        raise ValueError('Especificá la edición entre 8 y 3000 caracteres')
    data=status(request_id)
    if not data['project_id'] or data['status']!='completed':
        raise ValueError('Para editar un entregable, primero completá el proyecto')
    source=_revision_snapshot(source_item_id)
    from .sky_projects import links
    output=source.get('output') or {}
    associated=(('world',output.get('world_id')) if source['action']=='world' else ('task' if source['action']=='document' else 'experience',source_item_id))
    if not any(x['kind']==associated[0] and x['ref']==associated[1] for x in links(data['project_id'])):
        raise PermissionError('Este entregable no pertenece al proyecto de la solicitud')
    action=source['action']
    params=source['params']
    if action=='document':
        original=params.get('document') or {}
        if original.get('kind') in ('xlsx','csv'):
            raise ValueError('Edición de tablas: utilizá Office Studio para proteger los datos y fórmulas')
        previous=original.get('content') or ''
        if len(previous)+len(instruction)>26000:raise ValueError('Documento demasiado largo para revisión de chat')
        params={'document':{**original,'content':previous+'\n\n## Revisión solicitada\n'+instruction.strip(),
                            'title':str(original.get('title','Documento SKY'))[:125]+' — revisión','ai_provider':'none'}}
        task='Revisión de documento solicitada: '+instruction.strip()
    elif action=='experience':
        task='Revisar diseño visual: '+source['task'][:1200]+'; cambios: '+instruction.strip()
        params={} # crea un diseño nuevo, no altera la versión original.
    else:
        params={**params,'name':(str(params.get('name','Mundo SKY'))[:43]+' - revisión')[:65],
                'prompt':(str(params.get('prompt',''))[:650]+'; cambios: '+instruction.strip())[:1000]}
        task='Revisar mundo 3D: '+instruction.strip()
    payload={'request_id':request_id,'source':source_item_id,'action':action,'task':task,'params':params}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    ident='skyrev_'+uuid.uuid4().hex[:20]
    with connect() as db:
        db.execute("""INSERT INTO intelligent_revisions
          (id,request_id,project_id,source_item_id,action,instruction,source_snapshot,spec,fingerprint,status,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
          (ident,request_id,data['project_id'],source_item_id,action,instruction.strip(),
           json.dumps({'output':source['output'],'action':action},ensure_ascii=False),
           json.dumps(payload,ensure_ascii=False),digest,'awaiting_approval',now(),now()))
    return revision(ident)


def revision(ident):
    with connect() as db:
        row=db.execute('SELECT * FROM intelligent_revisions WHERE id=?',(ident,)).fetchone()
    if not row:raise KeyError('Revisión inexistente')
    d=dict(row)
    d['spec']=json.loads(d['spec'])
    return d


def approve_revision(ident,fingerprint,approved):
    if not approved:raise PermissionError('Confirmá la revisión antes de ejecutarla')
    d=revision(ident)
    if d['fingerprint']!=fingerprint:raise RuntimeError('El borrador de edición cambió; revisalo')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        changed=db.execute("UPDATE intelligent_revisions SET status='executing',updated_at=? WHERE id=? AND status='awaiting_approval' AND fingerprint=?""",
                           (now(),ident,fingerprint)).rowcount
        db.commit()
    if not changed:raise RuntimeError('Esta revisión ya está ejecutada o necesita inspección')
    try:
        from .sky_workbench import create_item,execute_item
        from .sky_projects import link
        payload=d['spec']
        task=create_item(payload['task'],payload['action'],payload['params'])
        with connect() as db:
            db.execute('UPDATE intelligent_revisions SET result_item_id=?,updated_at=? WHERE id=?',(task['id'],now(),ident))
        result=execute_item(task['id'],True)
        link(d['project_id'],'task',task['id'],'Revisión · '+payload['task'][:100])
        with connect() as db:
            db.execute("UPDATE intelligent_revisions SET status='completed',updated_at=? WHERE id=?",(now(),ident))
    except Exception as exc:
        with connect() as db:
            db.execute('UPDATE intelligent_revisions SET status=?,error=?,updated_at=? WHERE id=?',
                       ('needs_review',type(exc).__name__,now(),ident))
        raise RuntimeError('Resultado incierto; revisá antes de repetir para evitar duplicados') from exc
    return revision(ident)

def approve(ident,expected_fingerprint,approved=False):
    if not approved:raise PermissionError('Se requiere aprobación explícita del creador')
    data=get(ident)
    if not data:raise KeyError('Solicitud no encontrada')
    if not expected_fingerprint or expected_fingerprint!=data['fingerprint']:
        raise RuntimeError('La propuesta no coincide con la aprobación presentada')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        affected=db.execute('''UPDATE intelligent_requests SET status='activating',updated_at=?
                               WHERE id=? AND status='awaiting_approval' ''',(now(),ident)).rowcount
        db.commit()
        if affected!=1:raise RuntimeError('La propuesta ya fue procesada o está en revisión')
    try:
        from . import sky_projects as ph
        from . import sky_workflows as wf
        pid=data['project_id']
        if pid is None:
            p=ph.create_project(data['title'],data['user_request'])
            pid=p['id']
            # Guardar inmediatamente para facilitar recuperación manual si ocurre una interrupción.
            with connect() as db:
                db.execute('UPDATE intelligent_requests SET project_id=?,updated_at=? WHERE id=?',(pid,now(),ident))
        flow=wf.create('SKY Workspace · '+data['title'][:95],data['stages'],pid)
        with connect() as db:
            db.execute('UPDATE intelligent_requests SET flow_id=?,updated_at=? WHERE id=?',(flow['id'],now(),ident))
        preview=wf.preview(flow['id'])
        wf.approve(flow['id'],preview['fingerprint'])
        ph.add_exchange(pid,data['user_request'],
                        'Proyecto preparado y flujo aprobado por el propietario. El motor local continuará las etapas.',
                        'sky-local')
        with connect() as db:
            db.execute("UPDATE intelligent_requests SET status='active',updated_at=? WHERE id=?",(now(),ident))
    except Exception as exc:
        with connect() as db:
            db.execute("UPDATE intelligent_requests SET status='needs_review',error=?,updated_at=? WHERE id=?",
                       (type(exc).__name__,now(),ident))
        raise RuntimeError('No se completó la activación; revisá la solicitud antes de repetir.') from exc
    return status(ident)


def status(ident):
    data=get(ident)
    if not data:raise KeyError('Solicitud no encontrada')
    flow=None; deliverables=[]; completion=0
    if data['flow_id']:
        from .sky_workflows import get as get_flow
        flow=get_flow(data['flow_id'])
        if flow:
            total=max(1,len(flow['steps']))
            completed=flow['current_step']
            if flow['status']=='completed':completed=total
            completion=round(completed*100/total)
            for row in flow['results']:
                if row['run']!=flow['run_number']:continue
                value=row.get('result') or {}
                k=value.get('kind')
                if k in ('world','experience','file','plan'):
                    deliverables.append({'step':row['step'],'kind':k,
                         'name':value.get('name') or value.get('title') or value.get('message') or k,
                         'download':value.get('download') if k=='file' else None,
                         'world_id':value.get('world_id') if k=='world' else None,
                         'design_id':value.get('id') if k=='experience' else None,
                         'item_id':row.get('item_id')})
    current=(flow['status'] if flow else data['status'])
    return {'id':ident,'name':data['title'],'status':current,'state':data['status'],
            'project_id':data['project_id'],'flow_id':data['flow_id'],'fingerprint':data['fingerprint'],
            'stages':[{'number':i,'action':stage['action'],'description':stage['task'].replace('{{project.title}}',data['title'])[:220]}
                      for i,stage in enumerate(data['stages'],1)],
            'completed_percent':completion,'deliverables':deliverables,
            'project_export':f"/api/sky/projects/{data['project_id']}/export.zip" if data['project_id'] else None,
            'error':flow.get('last_error') if flow else data['error'],
            'requires_approval':data['status']=='awaiting_approval',
            'dependencies':[{'step':i+1,'depends_on':[int(x.split('.')[1]) for x in sorted(set(__import__('neural_core.sky_workflows',fromlist=['_tokens'])._tokens(stage))) if x.startswith('step.')]} for i,stage in enumerate(data['stages'])],
            'local_only':True,'external_provider_used':False,
            'revisions':revisions_for_request(ident)}


def revisions_for_request(ident):
    with connect() as db:
        rows=db.execute('SELECT id FROM intelligent_revisions WHERE request_id=? ORDER BY created_at,id',(ident,)).fetchall()
    result=[]
    for row in rows:
        d=revision(row['id'])
        out=None
        if d.get('result_item_id'):
            from .sky_workbench import get_item
            item=get_item(d['result_item_id'])
            out=item.get('output') if item else None
        result.append({'id':d['id'],'status':d['status'],'action':d['action'],
                       'instruction':d['instruction'],'source_item_id':d['source_item_id'],
                       'item_id':d['result_item_id'],'result':out,'fingerprint':d['fingerprint'],
                       'error':d.get('error')})
    return result


def conversation(ident):
    data=get(ident)
    if not data:raise KeyError('Solicitud no encontrada')
    if not data['project_id']:return []
    from .sky_projects import messages
    return messages(data['project_id'])
