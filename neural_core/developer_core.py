"""SKY Developer Intelligence Core (SKY-DEVELOPER-CORE v1.0).

Módulo maestro de ingeniería de software para SKY IA v11.0.
Carga, modula e inyecta directivas avanzadas de arquitectura, programación,
bases de datos, DevOps, ciberseguridad y análisis de repositorios.
Autoría y visión conceptual: Oscar Elieser Chamorro Guzmán.
"""
from __future__ import annotations
import os, re
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT = Path(__file__).resolve().parents[1]
CORE_FILE = ROOT / "knowledge" / "sky_developer_core.md"

DEV_KEYWORDS = {
    # General & Desarrollo
    "código", "codigo", "programación", "programacion", "programar", "programador",
    "compilar", "compilador", "desarrollar", "desarrollo", "software",
    "script", "función", "funcion", "clase", "algoritmo", "refactor", "bug", "error",
    # Frontend & Web
    "frontend", "backend", "full stack", "fullstack", "web", "html", "css", "javascript",
    "typescript", "react", "next.js", "nextjs", "vue", "angular", "svelte", "tailwind",
    # Backend & APIs
    "api", "rest", "graphql", "fastapi", "django", "flask", "express", "node", "nestjs",
    "spring boot", "laravel", "jwt", "oauth", "microservicios",
    # Móvil & Desktop
    "android", "ios", "flutter", "dart", "kotlin", "swift", "react native", "electron", "tauri",
    # Bases de Datos
    "base de datos", "database", "sql", "postgres", "postgresql", "mysql", "sqlite",
    "mongodb", "redis", "supabase", "firebase", "orm", "prisma", "sqlalchemy",
    # DevOps, Cloud & Infraestructura
    "devops", "cloud", "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "ci/cd",
    "github actions", "terraform", "nginx", "hosting", "servidor",
    # IA, ML & Ciberseguridad
    "machine learning", "deep learning", "llm", "rag", "embeddings", "seguridad",
    "ciberseguridad", "owasp", "vulnerabilidad", "testing", "pytest", "jest"
}

def load_master_prompt() -> str:
    """Carga el texto completo del Master Developer Core desde knowledge/."""
    if not CORE_FILE.is_file():
        return ""
    try:
        return CORE_FILE.read_text(encoding="utf-8")
    except Exception:
        return ""

def is_developer_task(area: str, prompt: str = "") -> bool:
    """Detecta si la consulta corresponde a ingeniería de software o desarrollo."""
    combined = f"{area} {prompt}".casefold()
    from .sky_programming_capabilities import detect_languages
    return any(kw in combined for kw in DEV_KEYWORDS) or any(
        name not in {"C", "R", "Go", "Java", "SQL", "CSS", "JSON", "XML", "YAML", "TOML"}
        for name in detect_languages(combined)
    )

def extract_thematic_section(full_text: str, section_number: int) -> str:
    """Extrae una sección específica del prompt maestro por número de sección."""
    pattern = rf"###\s+{section_number}\.\s+.*?(?=(?:###\s+\d+\.|\Z))"
    match = re.search(pattern, full_text, flags=re.DOTALL)
    if match:
        return match.group(0).strip()
    return ""

