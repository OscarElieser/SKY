"""SKY Visual Creator: UI generativa local basada en parámetros estructurados.

Genera HTML/CSS auténtico, editable y descargable. No afirma generar arte
fotorrealista con un modelo que no está instalado.
"""
from __future__ import annotations
from html import escape
from datetime import datetime
import re,unicodedata

TEMPLATES={
 'landing':{'label':'Página de presentación','sections':['Inicio','Características','Nuestro equipo','Contacto']},
 'portfolio':{'label':'Portafolio creativo','sections':['Galería','Proyectos','Sobre mí','Contacto']},
 'classroom':{'label':'Aula virtual','sections':['Cursos','Lecciones','Recursos','Progreso']},
 'dashboard':{'label':'Panel de indicadores','sections':['Resumen','Métricas','Actividad','Informes']},
 'business':{'label':'Sitio de negocio','sections':['Servicios','Catálogo','Clientes','Contacto']},
 'metaverse':{'label':'Portal del metaverso','sections':['Mundos','Avatares','Comunidad','Studio 3D']},
}
PALETTES={
 'sky':{'bg':'#071426','paper':'#0c2237','accent':'#58d9f5','accent2':'#997bff','text':'#e9f6ff'},
 'nature':{'bg':'#0a211b','paper':'#133b31','accent':'#a2e3b6','accent2':'#dfc17e','text':'#effff0'},
 'sunrise':{'bg':'#221b2d','paper':'#372c47','accent':'#ffb17b','accent2':'#f98fc7','text':'#fff4ed'},
 'minimal':{'bg':'#f5f7f9','paper':'#ffffff','accent':'#1b5471','accent2':'#698493','text':'#122b3c'},
}

def _plain(s,limit):
    if not isinstance(s,str):raise ValueError('Texto inválido')
    # Limpia caracteres de control; luego escapa en HTML.
    return ''.join(c for c in s[:limit] if c=='\n' or ord(c)>=32).strip()

def _guess_template(prompt:str):
    t=unicodedata.normalize('NFKD',prompt.lower()).encode('ascii','ignore').decode()
    if re.search(r'curso|escuela|clase|alumno|capacitaci',t):return 'classroom'
    if re.search(r'panel|dashboard|estadistica|indicador|metricas',t):return 'dashboard'
    if re.search(r'portafolio|galeria|artista|creaciones',t):return 'portfolio'
    if re.search(r'metaverso|mundo|avatar|videojuego',t):return 'metaverse'
    if re.search(r'negocio|tienda|empresa|restaurante|servicios|producto',t):return 'business'
    return 'landing'

def make_experience(prompt:str,options:dict|None=None):
    options=options or {}
    if not isinstance(options,dict):raise ValueError('Configuración inválida')
    prompt=_plain(prompt,6000)
    if not prompt:raise ValueError('Describí la experiencia que querés')
    template=options.get('template') or _guess_template(prompt)
    palette=options.get('palette') or 'sky'
    if template not in TEMPLATES:raise ValueError('Plantilla desconocida')
    if palette not in PALETTES:raise ValueError('Paleta desconocida')
    title=_plain(options.get('title') or prompt[:78],100)
    description=_plain(options.get('description') or prompt,400)
    sections=options.get('sections') or TEMPLATES[template]['sections']
    if not isinstance(sections,list) or len(sections)>9:raise ValueError('Secciones inválidas')
    sections=[_plain(x,65) for x in sections if isinstance(x,str) and x.strip()]
    if not sections:raise ValueError('Se requiere una sección')
    return {'type':'sky-experience','schema_version':1,'title':title,'description':description,
            'template':template,'palette':palette,'sections':sections,
            'design_dna':{'theme':'SKY','responsive':True,'fonts':'system-ui','editable':True},
            'generated_by':'SKY Visual Creator local - plantilla estructurada',
            'limitation':'Diseño generado por reglas; no imágenes ni modelos 3D fotorrealistas.'}

