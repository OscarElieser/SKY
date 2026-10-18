"""Persistencia SQLite simple: dueño único y versiones para prevenir sobrescrituras."""
from __future__ import annotations
import json, sqlite3, os, uuid, threading
from pathlib import Path
from datetime import datetime, timezone
from .engine import generate_scene,validate_object

_lock=threading.RLock()

def path_db()->Path:
    return Path(os.environ.get('SKY_METAVERSE_DB',str(Path(__file__).resolve().parent.parent/'local_data'/'sky_metaverse.sqlite3')))

def connect():
    p=path_db();p.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(str(p),timeout=5)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA busy_timeout=5000')
    con.execute('CREATE TABLE IF NOT EXISTS worlds (id TEXT PRIMARY KEY, name TEXT NOT NULL, scene TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)')
    con.commit()
    return con

def utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def get_world(wid:str):
    with _lock, connect() as db:
        row=db.execute('SELECT * FROM worlds WHERE id=?',(wid,)).fetchone()
        if row is None:return None
        return {**dict(row),'scene':json.loads(row['scene'])}

def list_worlds():
    with _lock,connect() as db:
        return [dict(x) for x in db.execute('SELECT id,name,version,created_at,updated_at FROM worlds ORDER BY updated_at DESC').fetchall()]

def create_world(name,prompt,seed=42):
    if not 1<=len(name.strip())<=65:raise ValueError('El nombre debe tener entre 1 y 65 caracteres')
    scene=generate_scene(prompt,seed)
    wid=uuid.uuid4().hex;now=utc()
    with _lock,connect() as db:
        db.execute('INSERT INTO worlds (id,name,scene,version,created_at,updated_at) VALUES (?,?,?,?,?,?)',
                   (wid,name.strip(),json.dumps(scene,ensure_ascii=False),1,now,now))
        db.commit()
    return get_world(wid)

def save_scene(wid,scene,expected_version:int):
    if not isinstance(scene,dict) or len(scene.get('objects',[]))>180:raise ValueError('Escena supera 180 objetos')
    obj=scene.get('objects',[])
    if not isinstance(obj,list):raise ValueError('Lista de objetos inválida')
    scene={**scene,'objects':[validate_object(x) for x in obj]}
    if len({x['id'] for x in scene['objects']})!=len(scene['objects']):raise ValueError('IDs de piezas duplicados')
    # Scene metadata cannot inject script into browser; user labels rendered via textContent.
    scene['theme']=str(scene.get('theme','estudio'))[:32]
    scene['prompt']=str(scene.get('prompt',''))[:1000]
    with _lock,connect() as db:
        cur=db.execute('UPDATE worlds SET scene=?,version=version+1,updated_at=? WHERE id=? AND version=?',
                       (json.dumps(scene,ensure_ascii=False),utc(),wid,expected_version))
        db.commit()
        if cur.rowcount!=1:
            if get_world(wid) is None:raise KeyError('Mundo no existe')
            raise RuntimeError('Escena cambiada por otra sesión. Recargá antes de guardar.')
    return get_world(wid)

def delete_world(wid):
    with _lock,connect() as db:
        cur=db.execute('DELETE FROM worlds WHERE id=?',(wid,));db.commit()
        return cur.rowcount>0

def demo_world():
    worlds=list_worlds()
    if worlds:return worlds[0]['id']
    return create_world('SKY Central — Mi Universo','Laboratorio de creación 3D, innovación, educación y negocios',42)['id']
