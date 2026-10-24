"""SKY Design Studio: relevant, animated, editable web/app project generation.

Generates real file trees from audited local templates; does not claim builds
until independent npm/Flutter CI or owner devices have checked them. No
packages/files are installed or modified on the owner's machine on generation.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent / "templates"
_ALLOWED = {"react": "sky_design_react", "flutter": "sky_design_flutter"}
_LAYOUTS = ("editorial", "dashboard", "immersive")
_STYLES = ("aurora", "ember", "monochrome")
_THEMES = (
    ("#64e6cf", "#8c79ff", "#071119", "#edf6fa"),
    ("#fd946d", "#b678ff", "#170d15", "#fff5ef"),
    ("#91d9fc", "#6cc5f4", "#0c1421", "#eff8ff"),
    ("#b3f28a", "#5dc7b5", "#101a14", "#f2f9f1"),
    ("#ffc87e", "#f4935b", "#1d1320", "#fff6f3"),
)
_DOMAINS: dict[str, dict[str, Any]] = {
    "turismo": {"words": ("turismo", "tour", "viaje", "hotel", "destino", "ruta", "naturaleza", "baqueano"),
        "eyebrow": "DESCUBRIMIENTO · EXPERIENCIAS",
        "subtitle": "Explorá destinos fuera de lo común.",
        "description": "Rutas memorables, comunidad y experiencias que conectan con lugares reales.",
        "features": [("Rutas con sentido", "Planes claros para explorar a tu ritmo.", "compass"),
                     ("Comunidad local", "Conectá con personas y experiencias auténticas.", "layers"),
                     ("Viaje informado", "Decisiones accesibles, transparentes y útiles.", "shield")]},
    "educacion": {"words": ("educaci", "docent", "escuela", "aprend", "aula", "univers", "curso", "maestr"),
        "eyebrow": "APRENDIZAJE · INNOVACIÓN",
        "subtitle": "El aprendizaje merece otro horizonte.",
        "description": "Formación interactiva, herramientas educativas y progreso comprensible.",
        "features": [("Aprendizaje activo", "Experiencias diseñadas para comprender y practicar.", "sparkles"),
                     ("Seguimiento continuo", "Evaluaciones con criterios visibles.", "activity"),
                     ("Acceso inclusivo", "Aprender con claridad y propósito.", "shield")]},
    "salud": {"words": ("salud", "medic", "clinica", "clínica", "bienestar", "paciente", "hospital"),
        "eyebrow": "BIENESTAR · CONFIANZA",
        "subtitle": "Tecnología más humana para el bienestar.",
        "description": "Información clara, accesible y cercana para experiencias de salud responsables.",
        "features": [("Atención comprensible", "Información organizada para tomar mejores decisiones.", "activity"),
                     ("Seguridad y privacidad", "Diseño que respeta los datos de las personas.", "shield"),
                     ("Bienestar cercano", "Una experiencia visual serena y accesible.", "sparkles")]},
    "finanzas": {"words": ("finanza", "banco", "pago", "presupuesto", "ahorro", "contab", "inversion"),
        "eyebrow": "FINANZAS · VISIBILIDAD",
        "subtitle": "Más claridad para cada decisión financiera.",
        "description": "Paneles comprensibles, indicadores útiles y experiencias con control.",
        "features": [("Datos accionables", "Indicadores que explican qué está pasando.", "activity"),
                     ("Decisiones claras", "Información con una jerarquía visual rigurosa.", "layers"),
                     ("Confianza digital", "Privacidad y transparencia por diseño.", "shield")]},
    "videojuegos": {"words": ("videojuego", "gaming", "unity", "juego", "game", "metaverso", "unreal", "godot"),
        "eyebrow": "GAMING · INTERACCIÓN",
        "subtitle": "Un nuevo universo empieza aquí.",
        "description": "Diseño inmersivo para comunidades, mundos y experiencias interactivas.",
        "features": [("Universos vivos", "Una identidad que invita a explorar.", "sparkles"),
                     ("Interacción precisa", "Controles accesibles con respuesta inmediata.", "activity"),
                     ("Experiencia compartida", "Espacios legibles y visualmente memorables.", "layers")]},
    "cultura": {"words": ("cultura", "museo", "patrimonio", "arte", "historia", "musica", "música"),
        "eyebrow": "CULTURA · IDENTIDAD",
        "subtitle": "Historias que merecen seguir brillando.",
        "description": "Patrimonio y creatividad en una experiencia digital con carácter.",
        "features": [("Identidad auténtica", "Narrativas relevantes que conservan su origen.", "sparkles"),
                     ("Exploración intuitiva", "Colecciones fáciles de descubrir.", "compass"),
                     ("Acceso universal", "Diseño adaptable a más públicos.", "shield")]},
    "tecnologia": {"words": (),
        "eyebrow": "INNOVACIÓN · DISEÑO DIGITAL",
        "subtitle": "La próxima experiencia ya está tomando forma.",
        "description": "Interfaces con personalidad, movimiento intencional y funcionalidad comprobable.",
        "features": [("Diseño relevante", "Una identidad visual adaptada al producto.", "sparkles"),
                     ("Movimiento útil", "Interacciones que ayudan a comprender.", "activity"),
                     ("Confianza y acceso", "Experiencias con jerarquía, contraste y control.", "shield")]},
}


class DesignInvalid(ValueError):
    pass


def _clean(value: Any, name: str, limit: int) -> str:
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        raise DesignInvalid(f"{name} debe ser texto de hasta {limit} caracteres.")
    return " ".join(value.strip().split())


def _domain(brief: str, domain: str) -> str:
    if domain and domain not in _DOMAINS:
        raise DesignInvalid("Sector no reconocido por SKY Design Studio.")
    if domain:
        return domain
    lowered = brief.casefold()
    for key, details in _DOMAINS.items():
        if key != "tecnologia" and any(word in lowered for word in details["words"]):
            return key
    return "tecnologia"


def _file_set(platform: str) -> dict[str, str]:
    root = _ROOT / _ALLOWED[platform]
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if len(files) >= 25 or path.stat().st_size > 72_000 or relative.startswith("."):
            raise DesignInvalid("La plantilla interna excedió el límite permitido.")
        files[relative] = path.read_text(encoding="utf-8")
    if not files:
        raise DesignInvalid("La plantilla de diseño no se encuentra instalada.")
    return files


def _dart_literal(value: str) -> str:
    # Use double-quoted Dart literals with explicit escapes. No code interpolation.
    return '"' + value.replace("\\", "\\\\").replace("$", "\\$").replace('"', '\\"').replace(
        "\n", "\\n").replace("\r", "\\r") + '"'


def create_design(title: str, brief: str, *, platform: str = "react",
                  domain: str = "", style: str = "auto",
                  layout: str = "auto") -> dict[str, Any]:
    """Create a multi-file React/Flutter source tree without filesystem writes."""
    title = _clean(title, "Título", 90)
    brief = _clean(brief, "Descripción", 500)
    if not title or not brief:
        raise DesignInvalid("Indicá un título y una idea concreta.")
    if platform not in _ALLOWED:
        raise DesignInvalid("Plataforma: react o flutter.")
    if style not in {*_STYLES, "auto"} or layout not in {*_LAYOUTS, "auto"}:
        raise DesignInvalid("Estilo o distribución no admitida.")
    subject = _domain(brief, domain)
    digest = hashlib.sha256((title + "\x1e" + brief + "\x1e" + subject).encode("utf-8")).digest()
    palette = _THEMES[digest[0] % len(_THEMES)]
    chosen_style = _STYLES[digest[1] % len(_STYLES)] if style == "auto" else style
    chosen_layout = _LAYOUTS[digest[2] % len(_LAYOUTS)] if layout == "auto" else layout
    content = _DOMAINS[subject]
    files = _file_set(platform)
    if platform == "react":
        cfg = json.loads(files["src/config.json"])
        cfg.update({
            "title": title, "subtitle": content["subtitle"],
            "description": brief, "eyebrow": content["eyebrow"],
            "domain": subject, "style": chosen_style, "layout": chosen_layout,
            "primary": palette[0], "secondary": palette[1],
            "background": palette[2], "foreground": palette[3],
            "features": [{"title": name, "detail": detail, "icon": icon}
                         for name, detail, icon in content["features"]],
        })
        files["src/config.json"] = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
        # Title is inserted exclusively via JSON at runtime, not into HTML markup.
        dependencies = json.loads(files["package.json"])["dependencies"]
        next_steps = [
            "npm install --ignore-scripts --no-audit --no-fund",
            "npm run build",
            "npm run dev",
        ]
    else:
        cfg = files["lib/sky_config.dart"]
        replacements = {
            "skyTitle": _dart_literal(title),
            "skySubtitle": _dart_literal(content["subtitle"]),
            "skyDescription": _dart_literal(brief),
            "skyFeatureOne": _dart_literal(content["features"][0][0]),
            "skyFeatureTwo": _dart_literal(content["features"][1][0]),
            "skyFeatureThree": _dart_literal(content["features"][2][0]),
            "skyColorPrimary": "0xFF" + palette[0][1:].upper(),
            "skyColorSecondary": "0xFF" + palette[1][1:].upper(),
            "skyStyle": _dart_literal(chosen_style),
            "skyLayout": _dart_literal(chosen_layout),
        }
        for name, value in replacements.items():
            pattern = rf"(?m)^(const {re.escape(name)}\s*=\s*)(?:'[^'\n]*'|0x[0-9A-Fa-f]{{8}});$"
            cfg, count = re.subn(pattern, lambda m: m.group(1) + value + ";", cfg)
            if count != 1:
                raise DesignInvalid(f"Configuración Flutter no encontrada: {name}")
        files["lib/sky_config.dart"] = cfg
        dependencies = {"flutter_animate": "4.5.2"}
        next_steps = ["flutter pub get", "flutter analyze", "flutter test", "flutter run"]
    return {
        "ok": True, "platform": platform, "domain": subject,
        "style": chosen_style, "layout": chosen_layout,
        "colors": {"primary": palette[0], "secondary": palette[1],
                   "background": palette[2], "foreground": palette[3]},
        "files": files, "file_count": len(files),
        "libraries_declared": dependencies,
        "requires_owner_installation": True,
        "generated_sources_built_now": False, "compiled_on_owner_device": False,
        "files_written_on_owner_device": False, "device_visual_test_passed": False,
        "project_specific_design_reviewed_by_human": False,
        "commands_to_test_in_separate_approved_project": next_steps,
        "note": "Proyecto real y editable; generación no significa que el SDK esté instalado ni que haya compilado en tu dispositivo.",
    }


def design_archive(result: dict[str, Any]) -> bytes:
    """Build downloadable ZIP in memory with only fixed local-template paths."""
    data = io.BytesIO()
    if result.get("platform") not in _ALLOWED:
        raise DesignInvalid("Plataforma de diseño inválida.")
    with zipfile.ZipFile(data, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
        root = f"sky-design-{result['platform']}/"
        for path, content in result["files"].items():
            # Already read from strictly controlled local project tree.
            bundle.writestr(root + path, content)
        bundle.writestr(root + "SKY_MANIFEST.json", json.dumps({
            "platform": result["platform"], "domain": result["domain"],
            "style": result["style"], "colors": result["colors"],
            "libraries": result["libraries_declared"],
            "testing": result["commands_to_test_in_separate_approved_project"],
            "generated_sources_built_now": False,
            "compiled_on_owner_device": False,
        }, ensure_ascii=False, indent=2))
    return data.getvalue()


def studio_capabilities() -> dict[str, Any]:
    return {
        "ok": True, "platforms": ["react", "flutter"],
        "styles": list(_STYLES), "layouts": list(_LAYOUTS),
        "domains": list(_DOMAINS),
        "react_libraries": {
            "animation": "motion", "icons": "lucide-react",
            "font": "@fontsource/inter", "build": "vite",
        },
        "flutter_libraries": {"animation": "flutter_animate", "icons": "Flutter Material Icons"},
        "verified_on_current_user_device": False,
        "code_execution_on_generation": False,
        "note": "Dependencias declaradas por proyecto; SKY no instala bibliotecas en su núcleo de manera global.",
    }
