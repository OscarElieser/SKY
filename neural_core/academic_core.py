"""SKY Universal Knowledge & Education Engine (SKY-ACADEMIC-CORE v1.0).

Segundo gran núcleo de inteligencia multidisciplinaria de SKY IA.
Cubre educación inicial, primaria, secundaria, formación técnica (INATEC),
carreras universitarias y posgrados (maestrías y doctorados).
Autoría y visión conceptual: Oscar Elieser Chamorro Guzmán.
"""
from __future__ import annotations
import os, re
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT = Path(__file__).resolve().parents[1]
ACADEMIC_FILE = ROOT / "knowledge" / "sky_academic_core.md"

ACADEMIC_ENGINES = {
    "SKY-MATH": {"name": "Matemáticas y Estadística", "keywords": ["matematica", "matemática", "calculo", "cálculo", "algebra", "álgebra", "geometria", "geometría", "trigonometria", "ecuacion", "derivada", "integral", "estadistica", "probabilidad", "fraccion", "porcentaje"]},
    "SKY-LANG": {"name": "Lengua, Literatura y Redacción", "keywords": ["gramatica", "gramática", "ortografia", "ortografía", "redaccion", "redacción", "sintaxis", "literatura", "novela", "poesia", "ruben dario", "rubén darío", "cuento", "ensayo", "monografia", "monografía"]},
    "SKY-APA": {"name": "Normas APA y Estilos Académicos", "keywords": ["apa", "normas apa", "citacion", "citación", "referencias", "bibliografia", "bibliografía", "mla", "vancouver", "chicago", "ieee", "doi"]},
    "SKY-GEO": {"name": "Geografía, Cartografía y Territorio", "keywords": ["geografia", "geografía", "mapa", "cartografia", "relieve", "hidrografia", "volcan", "volcán", "clima", "nicaragua", "capital", "continente", "gis"]},
    "SKY-HIST": {"name": "Historia Universal y de Nicaragua", "keywords": ["historia", "revolucion", "revolución", "independencia", "colonia", "sandino", "edad media", "antigua", "civilizacion", "guerra"]},
    "SKY-SCI": {"name": "Ciencias Naturales y Biología", "keywords": ["biologia", "biología", "celula", "célula", "genetica", "adn", "ecosistema", "zoologia", "botanica", "fotosintesis", "ecologia"]},
    "SKY-CHEM": {"name": "Química", "keywords": ["quimica", "química", "tabla periodica", "atomo", "átomo", "enlace", "estequiometria", "reaccion quimica", "acido", "solucion", "quimica organica"]},
    "SKY-PHYS": {"name": "Física", "keywords": ["fisica", "física", "newton", "velocidad", "aceleracion", "cinematica", "energia", "trabajo", "termodinamica", "ondas", "electricidad", "fuerza"]},
    "SKY-SPORT": {"name": "Educación Física y Deportes", "keywords": ["deporte", "educacion fisica", "entrenamiento", "futbol", "fútbol", "beisbol", "béisbol", "baloncesto", "atletismo", "nutricion deportiva"]},
    "SKY-LINGUA": {"name": "Idiomas y Lingüística", "keywords": ["ingles", "inglés", "frances", "francés", "portugues", "aleman", "mandarin", "idioma", "traduccion", "miskitu", "gramatica inglesa", "a1", "b2", "c1"]},
    "SKY-COMP": {"name": "Computación y Ofimática", "keywords": ["computacion", "computación", "ofimatica", "ofimática", "excel", "word", "powerpoint", "hoja de calculo", "hardware", "redes"]},
    "SKY-ADMIN": {"name": "Administración y Negocios", "keywords": ["administracion", "administración", "gestion", "gestión", "empresa", "emprendimiento", "plan de negocio", "logistica", "liderazgo"]},
    "SKY-ACCOUNT": {"name": "Contabilidad y Finanzas", "keywords": ["contabilidad", "partida doble", "balance", "estado financiero", "asiento contable", "libro diario", "niif", "impuestos", "auditoria"]},
    "SKY-HR": {"name": "Recursos Humanos", "keywords": ["recursos humanos", "rrhh", "nomina", "nómina", "reclutamiento", "clima laboral", "desempeño", "seguridad e higiene"]},
    "SKY-FASHION": {"name": "Diseño, Patronaje y Moda", "keywords": ["patronaje", "corte y confeccion", "confección", "costura", "tela", "textil", "medidas de cuerpo", "vestido", "diseño de modas"]},
    "SKY-WELD": {"name": "Soldadura y Metalmecánica", "keywords": ["soldadura", "soldar", "metalmecanica", "smaw", "mig", "tig", "electrodo", "metalurgia", "corte de metal"]},
    "SKY-AUTO": {"name": "Mecánica Automotriz y Motos", "keywords": ["mecanica automotriz", "mantenimiento automotriz", "motor", "frenos", "inyeccion", "motocicleta", "bujia", "obd", "caja de cambios"]},
    "SKY-BUILD": {"name": "Construcción y Obras Civiles", "keywords": ["construccion", "construcción", "albañileria", "albañilería", "concreto", "cemento", "plano", "maestro de obras", "cubicacion", "cubicación", "materiales"]},
    "SKY-TOPO": {"name": "Topografía y Geomática", "keywords": ["topografia", "topografía", "estacion total", "curvas de nivel", "altimetria", "planimetria", "nivelacion", "poligonal", "coordenadas utm"]},
    "SKY-EDU": {"name": "Docencia y Didáctica Pedagógica", "keywords": ["pedagogia", "pedagogía", "didactica", "didáctica", "plan de clase", "rubrica", "rúbrica", "planeacion", "unidad didactica", "secuencia didactica", "meidi", "clase"]},
    "SKY-ART": {"name": "Arte, Música y Cultura", "keywords": ["arte", "pintura", "dibujo", "musica", "música", "solfeo", "teatro", "danza", "folclore", "patrimonio cultural"]},
    "SKY-CUSTOMS": {"name": "Aduanas y Comercio Exterior", "keywords": ["aduana", "arancel", "partida arancelaria", "cauca", "recauca", "incoterms", "importacion", "exportacion"]},
    "SKY-MARKETING": {"name": "Marketing y Ventas", "keywords": ["marketing", "mercadotecnia", "publicidad", "branding", "redes sociales", "embudo de ventas", "posicionamiento"]},
    "SKY-RESEARCH": {"name": "Investigación Científica", "keywords": ["investigacion cientifica", "investigación", "tesis", "metodologia", "metodología", "problema de investigacion", "marco teorico", "variables"]},
    "SKY-DOCTORAL": {"name": "Investigación Doctoral y Posgrado", "keywords": ["doctorado", "maestria", "maestría", "epistemologia", "epistemología", "posgrado", "tribunal academico", "publicacion indexada"]}
}

