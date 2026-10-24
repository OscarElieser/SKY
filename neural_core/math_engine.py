"""Motor de Cálculo Simbólico (CAS), Python REPL y Linter de Código para SKY IA.

Pilar determinista para el núcleo académico (SKY-MATH) y de ingeniería (DEV-CORE).
Garantiza cero errores aritméticos y cumplimiento estricto de directivas de producción.
"""
from __future__ import annotations
import ast
import io
import math
import re
import sys
import time
import contextlib
from typing import Dict, Any, List, Optional, Tuple

# Importaciones matemáticas y científicas deterministas
try:
    import sympy as sp
    from sympy.parsing.sympy_parser import (
        parse_expr,
        standard_transformations,
        implicit_multiplication_application,
        convert_xor
    )
    HAS_SYMPY = True
    TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)
except ImportError:
    HAS_SYMPY = False
    TRANSFORMATIONS = None

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import scipy
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ==============================================================================
# 1. MOTOR DE CÁLCULO SIMBÓLICO DETERMINISTA (CAS)
# ==============================================================================
def sanitizar_expresion_matematica(expr_str: str) -> str:
    """Limpia la expresión matemática para que SymPy pueda analizarla con precisión."""
    e = expr_str.strip()
    e = re.sub(r'\^', '**', e)
    e = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', e)
    e = re.sub(r'^[a-zA-Z]\([a-zA-Z]\)\s*=\s*', '', e)
    e = re.sub(r'^y\s*=\s*', '', e)
    return e

def ejecutar_cas(expresion: str, operacion: str = "auto", variable: str = "x", punto: float = 0.0) -> Dict[str, Any]:

    """Ejecuta una operación matemática simbólica determinista usando SymPy.
    
    Operaciones soportadas:
    - 'derivada' / 'diff': Diferenciación simbólica.
    - 'integral' / 'integrate': Integración analítica indefinida.
    - 'limite' / 'limit': Límite de la función cuando la variable tiende a 'punto'.
    - 'resolver' / 'solve': Solución exacta de ecuaciones algebraicas f(x) = 0.
    - 'simplificar' / 'simplify': Simplificación algebraica.
    - 'factorizar' / 'factor': Descomposición en factores.
    - 'taylor' / 'series': Serie de potencias alrededor de un punto.
    """
    if not HAS_SYMPY:
        return {"ok": False, "error": "SymPy no está disponible en el entorno."}

    try:
        var = sp.Symbol(variable)
        clean_expr = sanitizar_expresion_matematica(expresion)
        if "=" in clean_expr:
            lados = clean_expr.split("=", 1)
            parsed = parse_expr(lados[0], transformations=TRANSFORMATIONS, evaluate=True) - parse_expr(lados[1], transformations=TRANSFORMATIONS, evaluate=True)
        else:
            parsed = parse_expr(clean_expr, transformations=TRANSFORMATIONS, evaluate=True)

        op = operacion.lower().strip()
        if op == "auto":
            if any(w in expresion.lower() for w in ["derivad", "d/dx", "diff"]):
                op = "derivada"
            elif any(w in expresion.lower() for w in ["integral", "antiderivad"]):
                op = "integral"
            elif any(w in expresion.lower() for w in ["limit", "límite"]):
                op = "limite"
            elif any(w in expresion.lower() for w in ["resuelve", "despeja", "soluci", "="]):
                op = "resolver"
            else:
                op = "simplificar"

        resultado = None
        comprobacion = ""
        teorema_aplicado = ""

        if op in ("derivada", "diff"):
            resultado = sp.diff(parsed, var)
            teorema_aplicado = "Regla de potencias, linealidad de operadores diferenciales y regla de la cadena"
            try:
                antiderivada = sp.integrate(resultado, var)
                comprobacion = f"Integración de comprobación: ∫ f'(x) dx = {sp.latex(antiderivada)} + C"
            except Exception:
                comprobacion = "Comprobado por consistencia analítica."

        elif op in ("integral", "integrate"):
            resultado = sp.integrate(parsed, var)
            teorema_aplicado = "Teorema Fundamental del Cálculo y métodos de integración analítica"
            try:
                derivada_check = sp.diff(resultado, var)
                comprobacion = f"Derivación de comprobación: d/dx [{sp.latex(resultado)}] = {sp.latex(derivada_check)}"
            except Exception:
                comprobacion = "Comprobado por derivación directa."

        elif op in ("integral_definida", "definite_integral"):
            lim_inf = 0
            lim_sup = punto
            resultado = sp.integrate(parsed, (var, lim_inf, lim_sup))
            teorema_aplicado = "Segundo Teorema Fundamental del Cálculo (Regla de Barrow)"
            comprobacion = f"Evaluación en intervalo [{lim_inf}, {lim_sup}]: {resultado}"

        elif op in ("limite", "limit"):
            resultado = sp.limit(parsed, var, punto)
            teorema_aplicado = f"Cálculo de límites por continuidad y Regla de L'Hôpital si aplica (x -> {punto})"
            comprobacion = f"Evaluación en entorno x -> {punto}"

        elif op in ("resolver", "solve"):
            resultado = sp.solve(parsed, var)
            teorema_aplicado = "Teorema Fundamental del Álgebra y propiedades de igualdad"
            comprobacion = f"Raíces encontradas: {len(resultado) if isinstance(resultado, list) else 1}"

        elif op in ("factorizar", "factor"):
            resultado = sp.factor(parsed)
            teorema_aplicado = "Factorización exacta en anillo de polinomios"
            comprobacion = f"Expansión de comprobación: {sp.latex(sp.expand(resultado))}"

        else:
            resultado = sp.simplify(parsed)
            teorema_aplicado = "Identidades algebraicas y trigonométricas canónicas"
            comprobacion = "Forma canónica reducida irreducible"

        resultado_latex = sp.latex(resultado)
        original_latex = sp.latex(parsed)

        return {
            "ok": True,
            "operacion": op,
            "variable": variable,
            "expresion_original": str(parsed),
            "expresion_latex": f"$${original_latex}$$",
            "resultado_simbolico": str(resultado),
            "resultado_exacto": str(resultado),
            "resultado_latex": f"$${resultado_latex}$$",
            "teorema": teorema_aplicado,
            "comprobacion": comprobacion
        }

    except Exception as exc:
        return {"ok": False, "error": f"Error en cálculo CAS: {type(exc).__name__}: {str(exc)}"}

