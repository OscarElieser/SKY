"""Motor procedural 3D SKY: escenas originales a partir de instrucciones escritas.
Funciona sin internet ni proveedores LLM. No reconstruye entornos reales desde fotos.
"""
from __future__ import annotations
import random, uuid, math, re
from typing import Any

KINDS = {'box','sphere','cylinder','cone','tree','house','palm','torus','rock','tower','platform'}
PALETTES = {
    'bosque':['#3D8B69','#59A68B','#215B43','#D2A376','#E8D4AA'],
    'playa':['#F6CC78','#EFBA63','#4EABA4','#D7E6C0','#DF9E59'],
    'ciudad':['#6C91BA','#9CACBE','#52677B','#D7DFE5','#FFB86D'],
    'espacio':['#8069CE','#BA83E3','#56B8CA','#FA9F72','#A2A1EB'],
    'estudio':['#3A90A6','#85B5AE','#BFDCD7','#C8A878','#F7C49E'],
}

def _hex(value: str) -> str:
    if not isinstance(value,str) or not re.fullmatch(r'#[A-Fa-f0-9]{6}',value):
        raise ValueError('El color debe ser hexadecimal, como #3488DD')
    return value.upper()

def _vector(value, *, positive: bool = False) -> list[float]:
    if not isinstance(value, (tuple,list)) or len(value)!=3: raise ValueError('Coordenadas XYZ incorrectas')
    v=[float(x) for x in value]
    if not all(math.isfinite(x) and abs(x)<=100 for x in v):raise ValueError('Coordenadas fuera de rango')
    if positive and not all(.05<=x<=100 for x in v):raise ValueError('Escala positiva requerida')
    return v

def validate_object(raw:dict[str,Any])->dict[str,Any]:
    if not isinstance(raw,dict):raise ValueError('Objeto inválido')
    kind=raw.get('kind','box')
    if kind not in KINDS:raise ValueError('Forma 3D no permitida')
    name=str(raw.get('name',kind)).strip()[:55]
    if not name:raise ValueError('Nombre vacío')
    oid=str(raw.get('id') or uuid.uuid4().hex)
    if not re.fullmatch('[A-Za-z0-9_-]{1,64}',oid):raise ValueError('ID inválido')
    return {'id':oid,'name':name,'kind':kind,
            'position':_vector(raw.get('position',[0,0,0])),
            'rotation':_vector(raw.get('rotation',[0,0,0])),
            'scale':_vector(raw.get('scale',[1,1,1]),positive=True),
            'color':_hex(raw.get('color','#56B8CA'))}

def object3d(name, kind, x,y,z,sx,sy,sz,color,rot_y=0.0):
    return validate_object({'name':name,'kind':kind,'position':[x,y,z],
                            'scale':[sx,sy,sz],'rotation':[0,rot_y,0], 'color':color})

def theme_of(prompt:str):
    p=prompt.casefold()
    if any(s in p for s in ('playa',' mar ','costa','isla','oceano','océano','tropical')):return 'playa'
    if any(s in p for s in ('ciudad','edificio','rascacielos','edificios','urbano','negocios','metrópoli','metropoli')):return 'ciudad'
    if any(s in p for s in ('espacio','planeta','galaxia','universo','marte','luna','nave espacial')):return 'espacio'
    if any(s in p for s in ('bosque','selva','naturaleza','montaña','montana')) or re.search(r'\b(árbol|arbol|río|rio)\b',p):return 'bosque'
    return 'estudio'

def generate_scene(prompt:str, seed:int=42)->dict:
    if not 1<=len(prompt.strip())<=1000:raise ValueError('Descripción de 1 a 1000 caracteres')
    if not -2**31<=seed<=2**31-1:raise ValueError('Semilla inválida')
    rng=random.Random(seed)
    theme=theme_of(prompt)
    palette=PALETTES[theme]
    obj=[]
    def add(name,kind,x,y,z,sx,sy,sz,color,ry=0):
        obj.append(object3d(name,kind,x,y,z,sx,sy,sz,color,ry))
    add('Terreno SKY','platform',0,-.3,0,38,.35,38,
        {'bosque':'#437655','playa':'#E2C083','ciudad':'#526373','espacio':'#242744','estudio':'#42516B'}[theme])
    if theme=='bosque':
        for i in range(24):
            x,z=rng.uniform(-16,16),rng.uniform(-16,16)
            if abs(x)<3 and abs(z)<3:continue
            add(f'Árbol {i+1}','tree',x,0,z,rng.uniform(.75,1.3),rng.uniform(2.3,4.2),rng.uniform(.75,1.3),rng.choice(palette[:3]))
        add('Refugio SKY','house',0,0,1,3.5,3,3.5,'#D5AC7E')
        add('Piedra del sendero','rock',4,0,4,2,1.3,1.8,'#A9ACA2')
    elif theme=='playa':
        add('Laguna turquesa','platform',-8,-.1,0,15,.06,34,'#329BB9')
        for i in range(16):
            x=rng.uniform(0,16);z=rng.uniform(-16,16)
            add(f'Palmera {i+1}','palm',x,0,z,1,2.8+rng.random(),1,'#35A784')
        for i in range(4):add(f'Kiosco {i+1}','house',3+i*3,0,10,2.2,2.4,2.3,'#E5A15D')
    elif theme=='ciudad':
        add('Avenida central','platform',0,-.08,0,3,.09,38,'#293E55')
        for i in range(-3,4):
            for j in range(-3,4):
                if i==0 or j==0: continue
                height=rng.uniform(2.8,11)
                add(f'Edificio {i}:{j}','tower',i*4.5,0,j*4.5,2.8,height,2.8,rng.choice(palette[:4]))
        add('Sede SKY','tower',0,0,0,3.2,9,3.2,'#48C9D6')
    elif theme=='espacio':
        for i in range(15):
            x,y,z=rng.uniform(-14,14),rng.uniform(1,8),rng.uniform(-14,14)
            add(f'Astro {i+1}','sphere',x,y,z,*([rng.uniform(.4,2)]*3),rng.choice(palette))
        add('Portal orbital','torus',0,3,0,5,5,.6,'#67D7EF')
        add('Estación SKY','house',0,0,4,4,3,3,'#B5C5E2')
    else:
        add('SKY central','tower',0,0,0,4,5,4,'#4AC5E1')
        add('Laboratorio 3D','house',-7,0,-4,5,3.5,4,'#B2D6D9')
        add('Innovación','house',7,0,-4,5,3.5,4,'#D7B68B')
        add('Galería audiovisual','house',-7,0,6,5,3.5,4,'#9B8BCE')
        add('Centro de negocios','house',7,0,6,5,3.5,4,'#8AB0CA')
        for i in range(8):
            a=i*math.tau/8
            add(f'Orbe creativo {i+1}','sphere',math.cos(a)*5,2.5,math.sin(a)*5,.65,.65,.65,rng.choice(palette))
    return {'prompt':prompt,'theme':theme,'seed':seed,'objects':obj,
            'sky':{'bosque':'#9ACBD6','playa':'#87CBEA','ciudad':'#9EB2CF','espacio':'#11172F','estudio':'#11253E'}[theme]}