def experience_html(spec:dict)->str:
    if not isinstance(spec,dict) or spec.get('type')!='sky-experience' or spec.get('schema_version')!=1:
        raise ValueError('Proyecto SKY inválido')
    pal=PALETTES.get(spec['palette'])
    if not pal:raise ValueError('Paleta no reconocida')
    t=escape(_plain(spec['title'],100));d=escape(_plain(spec['description'],400))
    sections=[escape(_plain(x,65)) for x in spec['sections']]
    nav=''.join(f'<a href="#s{i}">{name}</a>' for i,name in enumerate(sections))
    tiles=''.join(f'''<section class="tile" id="s{i}"><div class="idx">0{i+1}</div>
        <div class="orb"></div><h2>{name}</h2><p>Explorá, diseñá y ampliá esta sección dentro de SKY.</p>
        <a class="inline" href="#inicio">Volver al inicio →</a></section>''' for i,name in enumerate(sections))
    # No JavaScript insertado por usuario; CSS values salen únicamente de PALETTES.
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t} — SKY Experience</title><style>
:root{{--bg:{pal['bg']};--paper:{pal['paper']};--accent:{pal['accent']};--accent2:{pal['accent2']};--text:{pal['text']};}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font:16px/1.65 system-ui,-apple-system,sans-serif;color:var(--text);background:radial-gradient(ellipse at 80% -15%,var(--paper),transparent 56%),var(--bg)}}
a{{color:inherit;text-decoration:none}}header{{position:sticky;top:0;z-index:5;display:flex;justify-content:space-between;align-items:center;gap:20px;padding:20px clamp(18px,5vw,80px);background:var(--bg);border-bottom:1px solid var(--accent2)}}.logo{{font-weight:900;letter-spacing:.28em;color:var(--accent)}}nav{{display:flex;gap:16px;flex-wrap:wrap;font-size:13px}}nav a:hover{{color:var(--accent)}}main{{max-width:1350px;margin:auto;padding:0 26px 100px}}.hero{{min-height:370px;display:flex;flex-direction:column;justify-content:center;padding:65px 0}}.eyebrow{{color:var(--accent);font-weight:800;letter-spacing:.18em;font-size:12px}}h1{{font-size:clamp(39px,7vw,86px);line-height:1.06;max-width:900px;letter-spacing:-.05em;margin:14px 0}}h1 span{{color:var(--accent)}}.hero p{{max-width:800px;opacity:.82;font-size:clamp(16px,2vw,21px)}}.button{{background:var(--accent);color:var(--bg);display:inline-block;width:max-content;border-radius:12px;padding:12px 24px;font-weight:800;margin-top:16px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}.tile{{border:1px solid var(--accent2);border-radius:23px;background:var(--paper);padding:38px;min-height:275px;position:relative;overflow:hidden}}.tile h2{{font-size:clamp(23px,3vw,36px);letter-spacing:-.03em;margin:22px 0 5px}}.idx{{color:var(--accent);font-size:13px;font-weight:bold}}.tile p{{max-width:350px;opacity:.82}}.orb{{position:absolute;width:110px;height:110px;right:-40px;top:-40px;background:var(--accent2);filter:blur(70px);border-radius:100%}}.inline{{font-size:13px;color:var(--accent);font-weight:700}}footer{{text-align:center;padding:28px;border-top:1px solid var(--accent2);font-size:12px;opacity:.8}}@media(max-width:750px){{.grid{{grid-template-columns:1fr}}header{{display:block}}nav{{padding-top:12px}}.tile{{padding:25px}}}}</style></head>
<body><header><a class="logo" href="#inicio">✦ SKY IA</a><nav>{nav}</nav></header>
<main><div class="hero" id="inicio"><span class="eyebrow">SKY EXPERIENCE · DISEÑO EDITABLE</span><h1>{t}<span>.</span></h1><p>{d}</p><a class="button" href="#s0">Explorar experiencia ↗</a></div><div class="grid">{tiles}</div></main>
<footer>Experiencia exportada desde SKY IA · Diseño local editable · Oscar Elieser Chamorro Guzmán</footer></body></html>'''
