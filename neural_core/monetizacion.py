"""Embudo comercial realista, sin fingir ingresos ni ventas."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from neural_core.storage import conectar, hora

ETAPAS={"prospecto":0.10,"contactado":0.20,"interesado":0.40,"propuesta":0.65,"negociacion":0.80,"ganado":1.0,"perdido":0.0}


def _centavos(valor):
    try:
        v=Decimal(str(valor))
        if not v.is_finite() or not Decimal("0") <= v <= Decimal("100000000"):
            raise ValueError("Monto inválido")
        return int((v*100).quantize(Decimal("1"),rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError):
        raise ValueError("Monto inválido")


def crear_tablas():
    with conectar() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS clientes (
          id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, servicio TEXT NOT NULL,
          etapa TEXT NOT NULL, monto_centavos INTEGER NOT NULL, moneda TEXT NOT NULL,
          notas TEXT, creado TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ideas (
          id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, tipo TEXT NOT NULL,
          precio_centavos INTEGER NOT NULL, moneda TEXT NOT NULL, creado TEXT NOT NULL);
        """)


def agregar_cliente(nombre, servicio, monto, moneda, etapa="prospecto", notas=""):
    if etapa not in ETAPAS or moneda not in ("NIO", "USD") or not nombre.strip() or not servicio.strip():
        raise ValueError("Datos del cliente inválidos")
    with conectar() as c:
        c.execute("INSERT INTO clientes(nombre,servicio,etapa,monto_centavos,moneda,notas,creado) VALUES (?,?,?,?,?,?,?)",
                  (nombre[:120],servicio[:180],etapa,_centavos(monto),moneda,notas[:350],hora()))


def listar_clientes():
    with conectar() as c:
        return [dict(x) for x in c.execute("SELECT * FROM clientes ORDER BY id DESC LIMIT 500")]


def cambiar_etapa(identificador, etapa):
    if etapa not in ETAPAS:
        raise ValueError("Etapa inválida")
    with conectar() as c:
        c.execute("UPDATE clientes SET etapa=? WHERE id=?",(etapa,int(identificador)))


def resumen_comercial():
    acumulados={"NIO":{"confirmado":0,"potencial":0,"estimado":0},"USD":{"confirmado":0,"potencial":0,"estimado":0}}
    for x in listar_clientes():
        entry=acumulados[x["moneda"]]
        if x["etapa"] == "ganado":
            entry["confirmado"] += x["monto_centavos"]
        elif x["etapa"] != "perdido":
            entry["potencial"] += x["monto_centavos"]
            entry["estimado"] += round(x["monto_centavos"]*ETAPAS[x["etapa"]])
    return {m:{k:v/100 for k,v in grupo.items()} for m,grupo in acumulados.items()}


def simular_ventas(precio,contactos,conversion_pct,costo,moneda="USD"):
    if moneda not in ("USD","NIO") or not 0<=conversion_pct<=100 or contactos<0:
        raise ValueError("Datos de escenario inválidos")
    p=_centavos(precio)/100
    c=_centavos(costo)/100
    ventas_esperadas=float(contactos)*float(conversion_pct)/100
    ingreso=ventas_esperadas*p
    return {"moneda":moneda, "ventas_esperadas":round(ventas_esperadas,2),
            "ingreso_proyectado":round(ingreso,2), "costo_proyectado":c,
            "margen_proyectado":round(ingreso-c,2)}
