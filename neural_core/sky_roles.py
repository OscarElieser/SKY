"""SKY Roles: Catálogo multidisciplinario, selección determinista y planes explicables.

Los roles describen enfoques operativos para ayudar al usuario; no confieren licencias
profesionales ni capacidades técnicas que no estén implementadas.
"""
from __future__ import annotations
from dataclasses import dataclass
from unicodedata import normalize
import re

@dataclass(frozen=True)
class Role:
    id: str
    title: str
    description: str
    keys: tuple[str,...]
    skills: tuple[str,...]

# Un catálogo versionado, extensible. Nunca ejecutar código arbitrario descubierto en texto.
_ROLES=(
    ('general','Asistente personal','Coordina tareas, preferencias y proyectos','asistente agenda plan general ayuda personal','plan,calcular,memoria'),
    ('educacion','Docente y diseñador didáctico','Diseña secuencias formativas y evaluaciones','clase curso docencia educativo estudiante escuela capacitacion aprendizaje didactica','plan,documento,presentacion'),
    ('investigacion','Investigador','Diseña preguntas, metodología y revisión de evidencias','investigacion tesis articulo paper evidencia metodologia bibliografia fuentes estudio','plan,documento'),
    ('negocios','Estratega de negocios','Modela propuestas comerciales y clientes','negocio emprendimiento empresa ventas clientes rentabilidad estrategia plan comercial','plan,presupuesto,documento'),
    ('finanzas','Analista financiero','Prepara presupuestos, escenarios y riesgos','dinero inversion presupuesto finanzas ingresos gastos ahorro deuda rentabilidad','presupuesto,calcular,plan'),
    ('contabilidad','Asistente contable','Organiza información de ingresos, egresos y conciliación','contabilidad factura balance contable nomina impuestos costos','presupuesto,documento'),
    ('bolsa','Analista de mercados','Organiza análisis de bolsa e información verificable','bolsa acciones dividendos etf cotizacion mercado financiero portafolio trading','plan,calcular'),
    ('cripto','Analista de criptoactivos','Evalúa escenarios, volatilidad y custodia','bitcoin cripto ethereum blockchain token stablecoin defi wallet','plan,calcular'),
    ('marketing','Estratega de marketing','Define públicos, oferta, mensajes y campañas','marketing publicidad posicionamiento campaña conversion publicidad marca seo','plan,presentacion,diseno'),
    ('redes','Creador para redes sociales','Prepara calendarios, guiones y materiales sociales','tiktok instagram facebook youtube reels hashtag viral seguidores redes sociales','plan,documento,diseno'),
    ('diseño','Diseñador visual','Crea estructuras editables, estilos y sistemas de identidad','diseno diseño visual poster cartel branding logotipo paleta interfaz ui ux','diseno,plan'),
    ('web','Desarrollador web','Plantea interfaces y componentes funcionales','sitio web pagina landing frontend html css javascript accesibilidad','diseno,plan'),
    ('programacion','Ingeniero de software','Descompone soluciones técnicas y pruebas','programar codigo api python backend software debugging flutter dart android','plan,documento'),
    ('datos','Analista de datos','Explora indicadores y tablas verificables','datos analisis estadistica dashboard excel csv kpi metricas dataset','presupuesto,calcular,documento'),
    ('inteligencia_artificial','Ingeniero de IA','Orquesta modelos, herramientas y evaluaciones','inteligencia artificial ia machine learning neural gru mlp rag llm agentes','plan,documento'),
    ('ciberseguridad','Analista defensivo','Revisa protección, permisos, riesgos y auditoría autorizada','seguridad antivirus virus malware hacking hackear auditoria vulnerabilidad defensa','plan,documento'),
    ('3d','Artista 3D','Planifica piezas, escenas, texturas y exportación','3d blender modelo tridimensional escultura malla textura objeto foto','mundo,diseno,plan'),
    ('metaverso','Arquitecto de mundos','Diseña experiencias, avatares y entornos virtuales','metaverso mundo avatar virtual inmersivo escenario realidad virtual vr','mundo,diseno,plan'),
    ('videojuegos','Diseñador de videojuegos','Organiza mecánicas, misiones, progresión y pruebas','videojuego juego gamificacion npc mision personaje jugador motor de juego','mundo,plan,documento'),
    ('audiovisual','Productor audiovisual','Plantea secuencias, grabación y edición audiovisual','video pelicula cine guion escena rodaje animacion trailer','plan,presentacion'),
    ('musica','Productor musical','Estructura proyectos sonoros y criterios creativos','musica cancion produccion musical melodia ritmo audio mezcla','plan,documento'),
    ('comunidad','Gestor de comunidades','Promueve experiencias sociales y convivencia','comunidad red social usuarios chat social avatar seguidores moderacion','plan,mundo'),
    ('salud','Educador en salud','Organiza información general y fuentes clínicas','salud medico medicamento sintomas nutricion bienestar ejercicio tratamiento','plan,documento'),
    ('deporte','Analista deportivo','Organiza entrenamiento y lectura de resultados','deporte futbol beisbol baloncesto partido entrenamiento equipo torneo','plan,documento'),
    ('viajes','Planificador de viajes','Diseña recorridos y requisitos verificables','turismo viaje destinos mapa ruta hospedaje hotel guia baqueano','plan,mundo,documento'),
    ('legal','Asistente jurídico informativo','Ayuda a estructurar documentos sin reemplazar asesoría legal','contrato ley registro legal marca autoria licencia derecho patente','documento,plan'),
    ('proyectos','Director de proyectos','Desglosa hitos, dependencias y entregables','proyecto gestion cronograma tareas roadmap entregables prioridades','plan,presentacion'),
    ('automatizacion','Arquitecto de automatizaciones','Diseña flujos y permisos entre servicios','automatizar automatizacion workflow robots proceso tarea recurrente','plan,documento'),
    ('documentos','Editor de documentos','Crea y estructura contenido exportable','word pdf documento carta informe memorando presentacion powerpoint','documento,presentacion'),
    ('excel','Especialista en hojas de cálculo','Estructura tablas, datos, presupuestos y fórmulas','excel hoja calculo xlsx tabla formula spreadsheet','presupuesto,calcular'),
    ('noticias','Analista de actualidad','Resume hechos citados separando rumor de evidencia','noticias actualidad periodismo politica acontecimientos prensa','plan,documento'),
    ('innovacion','Facilitador de innovación','Diseña experimentos y prototipos medibles','innovacion inventor hackathon prototipo experimento emprendimiento tecnologico','plan,diseno'),
    ('baqueano','Administrador técnico de BAQUEANO','Prepara mejoras del ecosistema BAQUEANO con revisión','baqueano nicaragua sitio destino turista emprendedores ops center','plan,documento'),
)
ROLES={a:Role(a,b,c,tuple(k.split()),tuple(s.split(','))) for a,b,c,k,s in _ROLES}

