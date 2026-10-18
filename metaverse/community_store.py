"""Persistent, invitation-only multi-user community store for SKY.

Individual credentials are never stored in plaintext. This is a single-server
starter, not a general distributed social network service.
"""
from __future__ import annotations
import hashlib,hmac,json,os,re,secrets,sqlite3,threading,time,uuid
from pathlib import Path
from datetime import datetime,timezone

LOCK=threading.RLock()
HANDLE=re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{2,23}$')
COLORS={'aurora','coral','violeta','cielo','bosque','dorado'}


def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def db_path():return Path(os.getenv('SKY_COMMUNITY_DB',str(Path(__file__).resolve().parent.parent/'local_data'/'sky_community.sqlite3')))
def digest(token):return hashlib.sha256(token.encode('utf-8')).hexdigest()
def connect():
    p=db_path();p.parent.mkdir(exist_ok=True,parents=True)
    c=sqlite3.connect(p,timeout=8,check_same_thread=False)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA busy_timeout=5000')
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
      display_name TEXT NOT NULL, password_salt TEXT NOT NULL,password_hash TEXT NOT NULL,
      avatar TEXT NOT NULL DEFAULT 'cielo',bio TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS invites(code_hash TEXT PRIMARY KEY,created_at TEXT NOT NULL,expires_at INTEGER NOT NULL,used_by TEXT);
    CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      expires_at INTEGER NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS tickets(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,
      world_id TEXT NOT NULL,expires_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS published(world_id TEXT PRIMARY KEY,published_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,world_id TEXT NOT NULL,user_id TEXT NOT NULL REFERENCES users(id),
      body TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS messages_idx ON messages(world_id,created_at);
    CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      label TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS memories_user_idx ON memories(user_id,updated_at);
    CREATE TABLE IF NOT EXISTS feedback(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      topic TEXT NOT NULL,score INTEGER NOT NULL,comment TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS posts(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),
      body TEXT NOT NULL,world_id TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS likes(post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,PRIMARY KEY(post_id,user_id));
    CREATE TABLE IF NOT EXISTS follows(follower TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      followed TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,PRIMARY KEY(follower,followed));
    CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,reporter_id TEXT NOT NULL REFERENCES users(id),
      target_id TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT NOT NULL);
    ''')
    c.commit();return c


def issue_invite(hours=48):
    token=secrets.token_urlsafe(24)
    with LOCK,connect() as c:
        c.execute('INSERT INTO invites VALUES (?,?,?,NULL)',(digest(token),now(),int(time.time()+hours*3600)));c.commit()
    return token

def _pw_hash(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),350_000).hex()

def register(username,password,display_name,invite):
    username=username.strip().lower();display_name=display_name.strip()
    if not HANDLE.fullmatch(username):raise ValueError('Usuario: 3–24 letras, números o guion bajo; empieza por letra')
    if not (12<=len(password)<=128):raise ValueError('Contraseña: 12–128 caracteres')
    if not 2<=len(display_name)<=45:raise ValueError('Nombre visible: 2–45 caracteres')
    uid=uuid.uuid4().hex;salt=secrets.token_hex(16)
    with LOCK,connect() as c:
        invite_row=c.execute('SELECT expires_at,used_by FROM invites WHERE code_hash=?',(digest(invite),)).fetchone()
        if not invite_row or invite_row['used_by'] or invite_row['expires_at']<int(time.time()):raise PermissionError('Invitación no válida o caducada')
        try:
            c.execute('INSERT INTO users (id,username,display_name,password_salt,password_hash,created_at) VALUES (?,?,?,?,?,?)',
                (uid,username,display_name,salt,_pw_hash(password,salt),now()))
            c.execute('UPDATE invites SET used_by=? WHERE code_hash=? AND used_by IS NULL',(uid,digest(invite)))
            c.commit()
        except sqlite3.IntegrityError as exc:raise ValueError('Ese nombre de usuario ya existe') from exc
    return get_user(uid)

def _public(row):
    if not row:return None
    return {k:row[k] for k in ['id','username','display_name','avatar','bio','created_at']}

def get_user(uid):
    with connect() as c:return _public(c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone())

def login(username,password):
    with LOCK,connect() as c:
        row=c.execute('SELECT * FROM users WHERE username=?',(username.strip().lower(),)).fetchone()
        # Always compute a password hash, even if user does not exist.
        salt=row['password_salt'] if row else '0'*32
        candidate=_pw_hash(password,salt)
        if not row or not hmac.compare_digest(row['password_hash'],candidate):raise PermissionError('Credenciales incorrectas')
        token=secrets.token_urlsafe(40)
        c.execute('INSERT INTO sessions VALUES (?,?,?,?)',(digest(token),row['id'],int(time.time()+7*86400),now()));c.commit()
    return token,_public(row)

def user_from_token(token):
    if not token:return None
    with connect() as c:
        row=c.execute('''SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
           WHERE s.token_hash=? AND s.expires_at>?''',(digest(token),int(time.time()))).fetchone()
        return _public(row)

def logout(token):
    with LOCK,connect() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(digest(token),));c.commit()

def set_profile(uid,name,avatar,bio):
    if not 2<=len(name.strip())<=45:raise ValueError('Nombre visible inválido')
    if avatar not in COLORS:raise ValueError('Avatar no válido')
    if len(bio)>200:raise ValueError('Biografía supera 200 caracteres')
    with LOCK,connect() as c:c.execute('UPDATE users SET display_name=?,avatar=?,bio=? WHERE id=?',(name.strip(),avatar,bio.strip(),uid));c.commit()
    return get_user(uid)

def publish(wid,enabled):
    with LOCK,connect() as c:
        if enabled:c.execute('INSERT OR IGNORE INTO published VALUES (?,?)',(wid,now()))
        else:c.execute('DELETE FROM published WHERE world_id=?',(wid,))
        c.commit()

def is_published(wid):
    with connect() as c:return c.execute('SELECT 1 FROM published WHERE world_id=?',(wid,)).fetchone() is not None

def published_ids():
    with connect() as c:return [r['world_id'] for r in c.execute('SELECT world_id FROM published').fetchall()]

def issue_ticket(uid,wid):
    if not is_published(wid):raise PermissionError('Mundo no publicado')
    token=secrets.token_urlsafe(30)
    with LOCK,connect() as c:
        c.execute('INSERT INTO tickets VALUES (?,?,?,?)',(digest(token),uid,wid,int(time.time()+30)));c.commit()
    return token

def consume_ticket(wid,ticket):
    with LOCK,connect() as c:
        row=c.execute('SELECT * FROM tickets WHERE token_hash=?',(digest(ticket),)).fetchone()
        c.execute('DELETE FROM tickets WHERE token_hash=?',(digest(ticket),));c.commit()
        if row and row['world_id']==wid and row['expires_at']>=int(time.time()) and is_published(wid):return get_user(row['user_id'])
    return None

def save_message(wid,uid,body):
    body=body.strip()
    if not 1<=len(body)<=500:raise ValueError('Mensaje debe tener entre 1 y 500 caracteres')
    mid=uuid.uuid4().hex;ts=now()
    with LOCK,connect() as c:
        c.execute('INSERT INTO messages VALUES (?,?,?,?,?)',(mid,wid,uid,body,ts));c.commit()
    return {'id':mid,'world_id':wid,'user_id':uid,'body':body,'created_at':ts}

def message_history(wid,limit=60):
    with connect() as c:
        rows=c.execute('''SELECT m.id,m.body,m.created_at,u.username,u.display_name,u.avatar
             FROM messages m JOIN users u ON m.user_id=u.id WHERE m.world_id=?
             ORDER BY m.created_at DESC,m.rowid DESC LIMIT ?''',(wid,min(limit,100))).fetchall()
    return [dict(r) for r in reversed(rows)]

def remember(uid,label,content):
    label=label.strip();content=content.strip()
    if not 2<=len(label)<=70 or not 1<=len(content)<=1200:raise ValueError('Memoria inválida (etiqueta 2–70, texto 1–1200)')
    ts=now();mid=uuid.uuid4().hex
    with LOCK,connect() as c:
        if c.execute('SELECT COUNT(*) FROM memories WHERE user_id=?',(uid,)).fetchone()[0]>=200:raise ValueError('Límite de 200 recuerdos por usuario')
        c.execute('INSERT INTO memories VALUES (?,?,?,?,?,?)',(mid,uid,label,content,ts,ts));c.commit()
    return {'id':mid,'label':label,'content':content,'created_at':ts}

def memories(uid):
    with connect() as c:return [dict(r) for r in c.execute('SELECT id,label,content,created_at,updated_at FROM memories WHERE user_id=? ORDER BY updated_at DESC',(uid,))]

def forget(uid,mid):
    with LOCK,connect() as c:
        cur=c.execute('DELETE FROM memories WHERE user_id=? AND id=?',(uid,mid));c.commit()
        return cur.rowcount>0

def feedback(uid,topic,score,comment):
    if not 1<=score<=5 or not 2<=len(topic)<=60 or len(comment)>400:raise ValueError('Evaluación inválida')
    with LOCK,connect() as c:c.execute('INSERT INTO feedback VALUES (?,?,?,?,?,?)',(uuid.uuid4().hex,uid,topic,score,comment,now()));c.commit()

def feedback_summary(uid):
    with connect() as c:return [dict(r) for r in c.execute('SELECT topic,COUNT(*) total,ROUND(AVG(score),2) mean_score FROM feedback WHERE user_id=? GROUP BY topic',(uid,))]

def create_post(uid,body,wid=None):
    body=body.strip()
    if not 1<=len(body)<=1200:raise ValueError('Publicación entre 1 y 1200 caracteres')
    if wid and not is_published(wid):raise ValueError('El mundo no está publicado')
    post_id=uuid.uuid4().hex
    with LOCK,connect() as c:c.execute('INSERT INTO posts VALUES (?,?,?,?,?)',(post_id,uid,body,wid,now()));c.commit()
    return post_id

def posts(limit=40):
    with connect() as c:return [dict(r) for r in c.execute('''SELECT p.*,u.username,u.display_name,u.avatar,
          (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) likes
          FROM posts p JOIN users u ON u.id=p.user_id ORDER BY p.created_at DESC,p.rowid DESC LIMIT ?''',(min(limit,80),))]

def like(uid,post_id,enabled=True):
    with LOCK,connect() as c:
        if enabled:
            try:c.execute('INSERT OR IGNORE INTO likes VALUES (?,?)',(post_id,uid))
            except sqlite3.IntegrityError:raise ValueError('Publicación inexistente')
        else:c.execute('DELETE FROM likes WHERE post_id=? AND user_id=?',(post_id,uid))
        c.commit()

def follow(uid,target,enabled=True):
    if uid==target:raise ValueError('No podés seguirte a vos mismo')
    with LOCK,connect() as c:
        if not c.execute('SELECT 1 FROM users WHERE id=?',(target,)).fetchone():raise ValueError('Usuario inexistente')
        if enabled:c.execute('INSERT OR IGNORE INTO follows VALUES (?,?)',(uid,target))
        else:c.execute('DELETE FROM follows WHERE follower=? AND followed=?',(uid,target))
        c.commit()

def report(uid,target,reason):
    if not 3<=len(reason.strip())<=400:raise ValueError('Motivo entre 3 y 400 caracteres')
    with LOCK,connect() as c:c.execute('INSERT INTO reports VALUES (?,?,?,?,?)',(uuid.uuid4().hex,uid,target,reason.strip(),now()));c.commit()