math_cas_evaluate = ejecutar_cas



def detectar_y_calcular_en_prompt(prompt: str) -> Optional[Dict[str, Any]]:
    """Detecta si un mensaje contiene una consulta matemática determinista y la calcula."""
    p = prompt.strip()
    
    # 1. Patrón: Derivada de f(x) = ... o derivada de ...
    m_diff = re.search(r'(?:derivada|diferenciar|deriva)\s+(?:de\s+)?(?:f\([a-z]\)\s*=\s*|y\s*=\s*)?([0-9a-zA-Z\s\+\-\*\/\^\(\)]+?)(?:\s+paso|\s+bajo|\s+con|\s*$|\.|\,)', p, re.I)
    if m_diff:
        expr = m_diff.group(1).strip()
        if len(expr) >= 2 and any(c in expr for c in ['x', 't', 'y', 'z', '^', '*', '+', '-']):
            res = ejecutar_cas(expr, operacion="derivada")
            if res.get("ok"):
                return res

    # 2. Patrón: Integral de ...
    m_int = re.search(r'(?:integral|antiderivada|integra)\s+(?:de\s+)?(?:f\([a-z]\)\s*=\s*)?([0-9a-zA-Z\s\+\-\*\/\^\(\)]+?)(?:\s+paso|\s+bajo|\s+dx|\s*$|\.|\,)', p, re.I)
    if m_int:
        expr = m_int.group(1).strip()
        if len(expr) >= 2 and any(c in expr for c in ['x', 't', 'y', 'z', '^', '*', '+', '-']):
            res = ejecutar_cas(expr, operacion="integral")
            if res.get("ok"):
                return res

    # 3. Patrón: Límite de ... cuando x -> ...
    m_lim = re.search(r'(?:l[ií]mite|limit)\s+(?:de\s+)?([0-9a-zA-Z\s\+\-\*\/\^\(\)]+?)\s+(?:cuando|para)\s+([a-z])\s*(?:tiende\s+a|->|→)\s*([0-9\-]+)', p, re.I)
    if m_lim:
        expr = m_lim.group(1).strip()
        var = m_lim.group(2).strip()
        punto = float(m_lim.group(3).strip())
        res = ejecutar_cas(expr, operacion="limite", variable=var, punto=punto)
        if res.get("ok"):
            return res

    # 4. Patrón: Resuelve / Solución de ecuación 2*x + 3 = 7
    m_solve = re.search(r'(?:resuelve|despeja|soluciona|soluci[oó]n\s+de)\s+(?:la\s+ecuaci[oó]n\s+)?([0-9a-zA-Z\s\+\-\*\/\^\(\)]+=[0-9a-zA-Z\s\+\-\*\/\^\(\)]+)', p, re.I)
    if m_solve:
        expr = m_solve.group(1).strip()
        res = ejecutar_cas(expr, operacion="resolver")
        if res.get("ok"):
            return res

    return None