EDUCATIONAL_LEVELS = {
    "inicial": ["preescolar", "kinder", "infantil", "inicial", "niños pequeños", "meidi"],
    "primaria": ["primaria", "primer grado", "segundo grado", "tercer grado", "cuarto grado", "quinto grado", "sexto grado"],
    "secundaria": ["secundaria", "bachillerato", "séptimo", "octavo", "noveno", "décimo", "undécimo"],
    "tecnico": ["tecnico", "técnico", "inatec", "vocacional", "taller", "formacion profesional", "oficio"],
    "universidad": ["universidad", "licenciatura", "ingenieria", "ingeniería", "carrera", "facultad", "pregrado"],
    "posgrado": ["maestria", "maestría", "doctorado", "posgrado", "especialidad", "phd"]
}

def load_academic_prompt() -> str:
    """Carga el texto completo del Master Academic Core desde knowledge/."""
    if not ACADEMIC_FILE.is_file():
        return ""
    try:
        return ACADEMIC_FILE.read_text(encoding="utf-8")
    except Exception:
        return ""

def is_academic_task(area: str, prompt: str = "") -> bool:
    """Detecta si la consulta corresponde al ámbito académico, docente, científico o técnico."""
    combined = f"{area} {prompt}".casefold()
    for engine, data in ACADEMIC_ENGINES.items():
        if any(kw in combined for kw in data["keywords"]):
            return True
    return any(term in combined for term in [
        "aprender", "enseñar", "explicar", "tarea", "profesor", "maestro",
        "docente", "escuela", "colegio", "universidad", "clase", "lección", "curso"
    ])

