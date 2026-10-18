"""SKY Project Hub v9.2 — persistencia local y continuidad entre módulos.

Todos los proyectos son privados al propietario de la API. No se publican en
la comunidad, ni se sincronizan en la nube por defecto. Cualquier referencia
ligada a un proyecto se resuelve bajo autenticación en workspace_api.
"""
from __future__ import annotations
import os, json, sqlite3, uuid, io, zipfile, re
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]

def db_path():
    return Path(os.getenv('SKY_PROJECTS_DB') or ROOT/'local_data'/'sky_projects.sqlite3')

def _now():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def _connection():
    p=db_path();p.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(p,timeout=15)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=15000')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS projects(
      id TEXT PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'activo',version INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS links(
      id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      kind TEXT NOT NULL,ref TEXT NOT NULL,label TEXT NOT NULL,created_at TEXT NOT NULL,
      UNIQUE(project_id,kind,ref));
    CREATE TABLE IF NOT EXISTS project_messages(
      id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      role TEXT NOT NULL CHECK(role IN ('user','assistant')),provider TEXT NOT NULL,
      content TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS project_notes(
      id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      title TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_links_project ON links(project_id,created_at);
    CREATE INDEX IF NOT EXISTS idx_messages_project ON project_messages(project_id,id);
    ''')
    return db

def _validate(text,limit,label,minimum=1):
    if not isinstance(text,str) or len(text.strip())<minimum or len(text)>limit:
        raise ValueError(f'{label}: se requieren entre {minimum} y {limit} caracteres')
    return text.strip()

def create_project(title,description=''):
    title=_validate(title,120,'Título')
    description=_validate(description,3000,'Descripción',0)
    ident='prj_'+uuid.uuid4().hex[:20]; now=_now()
    with _connection() as db:
        db.execute('INSERT INTO projects VALUES(?,?,?,?,?,?,?)',(ident,title,description,'activo',1,now,now))
    return project(ident)

def project(pid):
    with _connection() as db:r=db.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
    return dict(r) if r else None

def list_projects():
    with _connection() as db:
        rows=db.execute('SELECT p.*, (SELECT count(*) FROM links l WHERE l.project_id=p.id) AS linked_items '
                        'FROM projects p ORDER BY p.updated_at DESC LIMIT 150').fetchall()
    return [dict(r) for r in rows]

def update_project(pid,title,description,expected_version):
    title=_validate(title,120,'Título');description=_validate(description,3000,'Descripción',0)
    with _connection() as db:
        cur=db.execute('UPDATE projects SET title=?,description=?,version=version+1,updated_at=? WHERE id=? AND version=?',
                       (title,description,_now(),pid,expected_version))
        if cur.rowcount!=1:
            if db.execute('SELECT 1 FROM projects WHERE id=?',(pid,)).fetchone():raise RuntimeError('Versión desactualizada: recargá el proyecto')
            raise KeyError('Proyecto no encontrado')
    return project(pid)

def link(pid,kind,ref,label):
    if kind not in {'task','world','experience','creative'}:raise ValueError('Tipo de enlace no permitido')
    ref=_validate(ref,96,'Referencia')
    label=_validate(label,160,'Nombre')
    with _connection() as db:
        if not db.execute('SELECT 1 FROM projects WHERE id=?',(pid,)).fetchone():raise KeyError('Proyecto no encontrado')
        db.execute('INSERT OR IGNORE INTO links VALUES(?,?,?,?,?,?)',
                   ('lnk_'+uuid.uuid4().hex[:18],pid,kind,ref,label,_now()))
        db.execute('UPDATE projects SET updated_at=? WHERE id=?',(_now(),pid))
    return links(pid)

def unlink(pid,link_id):
    with _connection() as db:cur=db.execute('DELETE FROM links WHERE id=? AND project_id=?',(link_id,pid))
    return cur.rowcount>0

def links(pid):
    with _connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM links WHERE project_id=? ORDER BY created_at,id',(pid,))]

def add_note(pid,title,content):
    title=_validate(title,120,'Título de nota');content=_validate(content,6000,'Contenido')
    with _connection() as db:
        if not db.execute('SELECT 1 FROM projects WHERE id=?',(pid,)).fetchone():raise KeyError('Proyecto no encontrado')
        ident='note_'+uuid.uuid4().hex[:16]
        db.execute('INSERT INTO project_notes VALUES(?,?,?,?,?)',(ident,pid,title,content,_now()))
    return {'id':ident,'title':title,'content':content}

def notes(pid):
    with _connection() as db:return [dict(r) for r in db.execute('SELECT * FROM project_notes WHERE project_id=? ORDER BY created_at DESC LIMIT 100',(pid,))]

def delete_note(pid,nid):
    with _connection() as db:cur=db.execute('DELETE FROM project_notes WHERE project_id=? AND id=?',(pid,nid))
    return cur.rowcount>0

def add_exchange(pid,user,assistant,provider):
    user=_validate(user,6000,'Mensaje del usuario');assistant=_validate(assistant[:16000],16000,'Respuesta SKY')
    provider=_validate(provider,30,'Proveedor')
    with _connection() as db:
        if not db.execute('SELECT 1 FROM projects WHERE id=?',(pid,)).fetchone():raise KeyError('Proyecto no encontrado')
        now=_now()
        db.execute('INSERT INTO project_messages(project_id,role,provider,content,created_at) VALUES(?,?,?,?,?)',(pid,'user',provider,user,now))
        db.execute('INSERT INTO project_messages(project_id,role,provider,content,created_at) VALUES(?,?,?,?,?)',(pid,'assistant',provider,assistant,now))

def messages(pid,limit=40):
    with _connection() as db:
        rows=db.execute('SELECT * FROM (SELECT * FROM project_messages WHERE project_id=? ORDER BY id DESC LIMIT ?) ORDER BY id ASC',
                        (pid,max(1,min(100,int(limit))))).fetchall()
    return [dict(r) for r in rows]

def clear_messages(pid):
    with _connection() as db:cur=db.execute('DELETE FROM project_messages WHERE project_id=?',(pid,))
    return cur.rowcount

def brief(pid):
    p=project(pid)
    if not p:raise KeyError('Proyecto no encontrado')
    # Sólo metadatos. El usuario selecciona si desea compartirlo con un proveedor externo.
    items=links(pid)
    from .sky_workbench import get_item
    from metaverse.store import get_world
    from .sky_workbench import get_experience
    state=[]
    for item in items[:100]:
        val={'id':item['id'],'kind':item['kind'],'ref':item['ref'],'label':item['label']}
        if item['kind']=='task':
            task=get_item(item['ref'])
            val.update(status=task['status'] if task else 'no_disponible',
                       output_kind=(task.get('output') or {}).get('kind') if task else None)
        if item['kind']=='world':val.update(status='disponible' if get_world(item['ref']) else 'no_disponible')
        if item['kind']=='experience':val.update(status='disponible' if get_experience(item['ref']) else 'no_disponible')
        if item['kind']=='creative':
            from .sky_creative import get_project as creative_project
            val.update(status='disponible' if creative_project(item['ref']) else 'no_disponible')
        state.append(val)
    return {'project':p,'items':state,'notes_count':len(notes(pid)),
            'messages_count':len(messages(pid,100))}

def context(pid):
    obj=brief(pid)
    p=obj['project']
    lines=[f'Proyecto: {p["title"]}',f'Objetivo: {p["description"][:800]}',
           'Entregables asociados: '+', '.join(x['label'][:75]+' ('+str(x.get('status',''))+')' for x in obj['items'][-14:])]
    return '\n'.join(lines)[:2600]

def _safe_filename(name):
    result=re.sub(r'[^a-zA-Z0-9_\-.]','_',name)[:100]
    return result.strip('._') or 'resultado'

def export_zip(pid):
    """ZIP de resultados realmente existentes. No incluye historial de chat, claves ni notas."""
    info=brief(pid); p=info['project']
    result=io.BytesIO();manifest={'format':'sky-project-v1','project':p,'items':[],'notice':'No incluye conversaciones ni notas privadas.'}
    from .sky_workbench import get_item,read_file,get_experience
    from .sky_experience import experience_html
    from metaverse.store import get_world
    # Quotas previenen descargas incontrolables desde referencias modificadas.
    total=0;max_total=45*1024*1024
    with zipfile.ZipFile(result,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for index,item in enumerate(info['items'][:80],1):
            ref=item['ref'];kind=item['kind'];meta={'kind':kind,'label':item['label'],'ref':ref,'status':item.get('status')}
            data=None; name=None; extras=[]
            if kind=='task':
                task=get_item(ref)
                if task and task['status']=='completada' and (task.get('output') or {}).get('kind')=='file':
                    try:
                        path,_=read_file(ref)
                        if path.stat().st_size>max_total-total:raise ValueError('El proyecto supera el límite de exportación de 45 MB')
                        data=path.read_bytes();name=path.name
                    except (KeyError,FileNotFoundError):meta['status']='archivo_no_disponible'
                elif task and task['status']=='completada' and (task.get('output') or {}).get('kind')=='experience':
                    spec=get_experience(ref)
                    if spec:
                        data=experience_html(spec).encode('utf-8');name='experience.html'
                        extras.append(('experience_spec.json',json.dumps(spec,ensure_ascii=False,indent=2).encode('utf-8')))
                elif task and task['status']=='completada' and (task.get('output') or {}).get('kind')=='world':
                    world=get_world(task['output']['world_id'])
                    if world:
                        data=json.dumps(world,ensure_ascii=False,indent=2).encode();name='world.json'
                        try:
                            from metaverse.export3d import export_scene_glb
                            extras.append(('world.glb',export_scene_glb(world['scene'])))
                        except (ImportError,ValueError):meta['glb']='no_disponible'
            elif kind=='experience':
                spec=get_experience(ref)
                if spec:
                    data=experience_html(spec).encode();name='experience.html'
                    extras.append(('experience_spec.json',json.dumps(spec,ensure_ascii=False,indent=2).encode('utf-8')))
            elif kind=='world':
                world=get_world(ref)
                if world:
                    data=json.dumps(world,ensure_ascii=False,indent=2).encode();name='world.json'
                    try:
                        from metaverse.export3d import export_scene_glb
                        extras.append(('world.glb',export_scene_glb(world['scene'])))
                    except (ImportError,ValueError):meta['glb']='no_disponible'
            elif kind=='creative':
                from .sky_creative import get_project as creative_project,exports as creative_exports,asset_path as creative_asset_path
                creative=creative_project(ref)
                if creative:
                    data=json.dumps({'name':creative['name'],'kind':creative['kind'],'spec':creative['spec'],'version':creative['version']},ensure_ascii=False,indent=2).encode()
                    name='creative_project.json'
                    for ex in creative_exports(ref)[-6:]:
                        try:
                            path, asset=creative_asset_path(ex['asset_id'])
                            # Medios demasiado grandes se exportan individualmente desde Creative Studio.
                            if path.stat().st_size+total<=max_total:
                                extras.append((f'export_{ex["id"][-8:]}{path.suffix}',path.read_bytes()))
                        except (KeyError,FileNotFoundError):pass
            if data is not None:
                total+=len(data)
                if total>max_total:raise ValueError('El proyecto supera el límite de exportación de 45 MB')
                pathname=f'entregables/{index:02d}_{_safe_filename(item["label"])}_{_safe_filename(name)}'
                z.writestr(pathname,data)
                meta['path']=pathname
            for suffix,extra_bytes in extras:
                total+=len(extra_bytes)
                if total>max_total:raise ValueError('El proyecto supera el límite de exportación de 45 MB')
                extra_path=f'entregables/{index:02d}_{_safe_filename(item["label"])}_{suffix}'
                z.writestr(extra_path,extra_bytes)
                meta.setdefault('extra_paths',[]).append(extra_path)
            manifest['items'].append(meta)
        z.writestr('proyecto.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    return result.getvalue(),_safe_filename(p['title'])+'.zip'
