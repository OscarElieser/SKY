"""Tests para los cuatro pilares de maestría matemática (CAS, REPL, CoT, LaTeX)
y excelencia de ingeniería de software (DEV-CORE, Zero Placeholders, Linter).
"""
import pytest
from fastapi.testclient import TestClient
from metaverse.api import app
from neural_core.math_engine import (
    ejecutar_cas,
    detectar_y_calcular_en_prompt,
    ejecutar_python_repl,
    auditar_codigo_fuente
)
from neural_core.academic_core import academic_instructions
from neural_core.developer_core import developer_instructions


def _llave_dueno():
    """SENTINEL v12.5: la API es privada; las pruebas usan la llave del dueño como lo hace la interfaz."""
    from metaverse.api import api_token
    return api_token()


client = TestClient(app, headers={'X-SKY-KEY': _llave_dueno()})

# ==============================================================================
# PILAR 1: CÁLCULO SIMBÓLICO DETERMINISTA (CAS - SymPy)
# ==============================================================================
def test_cas_derivative():
    res = ejecutar_cas("3*x^2 + 5*x + 2", operacion="derivada")
    assert res["ok"] is True
    assert res["operacion"] == "derivada"
    assert res["resultado_simbolico"] == "6*x + 5"
    assert "$$" in res["resultado_latex"]
    assert "Regla de potencias" in res["teorema"]
    assert "∫" in res["comprobacion"]

def test_cas_integral():
    res = ejecutar_cas("3*x^2 + 5*x + 2", operacion="integral")
    assert res["ok"] is True
    assert res["operacion"] == "integral"
    assert "x**3" in res["resultado_simbolico"]
    assert "$$" in res["resultado_latex"]
    assert "Teorema Fundamental del Cálculo" in res["teorema"]

def test_cas_limit():
    res = ejecutar_cas("sin(x)/x", operacion="limite", variable="x", punto=0.0)
    assert res["ok"] is True
    assert res["resultado_simbolico"] == "1"

def test_cas_solve():
    res = ejecutar_cas("2*x + 4 = 10", operacion="resolver")
    assert res["ok"] is True
    assert res["resultado_simbolico"] == "[3]"

def test_detectar_y_calcular_en_prompt():
    prompt = "Calcula la derivada de f(x) = 3*x^2 + 5*x + 2 bajo Academic Core"
    calc = detectar_y_calcular_en_prompt(prompt)
    assert calc is not None
    assert calc["ok"] is True
    assert calc["resultado_simbolico"] == "6*x + 5"

# ==============================================================================
# PILAR 1: SANDBOX PYTHON REPL DETERMINISTA
# ==============================================================================
def test_repl_basic_arithmetic():
    res = ejecutar_python_repl("a = 20\nb = 30\na + b")
    assert res["ok"] is True
    assert res["resultado"] == "50"
    assert res["tiempo_ms"] >= 0

def test_repl_scientific_libraries():
    res = ejecutar_python_repl("import sympy as sp\nx = sp.Symbol('x')\nsp.diff(x**3, x)")
    assert res["ok"] is True
    assert res["resultado"] == "3*x**2"

def test_repl_security_block():
    res = ejecutar_python_repl("import os\nos.system('echo hack')")
    assert res["ok"] is False
    assert "Violación de seguridad" in res["error"]

# ==============================================================================
# PILAR 2 Y 3: NIVELES Y CHAIN OF THOUGHT EN ACADEMIC CORE
# ==============================================================================
def test_academic_math_cot_and_latex():
    instructions = academic_instructions("educación", "Calcula la derivada de f(x) = 3*x^2 + 5*x + 2")
    assert "ARQUITECTURA DE MAESTRÍA MATEMÁTICA EN 4 PILARES" in instructions
    assert "Cadena de Pensamiento Obligatoria (Chain of Thought - CoT)" in instructions
    assert "Notación LaTeX Estricta Obligatoria" in instructions
    assert "<CALCULO_DETERMINISTA_CAS>" in instructions
    assert "6*x + 5" in instructions

# ==============================================================================
# DEV-CORE: PROTOCOLO, ZERO PLACEHOLDERS Y LINTER
# ==============================================================================
def test_developer_protocol_injected():
    instructions = developer_instructions("programación", "Crea una función en Python para ordenar una lista")
    assert "PROTOCOLO DE RESPUESTA OBLIGATORIO (DEV-CORE)" in instructions
    assert "REGLA ZERO PLACEHOLDERS" in instructions
    assert "Big-O: O(f(n))" in instructions
    assert "ADAPTACIÓN SEGÚN NIVEL TÉCNICO" in instructions

def test_auditar_codigo_good():
    code = '''
def busqueda_binaria(arr: list[int], objetivo: int) -> int:
    """Realiza búsqueda binaria en un arreglo ordenado."""
    if not isinstance(arr, list):
        raise TypeError("arr debe ser una lista")
    izq, der = 0, len(arr) - 1
    while izq <= der:
        medio = (izq + der) // 2
        if arr[medio] == objetivo:
            return medio
        elif arr[medio] < objetivo:
            izq = medio + 1
        else:
            der = medio - 1
    return -1
'''
    audit = auditar_codigo_fuente(code, lenguaje="python")
    assert audit["pasa_control_calidad"] is True
    assert audit["zero_placeholders"] is True
    assert audit["manejo_defensivo"] is True
    assert audit["tiene_docstrings"] is True
    assert audit["complejidad_estimada"] == "O(n)"

def test_auditar_codigo_placeholders_bad():
    code = '''
def procesar_datos(data):
    // tu código aquí
    pass
'''
    audit = auditar_codigo_fuente(code, lenguaje="python")
    assert audit["pasa_control_calidad"] is False
    assert audit["zero_placeholders"] is False
    assert len(audit["advertencias"]) > 0

# ==============================================================================
# ENDPOINTS REST: /api/math/cas, /api/developer/repl, /api/developer/audit
# ==============================================================================
def test_api_math_cas():
    response = client.post("/api/math/cas", json={"expresion": "3*x^2 + 5*x + 2", "operacion": "derivada"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["resultado_simbolico"] == "6*x + 5"

def test_api_developer_repl():
    response = client.post("/api/developer/repl", json={"code": "res = sum([1, 2, 3, 4, 5])\nres"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["resultado"] == "15"

def test_api_developer_audit():
    response = client.post("/api/developer/audit", json={"code": "def foo():\n    return 42\n", "language": "python"})
    assert response.status_code == 200
    data = response.json()
    assert "pasa_control_calidad" in data
