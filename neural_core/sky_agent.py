"""Núcleo de ejecución por capacidades: permite herramientas locales explícitas.

Nunca ejecuta comandos arbitrarios, ni compras, ni publica cambios automáticamente.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
import ast,operator,math
from .sky_evolution import metas,mejoras,feedback_resumen

@dataclass(frozen=True)
class Skill:
    name:str
    description:str
    needs_confirmation:bool

SKILLS={
    'calcular':Skill('calcular','Evaluar una fórmula aritmética local',False),
    'hora_local':Skill('hora_local','Mostrar fecha y hora del equipo',False),
    'metas':Skill('metas','Consultar metas personales',False),
    'mejoras':Skill('mejoras','Consultar propuestas de mejora de SKY',False),
    'evaluaciones':Skill('evaluaciones','Ver valoraciones registradas',False),
}
_ALLOWED_OP={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
             ast.Div:operator.truediv,ast.Pow:operator.pow,ast.Mod:operator.mod}
_ALLOWED_UN={ast.UAdd:lambda x:x,ast.USub:operator.neg}

def calc(expr:str)->float:
    if len(expr)>120:raise ValueError('Expresión demasiado larga')
    node=ast.parse(expr,mode='eval').body
    def ev(n,level=0):
        if level>12:raise ValueError('Expresión demasiado compleja')
        if isinstance(n,ast.Constant) and type(n.value) in (int,float): return float(n.value)
        if isinstance(n,ast.UnaryOp) and type(n.op) in _ALLOWED_UN:return _ALLOWED_UN[type(n.op)](ev(n.operand,level+1))
        if isinstance(n,ast.BinOp) and type(n.op) in _ALLOWED_OP:
            a,b=ev(n.left,level+1),ev(n.right,level+1)
            if abs(a)>1e15 or abs(b)>1e15:raise ValueError('Números demasiado grandes')
            if isinstance(n.op,ast.Pow) and abs(b)>12:raise ValueError('Exponente demasiado grande')
            return _ALLOWED_OP[type(n.op)](a,b)
        raise ValueError('Solo aritmética; no se ejecuta código')
    result=ev(node)
    if not math.isfinite(result) or abs(result)>1e16:raise ValueError('Resultado inválido')
    return result

def execute_skill(name:str,argument:str=''):
    if name not in SKILLS:raise ValueError('Herramienta no reconocida')
    return {'calcular':lambda:calc(argument),
            'hora_local':lambda:datetime.now().isoformat(timespec='seconds'),
            'metas':metas,'mejoras':mejoras,'evaluaciones':feedback_resumen}[name]()


def interpret_local_command(phrase:str):
    """Una orden explícita a herramientas locales (texto o voz), o None."""
    import re, json
    t=phrase.strip()
    m=re.match(r'^(?:/sky|sky[, :]+)\s*(?:calcul[aá]|calcular|calcula)\s+(.+)$',t,re.I)
    if m:return 'Resultado: '+str(execute_skill('calcular',m.group(1)))
    keys={'hora':'hora_local','fecha':'hora_local','metas':'metas',
          'mejoras':'mejoras','evaluaciones':'evaluaciones'}
    for keyword,key in keys.items():
        if re.fullmatch(r'(?:/sky|sky[, :]+)\s*'+keyword+r'\s*',t,re.I):
            return json.dumps(execute_skill(key),ensure_ascii=False,indent=2,default=str)
    if re.fullmatch(r'(?:/sky|sky[, :]+)\s*ayuda\s*',t,re.I):
        return 'Comandos internos: /sky calcula (500-120)*1.15 · /sky hora · /sky metas · /sky mejoras · /sky evaluaciones.'
    return None
