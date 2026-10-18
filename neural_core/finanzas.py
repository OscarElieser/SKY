"""Estadísticas financieras basadas en registros del usuario, sin conversión implícita de moneda."""
from collections import defaultdict
from neural_core.storage import movimientos, presupuestos
from datetime import date

def resumen(mes=None):
    mes = mes or date.today().strftime('%Y-%m')
    totales=defaultdict(lambda:{'ingreso':0,'gasto':0})
    categorias=defaultdict(int)
    for m in movimientos():
        if not m['creado'].startswith(mes):
            continue
        totales[m['moneda']][m['tipo']] += m['monto_centavos']
        if m['tipo']=='gasto':
            categorias[(m['categoria'],m['moneda'])] += m['monto_centavos']
    alertas=[]
    for p in presupuestos():
        gastado=categorias[(p['categoria'],p['moneda'])]
        if p['limite_centavos'] > 0 and gastado >= p['limite_centavos']:
            alertas.append({'categoria':p['categoria'],'moneda':p['moneda'],
                           'gasto':gastado/100,'limite':p['limite_centavos']/100})
    return {'mes':mes,'totales':dict(totales),'categorias':dict(categorias),'alertas':alertas}

def crecimiento_compuesto(capital,aporte,tasa_anual,meses):
    tasa=(1+tasa_anual/100)**(1/12)-1
    saldo=float(capital)
    for _ in range(int(meses)):
        saldo=saldo*(1+tasa)+float(aporte)
    return saldo