def detect_engines(text: str) -> List[str]:
    """Identifica qué motores especializados corresponden a la consulta."""
    t = text.casefold()
    matched = []
    for code, data in ACADEMIC_ENGINES.items():
        if any(kw in t for kw in data["keywords"]):
            matched.append(code)
    return matched or ["SKY-EDU"]

def detect_level(text: str) -> str:
    """Identifica el nivel educativo implícito o explícito."""
    t = text.casefold()
    for level, kws in EDUCATIONAL_LEVELS.items():
        if any(kw in t for kw in kws):
            return level
    return "general"

def extract_academic_section(full_text: str, section_number: int) -> str:
    """Extrae una sección numerada del texto del núcleo académico."""
    pattern = rf"###\s+{section_number}\.\s+.*?(?=(?:###\s+\d+\.|\Z))"
    match = re.search(pattern, full_text, flags=re.DOTALL)
    if match:
        return match.group(0).strip()
    return ""

def academic_instructions(area: str, prompt: str = "") -> str:
    """Genera instrucciones personalizadas de educación y rigor académico."""
    if not is_academic_task(area, prompt):
        return ""

    master_text = load_academic_prompt()
    if not master_text:
        return ""

    combined = f"{area} {prompt}".casefold()
    engines = detect_engines(combined)
    level = detect_level(combined)

    parts = [
        "=== SKY UNIVERSAL KNOWLEDGE & EDUCATION ENGINE (MÓDULO ACADÉMICO Y PEDAGÓGICO) ===",
        f"✦ Nivel educativo detectado: {level.upper()} · Motores activados: {', '.join(engines)}",
        extract_academic_section(master_text, 1), # Identidad y Misión
    ]

    # Inyección de motor determinista de cálculo CAS si la consulta incluye matemáticas
    if "SKY-MATH" in engines or any(k in combined for k in ["calcul", "deriv", "integr", "algebra", "ecuaci", "limit"]):
        try:
            from neural_core.math_engine import detectar_y_calcular_en_prompt
            cas_res = detectar_y_calcular_en_prompt(prompt)
            if cas_res and cas_res.get("ok"):
                cas_block = (
                    f"<CALCULO_DETERMINISTA_CAS>\n"
                    f"Operación: {cas_res['operacion'].upper()}\n"
                    f"Expresión analítica: {cas_res['expresion_original']}\n"
                    f"Resultado simbólico exacto: {cas_res['resultado_simbolico']}\n"
                    f"Resultado LaTeX: {cas_res['resultado_latex']}\n"
                    f"Teorema base: {cas_res['teorema']}\n"
                    f"Comprobación determinista: {cas_res['comprobacion']}\n"
                    f"</CALCULO_DETERMINISTA_CAS>\n"
                    f"Directiva estricta: Utiliza este cálculo simbólico verificado por SymPy como base irrefutable para tu desarrollo paso a paso."
                )
                parts.append(cas_block)
        except Exception:
            pass

        math_pillar = (
            "ARQUITECTURA DE MAESTRÍA MATEMÁTICA EN 4 PILARES (SKY-MATH):\n"
            "1. Niveles de Formación Cognitiva:\n"
            "   - Principiante (Aritmética/Álgebra básica): Intuición visual, analogías cotidianas, desglose sin omitir propiedades fundamentales (conmutativa, distributiva, asociativa).\n"
            "   - Medio (Geometría, Trigonometría, Pre-cálculo): Definiciones formales, representaciones gráficas conceptuales y despejes algebraicos explícitos.\n"
            "   - Avanzado (Cálculo diferencial/integral, Álgebra Lineal, EDO): Demostración de condiciones de aplicabilidad de teoremas (ej. Teorema del Valor Medio, Teorema Fundamental del Cálculo), interpretación geométrica y física del problema.\n"
            "   - Superior / Máster (Análisis Real/Complejo, Álgebra Abstracta, Topología): Rigor formal axiomático (ε-δ, espacios de Banach/Hilbert, teoría de grupos/anillos), formato de Lema, Teorema y Demostración estricta (Proof / Q.E.D.).\n"
            "2. Cadena de Pensamiento Obligatoria (Chain of Thought - CoT):\n"
            "   a) Identificar variables, dominio y restricciones del problema.\n"
            "   b) Enunciar explícitamente los teoremas, axiomas o reglas aplicables.\n"
            "   c) Ejecutar el cálculo paso a paso con máxima claridad y pulcritud algebraica.\n"
            "   d) Comprobar el resultado por un método alternativo o evaluar valores en extremos del dominio.\n"
            "3. Notación LaTeX Estricta Obligatoria:\n"
            "   - Fórmulas en línea delimitadas por `$f'(x)$`.\n"
            "   - Ecuaciones en bloque delimitadas por `$$\\int_{a}^{b} f(x) \\, dx$$`.\n"
            "   - Prohibido dejar expresiones matemáticas ambiguas en texto plano."
        )
        parts.append(math_pillar)

    # Inyectar motores especializados pertinentes
    if "SKY-MATH" in engines:
        parts.append(extract_academic_section(master_text, 3))
    if "SKY-LANG" in engines:
        parts.append(extract_academic_section(master_text, 4))
    if "SKY-APA" in engines:
        parts.append(extract_academic_section(master_text, 5))
    if "SKY-GEO" in engines or "SKY-HIST" in engines:
        parts.append(extract_academic_section(master_text, 6))
    if any(e in engines for e in ["SKY-SCI", "SKY-CHEM", "SKY-PHYS"]):
        parts.append(extract_academic_section(master_text, 7))
    if "SKY-SPORT" in engines:
        parts.append(extract_academic_section(master_text, 8))
    if "SKY-LINGUA" in engines:
        parts.append(extract_academic_section(master_text, 9))
    if any(e in engines for e in ["SKY-ADMIN", "SKY-ACCOUNT", "SKY-HR"]):
        parts.append(extract_academic_section(master_text, 11))
    if any(e in engines for e in ["SKY-FASHION", "SKY-WELD", "SKY-AUTO", "SKY-BUILD", "SKY-TOPO"]):
        parts.append(extract_academic_section(master_text, 12))
    if "SKY-EDU" in engines:
        parts.append(extract_academic_section(master_text, 13))
    if any(e in engines for e in ["SKY-ART", "SKY-CUSTOMS", "SKY-MARKETING"]):
        parts.append(extract_academic_section(master_text, 14))
    if any(e in engines for e in ["SKY-RESEARCH", "SKY-DOCTORAL"]):
        parts.append(extract_academic_section(master_text, 15))

    # Adaptación por nivel y reglas permanentes
    parts.append(extract_academic_section(master_text, 16))
    parts.append(extract_academic_section(master_text, 17))

    joined = "\n\n".join(p for p in parts if p)
    if len(joined) > 6500:
        return joined[:6500] + "\n...[SKY-ACADEMIC-CORE DIRECTIVAS ACTIVAS]..."
    return joined