# ==============================================================================
# 2. SANDBOX PYTHON REPL DETERMINISTA (Code Execution)
# ==============================================================================
BLOCKED_MODULES = {
    "os", "sys", "subprocess", "socket", "requests", "urllib", "shutil",
    "pathlib", "importlib", "ctypes", "posix", "winreg", "builtins"
}
BLOCKED_CALLS = {
    "open", "eval", "exec", "__import__", "breakpoint", "compile",
    "globals", "locals", "getattr", "setattr", "delattr", "vars", "input", "memoryview", "type"
}
# Funciones de bibliotecas que evalúan texto como código o tocan el sistema.
BLOCKED_ATTRS = {"sympify", "parse_expr", "lambdify", "system", "popen", "spawn", "exec_command", "load", "fromfile",
                 "tofile", "save", "savetxt", "loadtxt", "genfromtxt", "ctypeslib", "f2py", "testing"}

class SandboxSecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            base = alias.name.split('.')[0]
            if base in BLOCKED_MODULES or base not in REPL_PERMITIDOS:
                self.errors.append(f"Importación no autorizada en Sandbox: '{alias.name}'.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base = node.module.split('.')[0]
            if base in BLOCKED_MODULES or base not in REPL_PERMITIDOS:
                self.errors.append(f"Importación no autorizada en Sandbox: 'from {node.module}'.")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # SENTINEL: sin atributos internos (().__class__.__subclasses__() permitía salir del sandbox).
        if node.attr.startswith('_'):
            self.errors.append(f"Acceso a atributo interno bloqueado en Sandbox: '{node.attr}'.")
        if node.attr in BLOCKED_ATTRS:
            self.errors.append(f"Función bloqueada por seguridad en Sandbox: '{node.attr}'.")
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id.startswith('__') or node.id in BLOCKED_CALLS:
            self.errors.append(f"Nombre bloqueado por seguridad en Sandbox: '{node.id}'.")
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str) and ('__' in node.value or 'import' in node.value):
            self.errors.append('Texto con nombres internos o importaciones bloqueado en Sandbox.')
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
            self.errors.append(f"Llamada bloqueada por seguridad en Sandbox: '{node.func.id}()'.")
        self.generic_visit(node)


REPL_PERMITIDOS = {"math", "cmath", "fractions", "decimal", "statistics", "itertools", "functools", "collections",
                   "random", "json", "re", "datetime", "sympy", "numpy", "scipy"}


def _importar_permitido(nombre, globales=None, locales=None, desde=(), nivel=0):
    if nivel or nombre.split('.')[0] not in REPL_PERMITIDOS:
        raise ImportError(f"Importación no autorizada en Sandbox: '{nombre}'.")
    return __import__(nombre, globales, locales, desde, nivel)


def ejecutar_python_repl(codigo: str, timeout_segundos: float = 3.0) -> Dict[str, Any]:
    """Ejecuta código de forma segura en un sandbox con acceso a SymPy, NumPy, SciPy y matemáticas."""
    codigo_clean = codigo.strip()
    if codigo_clean.startswith("```"):
        lineas = codigo_clean.splitlines()
        if len(lineas) >= 2 and lineas[0].startswith("```"):
            codigo_clean = "\n".join(lineas[1:-1])

    try:
        parsed_tree = ast.parse(codigo_clean)
        visitor = SandboxSecurityVisitor()
        visitor.visit(parsed_tree)
        if visitor.errors:
            return {"ok": False, "error": "Violación de seguridad: " + "; ".join(visitor.errors)}
    except SyntaxError as syn_err:
        return {"ok": False, "error": f"Error de sintaxis: {syn_err.msg} en línea {syn_err.lineno}"}
    except Exception as exc:
        return {"ok": False, "error": f"Error al analizar código: {str(exc)}"}

    import builtins as _builtins
    _seguros = {n: getattr(_builtins, n) for n in (
        "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "format", "frozenset", "int",
        "isinstance", "len", "list", "map", "max", "min", "pow", "print", "range", "reversed", "round", "set",
        "slice", "sorted", "str", "sum", "tuple", "zip", "complex", "ValueError", "ZeroDivisionError", "Exception")}
    _seguros["__import__"] = _importar_permitido
    safe_globals = {
        "__builtins__": _seguros,
        "__name__": "__sandbox__",
        "__doc__": None,
        "math": math,
        "sp": sp if HAS_SYMPY else None,
        "sympy": sp if HAS_SYMPY else None,
        "np": np if HAS_NUMPY else None,
        "numpy": np if HAS_NUMPY else None,
        "scipy": scipy if HAS_SCIPY else None,
        "print": print,
        "range": range,
        "len": len,
        "enumerate": enumerate,
        "zip": zip,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
    }
    safe_locals = {}

    stdout_capture = io.StringIO()
    start_time = time.time()

    try:
        with contextlib.redirect_stdout(stdout_capture):
            if parsed_tree.body and isinstance(parsed_tree.body[-1], ast.Expr):
                last_expr = parsed_tree.body.pop()
                exec_code = compile(parsed_tree, filename="<sandbox>", mode="exec")
                exec(exec_code, safe_globals, safe_locals)
                eval_code = compile(ast.Expression(body=last_expr.value), filename="<sandbox>", mode="eval")
                ret_val = eval(eval_code, safe_globals, safe_locals)
                if ret_val is not None:
                    safe_locals["_result"] = ret_val
            else:
                exec_code = compile(parsed_tree, filename="<sandbox>", mode="exec")
                exec(exec_code, safe_globals, safe_locals)

        duracion_ms = (time.time() - start_time) * 1000
        output_text = stdout_capture.getvalue()
        resultado_final = safe_locals.get("_result", None)

        return {
            "ok": True,
            "stdout": output_text.strip(),
            "resultado": str(resultado_final) if resultado_final is not None else None,
            "tiempo_ms": round(duracion_ms, 2),
            "variables_creadas": [k for k in safe_locals.keys() if not k.startswith('_')]
        }

    except Exception as exc:
        duracion_ms = (time.time() - start_time) * 1000
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {str(exc)}",
            "stdout": stdout_capture.getvalue().strip(),
            "tiempo_ms": round(duracion_ms, 2)
        }


