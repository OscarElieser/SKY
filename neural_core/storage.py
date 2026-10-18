"""SQLite privado con índices de documentos y registro financiero local."""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
import sqlite3
import re

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "local_data" / "neuralt.sqlite3"
DB.parent.mkdir(exist_ok=True, parents=True)

@contextmanager
def conectar():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

def iniciar():
    with conectar() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY, creado TEXT NOT NULL, tipo TEXT NOT NULL,
            categoria TEXT NOT NULL, concepto TEXT NOT NULL,
            monto_centavos INTEGER NOT NULL CHECK(monto_centavos>0),
            moneda TEXT NOT NULL CHECK(moneda IN ('NIO','USD')));
        CREATE TABLE IF NOT EXISTS presupuestos (
            categoria TEXT NOT NULL, moneda TEXT NOT NULL, limite_centavos INTEGER NOT NULL,
            PRIMARY KEY(categoria, moneda));
        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, registrado TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fragmentos (
            id INTEGER PRIMARY KEY, documento_id INTEGER NOT NULL,
            contenido TEXT NOT NULL, FOREIGN KEY(documento_id) REFERENCES documentos(id));
        CREATE TABLE IF NOT EXISTS memorias (
            id INTEGER PRIMARY KEY, texto TEXT NOT NULL, creado TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, area TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente', creado TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS operaciones (
            id INTEGER PRIMARY KEY, concepto TEXT NOT NULL, beneficiario TEXT NOT NULL,
            monto_centavos INTEGER NOT NULL, moneda TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'borrador', creado TEXT NOT NULL,
            revisado TEXT);
        """)
        try:
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS indice USING fts5(contenido, fragmento_id UNINDEXED, tokenize='unicode61 remove_diacritics 2')")
        except sqlite3.OperationalError:
            pass  # Compatibilidad con SQLite compilado sin FTS5.

def hora():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def guardar_movimiento(tipo, categoria, concepto, monto, moneda):
    if tipo not in ('ingreso','gasto') or moneda not in ('NIO','USD'):
        raise ValueError("Tipo o moneda inválidos.")
    centavos = round(float(monto)*100)
    if centavos < 1 or centavos > 100_000_000_00:
        raise ValueError("Monto fuera de límites.")
    with conectar() as c:
        c.execute("INSERT INTO movimientos(creado,tipo,categoria,concepto,monto_centavos,moneda) VALUES(?,?,?,?,?,?)",
                  (hora(),tipo,categoria[:80],concepto[:240],centavos,moneda))

def movimientos():
    with conectar() as c:
        return [dict(x) for x in c.execute("SELECT * FROM movimientos ORDER BY id DESC LIMIT 1500")]

def guardar_presupuesto(categoria, moneda, limite):
    centavos = round(float(limite)*100)
    if not (0 <= centavos <= 100_000_000_00) or moneda not in ('NIO','USD'):
        raise ValueError("Presupuesto inválido")
    with conectar() as c:
        c.execute("INSERT INTO presupuestos VALUES(?,?,?) ON CONFLICT(categoria,moneda) DO UPDATE SET limite_centavos=excluded.limite_centavos",
                  (categoria[:80],moneda,centavos))

def presupuestos():
    with conectar() as c:
        return [dict(x) for x in c.execute("SELECT * FROM presupuestos")]

def _fragmentar(texto, tam=850, solape=120):
    limpio = re.sub(r"\s+", " ", texto).strip()
    i = 0
    while i < len(limpio):
        yield limpio[i:i+tam]
        if i+tam >= len(limpio):
            break
        i += tam-solape

def agregar_documento(nombre, texto):
    if len(texto) > 250_000:
        raise ValueError("Documento demasiado largo (máximo 250.000 caracteres).")
    if not texto.strip():
        raise ValueError("Documento sin texto extraíble.")
    with conectar() as c:
        cur = c.execute("INSERT INTO documentos(nombre,registrado) VALUES (?,?)", (nombre[:160],hora()))
        doc_id = cur.lastrowid
        for trozo in _fragmentar(texto):
            x = c.execute("INSERT INTO fragmentos(documento_id,contenido) VALUES(?,?)", (doc_id,trozo))
            try:
                c.execute("INSERT INTO indice(contenido,fragmento_id) VALUES(?,?)", (trozo,x.lastrowid))
            except sqlite3.OperationalError:
                pass
    return doc_id

def documentos():
    with conectar() as c:
        return [dict(x) for x in c.execute("SELECT * FROM documentos ORDER BY id DESC")]

def buscar_documentos(pregunta, limite=5):
    palabras = re.findall(r"\w+", pregunta, flags=re.UNICODE)
    # Consulta FTS sanitizada: OR de términos, sin operadores recibidos del usuario.
    consulta = " OR ".join('"'+p[:35]+'"' for p in palabras[:10] if len(p)>2)
    with conectar() as c:
        if consulta:
            try:
                rows = c.execute("""SELECT d.nombre, f.contenido FROM indice i
                    JOIN fragmentos f ON f.id=CAST(i.fragmento_id AS INTEGER)
                    JOIN documentos d ON d.id=f.documento_id
                    WHERE indice MATCH ? ORDER BY bm25(indice) LIMIT ?""",(consulta,limite)).fetchall()
                return [dict(x) for x in rows]
            except sqlite3.OperationalError:
                pass
        if not palabras:
            return []
        r = c.execute("""SELECT d.nombre,f.contenido FROM fragmentos f JOIN documentos d
                    ON d.id=f.documento_id WHERE f.contenido LIKE ? LIMIT ?""",
                    ('%'+palabras[0][:35]+'%', limite)).fetchall()
        return [dict(x) for x in r]

def guardar_memoria(texto):
    if not 3 <= len(texto.strip()) <= 1200:
        raise ValueError("Memoria debe contener entre 3 y 1200 caracteres")
    with conectar() as c:
        c.execute("INSERT INTO memorias(texto,creado) VALUES (?,?)", (texto.strip(),hora()))

def memorias():
    with conectar() as c:
        return [dict(x) for x in c.execute("SELECT * FROM memorias ORDER BY id DESC LIMIT 50")]

def eliminar_memoria(identificador):
    with conectar() as c:
        c.execute("DELETE FROM memorias WHERE id=?", (identificador,))

def guardar_tarea(nombre, area):
    with conectar() as c:
        c.execute("INSERT INTO tareas(nombre,area,creado) VALUES(?,?,?)",(nombre[:240],area[:80],hora()))

def tareas():
    with conectar() as c:
        return [dict(x) for x in c.execute("SELECT * FROM tareas ORDER BY id DESC")]

def completar_tarea(identificador):
    with conectar() as c:
        c.execute("UPDATE tareas SET estado='completada' WHERE id=?",(identificador,))

def crear_operacion(concepto,beneficiario,monto,moneda):
    centavos=round(float(monto)*100)
    if not (0<centavos<=100_000_000_00) or moneda not in ('NIO','USD'):
        raise ValueError("Monto o moneda inválidos")
    with conectar() as c:
        c.execute("INSERT INTO operaciones(concepto,beneficiario,monto_centavos,moneda,creado) VALUES(?,?,?,?,?)",
                  (concepto[:240],beneficiario[:180],centavos,moneda,hora()))

def operaciones():
    with conectar() as c:
        return [dict(x) for x in c.execute("SELECT * FROM operaciones ORDER BY id DESC")]

def revisar_operacion(identificador,estado):
    if estado not in ('aprobada_local','descartada'):
        raise ValueError("Estado no permitido")
    with conectar() as c:
        c.execute("UPDATE operaciones SET estado=?, revisado=? WHERE id=? AND estado='borrador'",
                  (estado,hora(),identificador))
