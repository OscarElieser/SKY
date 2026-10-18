"""Experiencia persistente de SKY: feedback, metas y cambios versionados.

Aprende preferencias declaradas y registra evaluaciones; NO modifica su propio código
ni se actualiza automáticamente sin revisión/ejecución humana.
"""
from pathlib import Path
from datetime import datetime,timezone
import json, sqlite3, os

DB_ENV='SKY_EVOLUTION_DB'

def path_db():
    p=Path(os.getenv(DB_ENV,Path(__file__).resolve().parents[1]/'data'/'sky_evolution.sqlite3'))
    p.parent.mkdir(parents=True,exist_ok=True)
    return p

def _conn():
    c=sqlite3.connect(path_db(),timeout=10)
    c.row_factory=sqlite3.Row
    c.executescript('''
    CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, module TEXT NOT NULL, score INTEGER NOT NULL,
      note TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, title TEXT NOT NULL, metric TEXT NOT NULL,
      target REAL NOT NULL, actual REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS improvements (id INTEGER PRIMARY KEY, title TEXT NOT NULL, proposal TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pendiente', created_at TEXT NOT NULL);
    ''')
    return c

def feedback(modulo:str,nota:int,comentario:str):
    if nota not in (1,2,3,4,5):raise ValueError('Calificación 1 a 5')
    if not (modulo or '').strip(): raise ValueError('Módulo vacío')
    with _conn() as c: c.execute('INSERT INTO feedback(module,score,note,created_at) VALUES(?,?,?,?)',
        (modulo.strip()[:80],nota,comentario.strip()[:1200],datetime.now(timezone.utc).isoformat()))

def feedback_resumen():
    with _conn() as c:return [dict(row) for row in c.execute(
      'SELECT module, COUNT(*) AS evaluaciones, ROUND(AVG(score),2) AS promedio FROM feedback GROUP BY module ORDER BY evaluaciones DESC')]

def nueva_meta(titulo:str,metrica:str,objetivo:float):
    if not titulo.strip() or not metrica.strip() or objetivo<=0 or objetivo>1e12:raise ValueError('Meta inválida')
    with _conn() as c:c.execute('INSERT INTO goals(title,metric,target,updated_at) VALUES(?,?,?,?)',
       (titulo[:120],metrica[:50],objetivo,datetime.now(timezone.utc).isoformat()))

def metas():
    with _conn() as c:return [dict(r) for r in c.execute('SELECT * FROM goals ORDER BY id DESC LIMIT 100')]

def actualizar_meta(id:int,valor:float):
    if valor<0 or valor>1e12:raise ValueError('Valor inválido')
    with _conn() as c:
        cursor=c.execute('UPDATE goals SET actual=?, updated_at=? WHERE id=?',
            (valor,datetime.now(timezone.utc).isoformat(),id))
        if cursor.rowcount!=1:raise ValueError('Meta inexistente')

def proponer_mejora(titulo:str,propuesta:str):
    if not titulo.strip() or len(propuesta.strip())<12:raise ValueError('Describí la mejora')
    with _conn() as c:c.execute('INSERT INTO improvements(title,proposal,created_at) VALUES(?,?,?)',
       (titulo[:150],propuesta[:4000],datetime.now(timezone.utc).isoformat()))

def mejoras():
    with _conn() as c:return [dict(r) for r in c.execute('SELECT * FROM improvements ORDER BY id DESC LIMIT 100')]

def cambiar_mejora(id:int,estado:str):
    if estado not in {'pendiente','aprobada_para_desarrollo','descartada','implementada_verificada'}:
        raise ValueError('Estado no permitido')
    with _conn() as c:
        cursor=c.execute('UPDATE improvements SET status=? WHERE id=?',(estado,id))
        if cursor.rowcount!=1:raise ValueError('Mejora inexistente')


def feedback_reciente(limit:int=6):
    with _conn() as c:
        return [dict(r) for r in c.execute('SELECT module,score,note FROM feedback ORDER BY id DESC LIMIT ?', (min(10,max(1,limit)),))]