def analyze_academic_request(prompt: str) -> Dict[str, Any]:
    """Analiza una solicitud educativa o técnica identificando nivel, motores y enfoque."""
    engines = detect_engines(prompt)
    level = detect_level(prompt)
    is_acad = is_academic_task("", prompt)

    mode = "Docente"
    p_lower = prompt.casefold()
    if any(w in p_lower for w in ["evalua", "evalúa", "evaluar", "rubrica", "rúbrica", "evaluacion", "evaluación", "examen", "nota"]):
        mode = "Evaluador"
    elif any(w in p_lower for w in ["paso a paso", "guiame", "guíame", "tutor", "no entiendo"]):
        mode = "Tutor"
    elif any(w in p_lower for w in ["investigacion", "investigación", "tesis", "metodologia", "metodología"]):
        mode = "Investigador"
    elif any(w in p_lower for w in ["taller", "manual", "procedimiento", "construir", "soldar", "tecnico", "técnico"]):
        mode = "Profesional Técnico"

    engine_names = [ACADEMIC_ENGINES.get(e, {}).get("name", e) for e in engines]

    return {
        "is_academic": is_acad,
        "educational_level": level,
        "pedagogical_mode": mode,
        "active_engines": engines,
        "engine_names": engine_names
    }

def list_academic_engines() -> List[Dict[str, Any]]:
    """Devuelve la lista estructurada de los 25 motores especializados."""
    return [{"code": k, "name": v["name"]} for k, v in ACADEMIC_ENGINES.items()]