def _norm(value:str)->str:
    return normalize('NFKD',str(value).lower()).encode('ascii','ignore').decode('ascii')

def select_roles(text:str,max_roles:int=3)->list[dict]:
    if not isinstance(text,str) or not text.strip():raise ValueError('Describí tu tarea')
    if len(text)>8000:raise ValueError('Solicitud demasiado extensa')
    tokens=set(re.findall(r'[a-z0-9]+',_norm(text)))
    phrase=' '.join(_norm(text).split())
    ranks=[]
    for role in ROLES.values():
        score=sum(3 if len(k)>5 else 2 for k in role.keys if k in tokens)
        # Frases distintivas, no palabras genéricas como 'de', 'para'.
        if role.id=='redes' and ('redes sociales' in phrase or 'social media' in phrase):score+=7
        if role.id=='inteligencia_artificial' and 'inteligencia artificial' in phrase:score+=7
        if role.id=='metaverso' and 'metaverso' in phrase:score+=7
        if role.id=='baqueano' and 'baqueano' in phrase:score+=12
        if score:ranks.append((score,role.id))
    ranks.sort(key=lambda x:(-x[0],x[1]))
    selected=[ROLES[i] for _,i in ranks[:min(max(max_roles,1),5)]] or [ROLES['general']]
    return [{'id':r.id,'title':r.title,'description':r.description,'skills':list(r.skills)} for r in selected]

def plan_for(task:str, selected=None)->dict:
    roles=selected or select_roles(task)
    skills=set(s for role in roles for s in role['skills'])
    stages=[{'step':1,'name':'Definir objetivo y resultado verificable','status':'pendiente'},
            {'step':2,'name':'Revisar datos disponibles y limitaciones','status':'pendiente'},
            {'step':3,'name':'Preparar entregable o prototipo mediante herramientas SKY','status':'pendiente'},
            {'step':4,'name':'Comprobar resultado, calidad y permisos','status':'pendiente'}]
    return {'request':task,'roles':roles,'skills_suggested':sorted(skills),'steps':stages,
       'policy':'Las acciones sobre equipos, dinero, publicación y datos de terceros requieren permisos y confirmación. Las funciones externas pueden requerir credenciales.'}