def developer_instructions(area: str, prompt: str = "") -> str:
    """Inyecta de forma modular las instrucciones del Developer Core pertinentes al contexto.
    
    Respeta el límite de caracteres para evitar saturación de la ventana de contexto.
    """
    if not is_developer_task(area, prompt):
        return ""

    master_text = load_master_prompt()
    if not master_text:
        return ""

    combined = f"{area} {prompt}".casefold()
    
    # 1. Base esencial siempre presente (Identidad, Misión y Directiva Central)
    sec_1 = extract_thematic_section(master_text, 1) # Identidad y Misión
    sec_24 = extract_thematic_section(master_text, 24) # Principios Irrenunciables
    sec_25 = extract_thematic_section(master_text, 25) # Directiva Central

    dev_protocol = (
        "PROTOCOLO DE RESPUESTA OBLIGATORIO (DEV-CORE):\n"
        "1. ANÁLISIS PREVIO Y ENFOQUE:\n"
        "   - Identifica el problema central, requerimientos técnicos y restricciones de rendimiento o entorno.\n"
        "   - Si involucra algoritmos, declara explícitamente la complejidad temporal y espacial esperada en notación Big-O: O(f(n)).\n"
        "2. CÓDIGO FUENTE DE PRODUCCIÓN:\n"
        "   - Entrega código limpio, tipado, modular y completamente funcional.\n"
        "   - REGLA ZERO PLACEHOLDERS: Prohibido usar pseudocódigo o comentarios como '// tu código aquí' o '/* resto */'. Todo script debe ser ejecutable y autocontenido.\n"
        "   - Manejo defensivo de errores: validación de entradas, captura de excepciones y documentación de posibles fallos en runtime.\n"
        "   - Documentación técnica estándar: Docstrings en Python, JSDoc en TS/JS, etc.\n"
        "   - Resaltado de sintaxis especificando el lenguaje (```python, ```dart, ```typescript, etc.).\n"
        "3. DESGLOSE TÉCNICO Y JUSTIFICACIÓN:\n"
        "   - Explica las decisiones arquitectónicas o algorítmicas adoptadas.\n"
        "   - Detalla librerías o dependencias necesarias para ejecución.\n"
        "4. PRUEBA DE CASOS DE USO / TEST UNITARIO:\n"
        "   - Proporciona un ejemplo ejecutable de prueba que incluya al menos un caso de éxito y un caso borde (edge case).\n\n"
        "ADAPTACIÓN SEGÚN NIVEL TÉCNICO:\n"
        "- Principiante: Flujo línea por línea, diagramas lógicos o tablas de traza, legibilidad sobre optimización prematura.\n"
        "- Medio: Principios SOLID, manejo de excepciones, tipado, pruebas unitarias básicas, diferencias entre estructuras de datos.\n"
        "- Avanzado: Análisis formal Big-O, concurrencia, asincronía, gestión de memoria, prevención de race conditions, patrones de diseño (Factory, Singleton, Repository, Strategy).\n"
        "- Nivel Máster: Arquitecturas limpias (Hexagonal, Event-Driven, Microservicios, CQRS), bajo nivel (AST, CPU cache, syscalls), seguridad estricta (OWASP Top 10, sanitización, criptografía) y escalabilidad global."
    )

    parts = [
        "=== SKY DEVELOPER INTELLIGENCE CORE (MÓDULO MAESTRO DE INGENIERÍA) ===",
        sec_1,
        dev_protocol
    ]

    # 2. Agregar secciones según el contexto detectado
    if any(k in combined for k in ["web", "front", "back", "api", "html", "react", "node", "fastapi"]):
        parts.append(extract_thematic_section(master_text, 3)) # Desarrollo Web

    if any(k in combined for k in ["android", "ios", "móvil", "movil", "flutter", "dart", "kotlin", "swift"]):
        parts.append(extract_thematic_section(master_text, 4)) # Móvil y Desktop

    if any(k in combined for k in ["base de datos", "database", "sql", "postgres", "supabase", "redis", "nosql"]):
        parts.append(extract_thematic_section(master_text, 5)) # Bases de Datos

    if any(k in combined for k in ["ia", "ai", "machine learning", "deep learning", "llm", "rag", "modelo"]):
        parts.append(extract_thematic_section(master_text, 6)) # Ingeniería de IA

    if any(k in combined for k in ["arquitectura", "clean", "patron", "patrón", "solid", "microservicio"]):
        parts.append(extract_thematic_section(master_text, 8)) # Arquitectura de Software

    if any(k in combined for k in ["devops", "cloud", "docker", "deploy", "despliegue", "ci/cd", "servidor"]):
        parts.append(extract_thematic_section(master_text, 9)) # Cloud & DevOps

    if any(k in combined for k in ["seguridad", "owasp", "ciberseguridad", "token", "auth", "vulnerab"]):
        parts.append(extract_thematic_section(master_text, 10)) # Seguridad

    if any(k in combined for k in ["error", "bug", "fallo", "debug", "traza", "exception", "no funciona"]):
        parts.append(extract_thematic_section(master_text, 11)) # Depuración
        parts.append(extract_thematic_section(master_text, 22)) # Autocorrección

    if any(k in combined for k in ["test", "prueba", "qa", "pytest", "jest", "validar"]):
        parts.append(extract_thematic_section(master_text, 12)) # Pruebas y Calidad

    if any(k in combined for k in ["repositorio", "repo", "git", "github", "estructura"]):
        parts.append(extract_thematic_section(master_text, 16)) # Protocolo Repositorios

    if any(k in combined for k in ["crear", "iniciar", "nuevo proyecto", "desde cero", "construir una app"]):
        parts.append(extract_thematic_section(master_text, 21)) # Creación desde cero

    # 3. Reglas de comunicación y cierre
    parts.append(extract_thematic_section(master_text, 23)) # Comunicación
    parts.append(sec_24)
    parts.append(sec_25)

    joined = "\n\n".join(p for p in parts if p)
    if len(joined) > 6500:
        return joined[:6500] + "\n...[SKY-DEVELOPER-CORE DIRECTIVAS ACTIVAS]..."
    return joined

def analyze_tech_stack(text: str) -> Dict[str, Any]:
    """Identifica automáticamente tecnologías, frameworks y tipo de tarea en el texto."""
    t = text.casefold()
    
    from .sky_programming_capabilities import detect_languages
    languages = detect_languages(text)

    frameworks = []
    for fw in ["flutter", "fastapi", "react", "next.js", "django", "express", "supabase", "docker", "vue", "tailwind", "redis", "postgresql"]:
        if fw in t:
            frameworks.append(fw.capitalize() if fw != "next.js" else "Next.js")

    task_type = "Consulta General"
    if any(w in t for w in ["crea", "crear", "nueva app", "nuevo proyecto", "construye"]):
        task_type = "Creación de Proyecto"
    elif any(w in t for w in ["error", "bug", "falla", "no compila", "arregla", "corrige"]):
        task_type = "Depuración y Corrección"
    elif any(w in t for w in ["arquitectura", "diseña", "estructura", "patrón"]):
        task_type = "Diseño de Arquitectura"
    elif any(w in t for w in ["seguridad", "auditoría", "vulnerable"]):
        task_type = "Auditoría de Seguridad"
    elif any(w in t for w in ["test", "pruebas", "pytest"]):
        task_type = "Testing y QA"

    return {
        "languages": languages,
        "frameworks": frameworks,
        "task_type": task_type,
        "is_dev": len(languages) > 0 or len(frameworks) > 0 or is_developer_task("", text)
    }
