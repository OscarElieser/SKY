"""SKY v12.3 — Perfil del dueño (USER.md): quién sos, tus herramientas, tus suscripciones y cómo querés que te hable.

El archivo vive en ~/.neuralt/USER.md, lo editás vos (en el HUD: Módulos → Perfil, o con cualquier editor) y el
cerebro lo lee en cada mensaje. Es texto del dueño: se usa como contexto, nunca se envía a terceros salvo al modelo
de IA que vos elegiste. No pongas contraseñas: SKY rechaza guardarlas.
"""
from __future__ import annotations

import re
from pathlib import Path

MAX_CHARS = 8000
PLANTILLA = """# Quién soy
- Nombre: Oscar Elieser Chamorro Guzmán
- Me gusta que me hablen: cálido, directo y con expresiones nicaragüenses moderadas
- Equipo de fútbol: Real Madrid

# Trabajo y proyectos
- (tu trabajo, tus proyectos activos, tus responsabilidades)

# Herramientas que uso
- (por ejemplo: Word, Excel, VS Code, Canva, Notion)

# Suscripciones
- (por ejemplo: Spotify, YouTube Premium, Claude, ChatGPT)

# Horarios y rutinas
- (por ejemplo: trabajo de 8 a 5, reviso el correo a las 8:00)

# Objetivos
- (lo que querés lograr este año)
"""
_SECRETO = re.compile(r'contrase(?:ñ|n)a\s*[:=]|password\s*[:=]|\bpin\s*[:=]|cvv|token\s*[:=]|api[_ ]?key\s*[:=]', re.I)


def ruta() -> Path:
    return Path.home() / '.neuralt' / 'USER.md'


def leer(crear: bool = True) -> str:
    p = ruta()
    if not p.exists():
        if not crear:
            return ''
        guardar(PLANTILLA)
    try:
        return p.read_text(encoding='utf-8')[:MAX_CHARS]
    except OSError:
        return ''


def guardar(texto: str) -> dict:
    texto = str(texto or '').replace('\r\n', '\n')
    if len(texto) > MAX_CHARS:
        raise ValueError(f'El perfil puede tener hasta {MAX_CHARS} caracteres.')
    if _SECRETO.search(texto):
        raise ValueError('Por seguridad el perfil no puede contener contraseñas, PIN, tokens ni claves de API.')
    p = ruta()
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(texto, encoding='utf-8')
    tmp.replace(p)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return {'ok': True, 'caracteres': len(texto)}


def _util(texto: str) -> str:
    """Quita las líneas de plantilla sin completar («- (…)») y las secciones que quedan vacías."""
    salida, titulo, cuerpo = [], None, []

    def volcar():
        if cuerpo:
            salida.extend(([titulo] if titulo else []) + cuerpo)

    for linea in texto.splitlines():
        if re.fullmatch(r'\s*-\s*\(.*\)\s*', linea) or not linea.strip():
            continue
        if linea.lstrip().startswith('#'):
            volcar()
            titulo, cuerpo = linea.strip(), []
        else:
            cuerpo.append(linea.rstrip())
    volcar()
    return '\n'.join(salida).strip()


def para_prompt(max_chars: int = 3000) -> str:
    texto = _util(leer(crear=False))
    if not texto:
        return ''
    return ('Perfil del dueño (lo escribió él; usalo para personalizar, no lo repitas entero):\n' + texto)[:max_chars]


def interpretar(t: str) -> dict | None:
    """t normalizado (sin tildes). «muéstrame mi perfil», «abre mi perfil»."""
    if re.fullmatch(r'(?:muestra(?:me)?|mostra(?:me)?|abre|abri|edita|editar|ver)(?: el)? (?:mi )?perfil', t):
        return {'tipo': 'respuesta', 'proveedor': 'sky-perfil', 'modulo': 'perfil',
                'mensaje': 'Te abro tu perfil. Lo que escribas ahí lo tengo en cuenta en cada respuesta.'}
    return None
