"""SKY v12.4 — Ejecutor aislado de habilidades generadas por el Skill Builder.

Se lanza como proceso aparte (python -I -S neural_core/sky_sandbox_runner.py) con un entorno mínimo y un
directorio temporal. Lee por stdin {"codigo": str, "casos": [{"entrada": str, "contexto": dict}]} y escribe por
stdout {"ok": bool, "resultados": [...], "error": str}.

Barreras (además de la revisión estática del código en sky_skill_builder.validar_codigo):
  * Sólo se pueden importar módulos puros de la biblioteca estándar (lista cerrada), ya precargados.
  * Sin open/exec/eval/compile/__import__ libre/getattr/globals… en los builtins.
  * Límites de memoria y CPU en Linux/macOS; tiempo máximo por caso y por proceso.
  * Sin red ni archivos: la habilidad recibe los datos de internet que el dueño aprobó ya descargados en `contexto`.
"""
import json
import sys

PERMITIDOS = ('math', 'statistics', 'json', 're', 'datetime', 'decimal', 'fractions', 'random', 'string', 'textwrap',
              'itertools', 'functools', 'collections', 'calendar', 'unicodedata', 'operator')
BUILTINS_SEGUROS = ('abs', 'all', 'any', 'bool', 'dict', 'divmod', 'enumerate', 'filter', 'float', 'format', 'frozenset',
                    'int', 'isinstance', 'issubclass', 'len', 'list', 'map', 'max', 'min', 'pow', 'range', 'repr',
                    'reversed', 'round', 'set', 'slice', 'sorted', 'str', 'sum', 'tuple', 'zip', 'chr', 'ord', 'hash',
                    'iter', 'next', 'callable', 'bin', 'hex', 'oct', 'Exception', 'ValueError', 'KeyError',
                    'IndexError', 'TypeError', 'ZeroDivisionError', 'ArithmeticError', 'StopIteration', 'RuntimeError',
                    'True', 'False', 'None', 'object', 'staticmethod', 'classmethod', 'property', 'super', 'NotImplementedError')
MAX_SALIDA = 4000


def _limites():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024, 384 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    except Exception:
        pass   # Windows: el proceso padre aplica el tiempo máximo


def _validar_salida(r):
    if not isinstance(r, dict):
        raise TypeError('ejecutar() debe devolver un dict')
    decir = r.get('decir', '')
    if not isinstance(decir, str):
        raise TypeError('«decir» debe ser texto')
    acciones = r.get('acciones', []) or []
    if not isinstance(acciones, list) or len(acciones) > 5:
        raise TypeError('«acciones» debe ser una lista de hasta 5 órdenes')
    limpias = []
    for a in acciones:
        if not isinstance(a, dict) or not isinstance(a.get('orden'), str) or not a['orden'].strip():
            raise TypeError('cada acción debe ser {"orden": "texto"}')
        limpias.append({'orden': ' '.join(a['orden'].split())[:200]})
    return {'decir': decir[:MAX_SALIDA], 'acciones': limpias}


def main():
    pedido = json.loads(sys.stdin.read(400_000))
    modulos = {n: __import__(n) for n in PERMITIDOS}
    import builtins as _b
    seguros = {n: getattr(_b, n) for n in BUILTINS_SEGUROS if hasattr(_b, n)}

    def importar(nombre, globales=None, locales=None, desde=(), nivel=0):
        raiz = nombre.split('.')[0]
        if nivel or raiz not in modulos:
            raise ImportError(f'Módulo no permitido en habilidades: {nombre}')
        return modulos[raiz]

    seguros['__import__'] = importar
    seguros['__build_class__'] = _b.__build_class__
    _limites()
    espacio = {'__builtins__': seguros, '__name__': 'habilidad'}
    try:
        exec(compile(pedido['codigo'], 'habilidad.py', 'exec'), espacio)
        fn = espacio.get('ejecutar')
        if not callable(fn):
            raise TypeError('falta la función ejecutar(entrada, contexto)')
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:300]}', 'resultados': []}))
        return
    resultados = []
    for caso in pedido.get('casos', [])[:20]:
        try:
            salida = _validar_salida(fn(str(caso.get('entrada', '')), json.loads(json.dumps(caso.get('contexto') or {}))))
            resultados.append({'ok': True, 'salida': salida})
        except Exception as exc:
            resultados.append({'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:300]}'})
    print(json.dumps({'ok': True, 'resultados': resultados}, ensure_ascii=False))


if __name__ == '__main__':
    main()
