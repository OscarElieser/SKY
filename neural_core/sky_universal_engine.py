"""SKY Universal Intelligence Engine (v12.0).

Núcleo central de razonamiento universal, planificación adaptativa,
enrutamiento global de fuentes primarias y coordinación multimodelo.

Reglas permanentes:
- Modos: rápido (fast), profundo (deep), investigación (research), desarrollo (dev).
- Global Source Router: fuentes internacionales primarias (ONU, OMS, UNESCO, Banco Mundial, etc.).
- Sin alucinaciones de citas, estadísticas ni fuentes inventadas.
- Adaptación a 7 niveles académicos (inicial a doctorado) y normas APA explícitas.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple


class OperationMode(str, Enum):
    FAST = "fast"
    DEEP = "deep"
    RESEARCH = "research"
    DEV = "dev"


class AcademicLevel(str, Enum):
    INICIAL = "inicial"
    PRIMARIA = "primaria"
    SECUNDARIA = "secundaria"
    TECNICO = "tecnico"
    UNIVERSITARIO = "universitario"
    MAESTRIA = "maestria"
    DOCTORADO = "doctorado"


@dataclass
class SourceReference:
    entidad: str
    pais_o_region: str
    categoria: str
    url_base: str
    descripcion: str
    es_oficial: bool = True


# ==============================================================================
# GLOBAL SOURCE ROUTER: Directorio de fuentes primarias y oficiales mundiales
# ==============================================================================
GLOBAL_SOURCES_REGISTRY: Dict[str, List[SourceReference]] = {
    "salud": [
        SourceReference("OMS / WHO", "Global", "Salud Internacional", "https://www.who.int", "Directrices mundiales de salud pública y epidemiología"),
        SourceReference("OPS / PAHO", "América", "Salud Regional", "https://www.paho.org", "Organización Panamericana de la Salud"),
        SourceReference("PubMed / NCBI", "Global", "Investigación Biomédica", "https://pubmed.ncbi.nlm.nih.gov", "Base de datos biomédica con revisión por pares"),
        SourceReference("CDC", "Estados Unidos", "Control Epidemiológico", "https://www.cdc.gov", "Centros para el Control y Prevención de Enfermedades"),
    ],
    "economia": [
        SourceReference("Banco Mundial / World Bank", "Global", "Desarrollo Económico", "https://www.worldbank.org", "Indicadores de desarrollo económico y social"),
        SourceReference("FMI / IMF", "Global", "Finanzas Internacionales", "https://www.imf.org", "Informes de estabilidad financiera y perspectivas mundiales"),
        SourceReference("OCDE / OECD", "Global", "Políticas Económicas", "https://www.oecd.org", "Estudios económicos y gobernanza comparada"),
        SourceReference("BCN", "Nicaragua", "Banca Central", "https://www.bcn.gob.ni", "Banco Central de Nicaragua: estadísticas macroeconómicas y tipo de cambio"),
    ],
    "estadistica": [
        SourceReference("UN Data / ONU Datos", "Global", "Estadística Mundial", "https://data.un.org", "Repositorio unificado de estadísticas de Naciones Unidas"),
        SourceReference("INIDE", "Nicaragua", "Censos y Estadísticas", "https://www.inide.gob.ni", "Instituto Nacional de Información de Desarrollo de Nicaragua"),
        SourceReference("Eurostat", "Europa", "Estadística Europea", "https://ec.europa.eu/eurostat", "Oficina estadística de la Unión Europea"),
        SourceReference("US Census Bureau", "Estados Unidos", "Demografía", "https://www.census.gov", "Datos demográficos y económicos oficiales"),
    ],
    "ciencia": [
        SourceReference("arXiv", "Global", "Preprints Científicos", "https://arxiv.org", "Física, matemáticas, computación y biología cuantitativa"),
        SourceReference("Crossref", "Global", "Metadatos Académicos", "https://www.crossref.org", "Registro global de DOI para publicaciones académicas"),
        SourceReference("NASA", "Global", "Aeroespacial y Clima", "https://www.nasa.gov", "Datos de misiones espaciales y ciencia climática"),
        SourceReference("Nature / Science Indices", "Global", "Revistas de Alto Impacto", "https://www.nature.com", "Publicaciones científicas evaluadas"),
    ],
    "educacion": [
        SourceReference("UNESCO", "Global", "Educación y Cultura", "https://www.unesco.org", "Informes mundiales de educación y patrimonio cultural"),
        SourceReference("UNICEF", "Global", "Infancia y Educación", "https://www.unicef.org", "Políticas educativas y desarrollo infantil"),
        SourceReference("INATEC", "Nicaragua", "Formación Técnica", "https://www.tecnacional.edu.ni", "Educación técnica y tecnológica de Nicaragua"),
        SourceReference("MINED", "Nicaragua", "Educación Básica", "https://www.mined.gob.ni", "Ministerio de Educación de Nicaragua"),
    ],
    "deporte": [
        SourceReference("FIFA", "Global", "Fútbol Mundial", "https://www.fifa.com", "Reglamentos y competiciones internacionales de fútbol"),
        SourceReference("UEFA", "Europa", "Fútbol Europeo", "https://www.uefa.com", "Champions League y torneos europeos"),
        SourceReference("LaLiga EA Sports", "España", "Fútbol Profesional", "https://www.laliga.com", "Calendarios, actas y estadísticas oficiales"),
        SourceReference("COI / IOC", "Global", "Olimpismo", "https://olympics.com", "Comité Olímpico Internacional"),
    ],
    "tecnologia": [
        SourceReference("W3C", "Global", "Estándares Web", "https://www.w3.org", "Estándares de HTML, CSS, accesibilidad y APIs web"),
        SourceReference("Python Software Foundation", "Global", "Documentación Lenguaje", "https://docs.python.org", "Referencia oficial del lenguaje Python"),
        SourceReference("MDN Web Docs", "Global", "Desarrollo Frontend", "https://developer.mozilla.org", "Documentación de estándares web de Mozilla"),
        SourceReference("GitHub Docs", "Global", "Versionado y CI/CD", "https://docs.github.com", "Guías oficiales de Git y GitHub Actions"),
    ],
    "legislacion": [
        SourceReference("ONU Tratados", "Global", "Derecho Internacional", "https://treaties.un.org", "Colección de tratados de Naciones Unidas"),
        SourceReference("La Gaceta Diario Oficial", "Nicaragua", "Legislación Nacional", "https://www.lagaceta.gob.ni", "Publicación oficial de leyes y decretos de Nicaragua"),
        SourceReference("EUR-Lex", "Europa", "Derecho Comunitario", "https://eur-lex.europa.eu", "Acceso al derecho de la Unión Europea"),
    ]
}


@dataclass
class ExecutionPlan:
    modo: OperationMode
    disciplina: str
    nivel_academico: AcademicLevel
    requiere_investigacion: bool
    requiere_calculo_determinista: bool
    requiere_codigo: bool
    fuentes_recomendadas: List[SourceReference]
    formato_citas: str = "APA 7ª edición"
    pasos: List[str] = field(default_factory=list)


class SkyUniversalEngine:
    """Motor de inteligencia universal para clasificación, enrutamiento y planificación."""

    @classmethod
    def clasificar_intencion(cls, texto: str, area: str = "General") -> ExecutionPlan:
        """Determina el modo operativo, disciplina, nivel cognitivo y necesidades de verificación."""
        t = f"{area} {texto}".lower()
        
        # 1. Detección de Modo Operativo
        if any(w in t for w in ["código", "codigo", "programa", "fastapi", "python", "bug", "refactor", "docker", "test", "algoritmo"]):
            modo = OperationMode.DEV
        elif any(w in t for w in ["investiga", "fuentes", "año", "fecha", "población", "poblacion", "noticia", "actual", "estadística", "estadistica", "ley", "estudio"]):
            modo = OperationMode.RESEARCH
        elif any(w in t for w in ["explica a fondo", "demuestra", "deriva", "teorema", "análisis exhaustivo", "tesis", "por qué ocurre", "doctorado", "maestría"]):
            modo = OperationMode.DEEP
        else:
            modo = OperationMode.FAST

        # 2. Detección de Disciplina
        disciplina = "general"
        if any(w in t for w in ["salud", "médic", "medic", "enfermedad", "síntoma", "tratamiento", "dosis", "fármaco"]):
            disciplina = "salud"
        elif any(w in t for w in ["economía", "economia", "inflación", "pib", "banco", "dólar", "fmi", "finanzas"]):
            disciplina = "economia"
        elif any(w in t for w in ["censo", "habitantes", "demografía", "tasa", "inide", "estadística"]):
            disciplina = "estadistica"
        elif any(w in t for w in ["física", "fisica", "química", "quimica", "biología", "biologia", "astro", "átomo", "nasa", "cuántica"]):
            disciplina = "ciencia"
        elif any(w in t for w in ["fútbol", "futbol", "real madrid", "champions", "deporte", "partido", "laliga"]):
            disciplina = "deporte"
        elif any(w in t for w in ["software", "python", "react", "código", "base de datos", "sql", "api", "algoritmo"]):
            disciplina = "tecnologia"
        elif any(w in t for w in ["ley", "código penal", "constitución", "decreto", "artículo", "derecho"]):
            disciplina = "legislacion"
        elif any(w in t for w in ["educación", "enseñar", "aula", "pedagogía", "didáctica", "colegio"]):
            disciplina = "educacion"

        # 3. Detección de Nivel Académico
        nivel = AcademicLevel.UNIVERSITARIO
        if any(w in t for w in ["niño", "infantil", "inicial", "preescolar", "kinder"]):
            nivel = AcademicLevel.INICIAL
        elif any(w in t for w in ["primaria", "para un niño de 8", "sencillo", "como a un niño"]):
            nivel = AcademicLevel.PRIMARIA
        elif any(w in t for w in ["secundaria", "bachillerato", "preparatoria"]):
            nivel = AcademicLevel.SECUNDARIA
        elif any(w in t for w in ["técnico", "tecnico", "formación técnica", "taller", "electricidad básica"]):
            nivel = AcademicLevel.TECNICO
        elif any(w in t for w in ["maestría", "maestria", "posgrado"]):
            nivel = AcademicLevel.MAESTRIA
        elif any(w in t for w in ["doctorado", "phd", "peer-reviewed", "revisión por pares", "epistemología"]):
            nivel = AcademicLevel.DOCTORADO

        # 4. Necesidades de Cálculo y Código
        requiere_calc = any(w in t for w in ["calcula", "deriva", "integra", "matriz", "ecuación", "suma", "cuánto es", "raiz", "evalúa"])
        requiere_codigo = (modo == OperationMode.DEV or any(w in t for w in ["script", "función", "clase", "def ", "import "]))
        requiere_inv = (modo == OperationMode.RESEARCH or disciplina in ["salud", "economia", "estadistica", "legislacion"])

        # 5. Enrutamiento de Fuentes Globales
        fuentes = GLOBAL_SOURCES_REGISTRY.get(disciplina, [])

        # 6. Pasos del Plan de Ejecución
        pasos = [
            f"1. Comprensión contextual: Disciplina={disciplina}, Nivel={nivel.value}, Modo={modo.value}.",
        ]
        if requiere_inv:
            pasos.append(f"2. Consulta de fuentes primarias recomendadas: {', '.join([f.entidad for f in fuentes[:3]])}.")
        if requiere_calc:
            pasos.append("3. Ejecución determinista de cálculo mediante CAS SymPy (anti-alucinación numérica).")
        if requiere_codigo:
            pasos.append("4. Síntesis de código profesional cumpliendo estándar DEV-CORE (Big-O, Zero Placeholders).")
        pasos.append("5. Verificación de exactitud factual y consistencia lógica.")

        return ExecutionPlan(
            modo=modo,
            disciplina=disciplina,
            nivel_academico=nivel,
            requiere_investigacion=requiere_inv,
            requiere_calculo_determinista=requiere_calc,
            requiere_codigo=requiere_codigo,
            fuentes_recomendadas=fuentes,
            formato_citas="APA 7ª edición",
            pasos=pasos
        )

    @classmethod
    def directivas_universales(cls, plan: ExecutionPlan) -> str:
        """Genera el bloque de directivas para inyectar al asistente según el plan."""
        fuentes_txt = "\n".join([f"  - [{f.entidad}] ({f.pais_o_region}): {f.descripcion} -> {f.url_base}" for f in plan.fuentes_recomendadas])
        
        citas_apa = (
            "✦ REGLAS DE CITACIÓN Y NORMAS APA (7ª EDICIÓN):\n"
            "- Cita siempre fuentes verificables en formato APA (Autor, Año). Si es web oficial: Organización (Año). Título. URL.\n"
            "- PROHIBICIÓN ABSOLUTA: Nunca inventes autores, títulos, años de publicación ni enlaces. Si una cifra no tiene fuente exacta, indícalo explícitamente: «Fuente no confirmada o dato aproximado pendiente de verificación».\n"
            "- No inventes porcentajes de confianza falsos (ej. '99.4% seguro'). Expresa el grado de certidumbre según la evidencia disponible."
        )

        nivel_txt = f"✦ ADAPTACIÓN PEDAGÓGICA Y COGNITIVA: Nivel {plan.nivel_academico.value.upper()}.\n"
        if plan.nivel_academico in (AcademicLevel.INICIAL, AcademicLevel.PRIMARIA):
            nivel_txt += "- Usa analogías cotidianas, vocabulario cálido, claro, sin jerga abstracta innecesaria."
        elif plan.nivel_academico == AcademicLevel.TECNICO:
            nivel_txt += "- Enfócate en la aplicación práctica, pasos secuenciales, normas de seguridad y manuales de taller."
        elif plan.nivel_academico in (AcademicLevel.MAESTRIA, AcademicLevel.DOCTORADO):
            nivel_txt += "- Emplea rigor metodológico, análisis epistemológico, referencias a literatura revisada por pares y discusión de limitaciones."
        else:
            nivel_txt += "- Equilibrio profesional universitario: conceptos fundamentales sólidos, precisión técnica y claridad explicativa."

        salud_legal_disclaimer = ""
        if plan.disciplina == "salud":
            salud_legal_disclaimer = (
                "\n✦ ADVERTENCIA MÉDICA INFORMATIVA:\n"
                "- La información brindada es estrictamente divulgativa y educativa basada en fuentes como la OMS o PubMed.\n"
                "- No sustituye el diagnóstico, receta ni criterio de un profesional médico colegiado. Recomienda siempre consultar a un especialista de la salud."
            )
        elif plan.disciplina == "legislacion":
            salud_legal_disclaimer = (
                "\n✦ ADVERTENCIA JURÍDICA INFORMATIVA:\n"
                "- La información jurídica es meramente referencial y explicativa de leyes vigentes o doctrinas.\n"
                "- No constituye asesoría legal vinculante. Los procedimientos formales requieren la intervención de un abogado o notario autorizado."
            )

        return (
            f"=== SKY UNIVERSAL INTELLIGENCE ENGINE (v12.0) ===\n"
            f"Modo: {plan.modo.value.upper()} | Disciplina: {plan.disciplina.upper()} | Nivel: {plan.nivel_academico.value.upper()}\n"
            f"{nivel_txt}\n\n"
            f"{citas_apa}\n"
            f"{salud_legal_disclaimer}\n"
            f"✦ FUENTES PRIMARIAS Y OFICIALES PRIORITARIAS:\n{fuentes_txt if fuentes_txt else '  - Motores de búsqueda globales y fuentes oficiales del país respectivo.'}\n"
            f"✦ DIRECTIVAS DE INVESTIGACIÓN Y RECONOCIMIENTO DE LÍMITES:\n"
            "- Si una pregunta requiere datos actualizados, consulta fuentes contrastadas de cualquier país del mundo.\n"
            "- Si la evidencia es insuficiente, reconócelo sin rodeos. La precisión siempre prevalece sobre la velocidad."
        )
