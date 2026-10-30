"""Herramientas científicas y docentes verificables, sin efectos externos.

Física 1D en SI, masa molar aproximada y sumatoria de rúbricas de usuario.
Los resultados no sustituyen simulación científica ni evaluación profesional.
"""
from __future__ import annotations
from collections import Counter
import math
import re
import statistics

class ScienceInputError(ValueError):
    pass

def _numeric(v, name, lower=-1e12, upper=1e12):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lower <= v <= upper:
        raise ScienceInputError(name + ": número finito en rango requerido")
    return float(v)

def _stable(v):
    if not math.isfinite(v) or abs(v)>1e19:
        raise ScienceInputError("Resultado fuera de límites")
    return v

def mecanica_si(args, previous=None):
    if not isinstance(args, dict):
        raise ScienceInputError("Objeto de entrada inválido")
    k = args.get("modelo")
    if k == "aceleracion_constante":
        if set(args)!={"modelo","velocidad_inicial_m_s","aceleracion_m_s2","tiempo_s"}:
            raise ScienceInputError("Campos de cinemática incorrectos")
        v0=_numeric(args["velocidad_inicial_m_s"],"velocidad_inicial_m_s",-1e5,1e5)
        a=_numeric(args["aceleracion_m_s2"],"aceleracion_m_s2",-1e5,1e5)
        t=_numeric(args["tiempo_s"],"tiempo_s",0,1e6)
        vf=_stable(v0+a*t)
        d=_stable(v0*t+0.5*a*t*t)
        if not math.isclose(d,(v0+vf)*t/2,rel_tol=1e-12,abs_tol=1e-7):
            raise ScienceInputError("No coincide velocidad media por tiempo")
        return {"modelo":k,"velocidad_final_m_s":vf,"desplazamiento_m":d,
                "unidades":"SI","comprobacion":"velocidad_media_por_tiempo"}
    if k == "energia_cinetica":
        if set(args)!={"modelo","masa_kg","velocidad_m_s"}:
            raise ScienceInputError("Campos de energía incorrectos")
        m=_numeric(args["masa_kg"],"masa_kg",1e-9,1e9)
        v=_numeric(args["velocidad_m_s"],"velocidad_m_s",-1e5,1e5)
        e=_stable(0.5*m*v*v)
        if not math.isclose(math.sqrt(2*e/m),abs(v),rel_tol=1e-12,abs_tol=1e-9):
            raise ScienceInputError("No coincide velocidad reconstruida")
        return {"modelo":k,"energia_j":e,"unidades":"SI","comprobacion":"velocidad_reconstruida"}
    if k == "segunda_ley_newton":
        if set(args)!={"modelo","masa_kg","aceleracion_m_s2"}:
            raise ScienceInputError("Campos de fuerza incorrectos")
        m=_numeric(args["masa_kg"],"masa_kg",1e-9,1e9)
        a=_numeric(args["aceleracion_m_s2"],"aceleracion_m_s2",-1e5,1e5)
        force=_stable(m*a)
        if not math.isclose(force/m,a,rel_tol=1e-12,abs_tol=1e-9):
            raise ScienceInputError("No coincide aceleración reconstruida")
        return {"modelo":k,"fuerza_n":force,"unidades":"SI",
                "comprobacion":"aceleracion_reconstruida"}
    raise ScienceInputError("Modelo físico no admitido")

# Masas atómicas estándar redondeadas para cálculo pedagógico aproximado (g/mol).
ATOMIC_WEIGHTS = {
    "H":1.008,"He":4.0026,"Li":6.94,"Be":9.0122,"B":10.81,
    "C":12.011,"N":14.007,"O":15.999,"F":18.998,"Ne":20.180,
    "Na":22.990,"Mg":24.305,"Al":26.982,"Si":28.085,"P":30.974,
    "S":32.06,"Cl":35.45,"Ar":39.948,"K":39.098,"Ca":40.078,
    "Cr":51.996,"Mn":54.938,"Fe":55.845,"Co":58.933,"Ni":58.693,
    "Cu":63.546,"Zn":65.38,"Br":79.904,"Ag":107.8682,
    "I":126.904,"Ba":137.327,"Au":196.967,
}
def _atoms(formula):
    if not isinstance(formula,str) or not 1<=len(formula)<=120 or not re.fullmatch(r"[A-Za-z0-9()]+",formula):
        raise ScienceInputError("Fórmula química no permitida")
    stack=[Counter()]
    i=0
    while i<len(formula):
        c=formula[i]
        if c=="(":
            if len(stack)>=6:
                raise ScienceInputError("Anidamiento excesivo")
            stack.append(Counter())
            i+=1
            continue
        if c==")":
            if len(stack)==1 or not stack[-1]:
                raise ScienceInputError("Paréntesis inválido")
            group=stack.pop()
            i+=1
        elif c.isupper():
            j=i+1
            if j<len(formula) and formula[j].islower():
                j+=1
            symbol=formula[i:j]
            if symbol not in ATOMIC_WEIGHTS:
                raise ScienceInputError("Elemento no disponible: "+symbol)
            group=Counter({symbol:1})
            i=j
        else:
            raise ScienceInputError("Secuencia química inválida")
        j=i
        while j<len(formula) and formula[j].isdigit():
            j+=1
        count=int(formula[i:j]) if j!=i else 1
        if not 1<=count<=999:
            raise ScienceInputError("Subíndice no admitido")
        i=j
        stack[-1].update({name:n*count for name,n in group.items()})
        if sum(stack[-1].values())>100000:
            raise ScienceInputError("Fórmula excesiva")
    if len(stack)!=1 or not stack[0]:
        raise ScienceInputError("Paréntesis sin cerrar")
    return stack[0]