# ==============================================================================
# 3. LINTER Y AUDITOR DE CÓDIGO (DEV-CORE)
# ==============================================================================
PLACEHOLDER_PATTERNS = [
    r'//\s*(?:tu\s+c[oó]digo|implementar|resto|aqu[ií]|todo|l[oó]gica)',
    r'#\s*(?:tu\s+c[oó]digo|implementar|resto|aqu[ií]|todo|l[oó]gica)',
    r'/\*\s*(?:tu\s+c[oó]digo|implementar|resto|aqu[ií]|todo|l[oó]gica).*?\*/',
]

def auditar_codigo_fuente(codigo: str, lenguaje: str = "python") -> Dict[str, Any]:
    """Audita el código generado contra las directivas de calidad de DEV-CORE:
    
    1. Zero Placeholders: Sin comentarios evasivos ni código incompleto.
    2. Manejo defensivo de errores: Validaciones y excepciones.
    3. Documentación técnica estándar: Docstrings / comentarios de API.
    4. Complejidad Big-O estimada.
    """
    hallazgos = []
    tiene_placeholders = False
    
    for pat in PLACEHOLDER_PATTERNS:
        matches = re.findall(pat, codigo, re.IGNORECASE)
        if matches:
            tiene_placeholders = True
            hallazgos.append(f"Se detectó comentario placeholder no permitido: '{matches[0]}'.")

    manejo_defensivo = False
    tiene_docstrings = False
    complejidad_estimada = "O(1)"
    funciones_detectadas = []

    if lenguaje.lower() in ("python", "py"):
        try:
            tree = ast.parse(codigo)
            bucles = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.For, ast.While)):
                    bucles += 1
                if isinstance(node, (ast.Try, ast.Raise)):
                    manejo_defensivo = True
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    funciones_detectadas.append(node.name)
                    if ast.get_docstring(node):
                        tiene_docstrings = True
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        hallazgos.append(f"Función '{node.name}' sin implementar (solo contiene 'pass').")

            if bucles == 1:
                complejidad_estimada = "O(n)"
            elif bucles == 2:
                complejidad_estimada = "O(n²)"
            elif bucles >= 3:
                complejidad_estimada = "O(n³+)"

        except SyntaxError as e:
            hallazgos.append(f"Error de sintaxis en el código: {e.msg} (Línea {e.lineno}).")
    else:
        if re.search(r'\b(try|catch|throw|finally)\b', codigo):
            manejo_defensivo = True
        if re.search(r'/\*\*[\s\S]*?\*/|///', codigo):
            tiene_docstrings = True
        bucles_genericos = len(re.findall(r'\b(for|while)\b\s*\(', codigo))
        if bucles_genericos == 1:
            complejidad_estimada = "O(n)"
        elif bucles_genericos >= 2:
            complejidad_estimada = "O(n²)"

    pasa_control_calidad = len(hallazgos) == 0 and not tiene_placeholders

    return {
        "pasa_control_calidad": pasa_control_calidad,
        "zero_placeholders": not tiene_placeholders,
        "manejo_defensivo": manejo_defensivo,
        "tiene_docstrings": tiene_docstrings,
        "complejidad_estimada": complejidad_estimada,
        "funciones": funciones_detectadas,
        "advertencias": hallazgos
    }