def masa_molar(args, previous=None):
    if not isinstance(args,dict) or set(args)!={"formula"}:
        raise ScienceInputError("Campo formula requerido")
    atoms=_atoms(args["formula"])
    total=math.fsum(n*ATOMIC_WEIGHTS[s] for s,n in atoms.items())
    if not math.isfinite(total) or total<=0:
        raise ScienceInputError("Masa molar inválida")
    return {"formula":args["formula"],"elementos":dict(sorted(atoms.items())),
            "masa_molar_g_mol":round(total,7),"unidades":"g/mol",
            "precision":"masas_atomicas_redondeadas",
            "comprobacion":"desglose_por_elemento"}

def evaluar_rubrica(args, previous=None):
    if not isinstance(args,dict) or set(args)!={"criterios"}:
        raise ScienceInputError("Criterios requeridos")
    criteria=args["criterios"]
    if not isinstance(criteria,list) or not 1<=len(criteria)<=20:
        raise ScienceInputError("La rúbrica debe tener 1 a 20 criterios")
    rows=[]
    seen=set()
    for criterion in criteria:
        if not isinstance(criterion,dict) or set(criterion)!={"nombre","maximo","obtenido"}:
            raise ScienceInputError("Criterio mal estructurado")
        name=criterion["nombre"]
        if not isinstance(name,str) or not 2<=len(name.strip())<=100 or name.strip().casefold() in seen:
            raise ScienceInputError("Criterio duplicado o nombre inválido")
        name=name.strip()
        seen.add(name.casefold())
        maximum=_numeric(criterion["maximo"],"maximo",0.01,1000)
        earned=_numeric(criterion["obtenido"],"obtenido",0,maximum)
        rows.append({"nombre":name,"maximo":maximum,"obtenido":earned})
    possible=math.fsum(x["maximo"] for x in rows)
    obtained=math.fsum(x["obtenido"] for x in rows)
    pct=100*obtained/possible
    if not 0<=pct<=100+1e-9:
        raise ScienceInputError("Resultado de rúbrica inconsistente")
    label="destacado" if pct>=95 else "logrado" if pct>=80 else (
        "en_progreso" if pct>=60 else "inicial")
    return {"criterios":rows,"total_obtenido":obtained,"total_posible":possible,
            "porcentaje":round(pct,4),"nivel_referencial":label,
            "regla":"Niveles orientativos SKY: inicial<60, progreso<80, logrado<95, destacado>=95",
            "comprobacion":"sumatoria_por_criterio"}

def review(role, tool, args, result):
    """Recomprobación mecánica acotada (no es auditoría independiente completa)."""
    if not isinstance(result,dict):
        return {"passed":False,"reason":"Resultado no estructurado"}
    try:
        if (role,tool)==("datos","resumen"):
            vals=args["values"]
            correct=(result.get("count")==len(vals)
                and math.isclose(result["mean"],math.fsum(vals)/len(vals),rel_tol=1e-10,abs_tol=1e-10)
                and result["minimum"]==min(vals) and result["maximum"]==max(vals)
                and result["median"]==statistics.median(vals))
            return {"passed":bool(correct),"rule":"estadisticas_recalculadas"}
        for pair,fn,rule in (
            (("fisica","mecanica_si"),mecanica_si,"identidades_fisicas"),
            (("quimica","masa_molar"),masa_molar,"formula_recalculada"),
            (("educacion","evaluar_rubrica"),evaluar_rubrica,"rubrica_recalculada"),
        ):
            if (role,tool)==pair:
                return {"passed":result==fn(args),"rule":rule}
    except (ValueError,TypeError,KeyError,OverflowError,ZeroDivisionError):
        return {"passed":False,"reason":"El control detectó una inconsistencia"}
    return {"passed":True,"rule":"verificacion_original_de_herramienta","scope":"limitada"}
