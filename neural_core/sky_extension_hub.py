"""SKY Extension Hub — the catalogue never installs, executes or trusts 3rd-party code.

SKY CORE remains the sole identity, memory, API, voice and authorization layer.
Entries are interoperability declarations, NOT installed programs or live tests.
"""
from __future__ import annotations

from . import sky_integraciones

# (slug, name, domain, integration_mode, repository_or_site, why, status_policy)
_ROWS = (
    ("openclaw","OpenClaw","agentes","reference","https://github.com/openclaw/openclaw",
     "Estudiar arquitectura de asistentes y herramientas sin delegar control.", "review_only"),
    ("hermes-agent","Hermes Agent","aprendizaje","reference","https://github.com/NousResearch/hermes-agent",
     "Revisar patrones de skills y memoria; no ejecutar actualizaciones automáticas.","review_only"),
    ("opencode","OpenCode","programación","sidecar","https://github.com/anomalyco/opencode",
     "Agente opcional de código en entorno aislado y repositorio de pruebas.","optional_not_installed"),
    ("n8n","n8n","automatización","api","https://github.com/n8n-io/n8n",
     "Automatización controlada mediante puente n8n ya disponible.","configured_not_verified"),
    ("firecrawl","Firecrawl","investigación","api","https://github.com/firecrawl/firecrawl",
     "Extracción web acotada mediante skillpack existente.","configured_not_verified"),
    ("ollama","Ollama","modelos","native","https://github.com/ollama/ollama",
     "Proveedor local de modelos ya conectado a SKY CORE.","present_not_live_verified"),
    ("agent-skills","Agent Skills","habilidades","skill_format","https://github.com/anthropics/skills",
     "Importar instrucciones seleccionadas para revisión humana y pruebas aisladas.","format_partial"),
    ("dify","Dify","automatización","sidecar","https://github.com/langgenius/dify",
     "Diseñador externo de workflows y RAG, no sustituye SKY.","optional_not_installed"),
    ("open-webui","Open WebUI","interfaz","sidecar","https://github.com/open-webui/open-webui",
     "Panel alternativo opcional, nunca interfaz principal.","optional_not_installed"),
    ("langflow","Langflow","automatización","sidecar","https://github.com/langflow-ai/langflow",
     "Diseño visual auxiliar de flujos y pruebas.","optional_not_installed"),
    ("claude-code","Claude Code","programación","development_tool","https://github.com/anthropics/claude-code",
     "Asistente de desarrollo opcional bajo su licencia y cuenta.","optional_not_installed"),
    ("langchain","LangChain","programación","library","https://github.com/langchain-ai/langchain",
     "Reutilizar componentes puntuales si SKY CORE los necesita.","optional_not_installed"),
    ("semantic-scholar","Semantic Scholar","investigación","api","https://www.semanticscholar.org/",
     "Artículos, resúmenes y citas bibliográficas.","configured_not_verified"),
    ("zotero","Zotero","investigación","api","https://www.zotero.org/",
     "Bibliotecas personales en solo lectura.","configured_not_verified"),
    ("wolfram","Wolfram Alpha","educación","api","https://www.wolframalpha.com/",
     "Cálculo y verificación matemática.","configured_not_verified"),
    ("openrouter","OpenRouter","modelos","provider","https://openrouter.ai/",
     "Selección explícita de otros modelos.","configured_not_verified"),
    ("huggingface","Hugging Face","modelos","provider","https://huggingface.co/",
     "Inferencia de modelos opcionales.","configured_not_verified"),
    ("github","GitHub","programación","api","https://github.com/",
     "Lectura e integración de código y solicitudes de cambio.","configured_not_verified"),
    ("remotion","Remotion","multimedia","local_skill","https://www.remotion.dev/",
     "Generación de video mediante el skillpack local.","configured_not_verified"),
    ("canva","Canva","diseño","external_app","https://www.canva.com/",
     "Diseños asistidos cuando exista una autorización y conector adecuados.","reference_only"),
    ("elevenlabs","ElevenLabs","audio","external_app","https://elevenlabs.io/",
     "Voz alternativa mediante servicio autorizado; sin sustituir TTS local.","reference_only"),
    ("stability-ai","Stable Diffusion","imágenes","external_app","https://github.com/Stability-AI/",
     "Modelos gráficos según hardware, licencia y permisos.","reference_only"),
    ("consensus","Consensus","investigación","external_app","https://consensus.app/",
     "Lectura de evidencia con origen y citas; integración sujeta a API.","reference_only"),
    ("notebooklm","NotebookLM","educación","external_app","https://notebooklm.google.com/",
     "Referencia de aprendizaje sobre documentos; sin acceso a sesiones privadas.","reference_only"),
    ("cursor","Cursor","programación","development_tool","https://cursor.com/",
     "Editor auxiliar, no agente que controle SKY.","reference_only"),
    ("replit","Replit","programación","external_app","https://replit.com/",
     "Entornos de desarrollo independientes para pruebas autorizadas.","reference_only"),
    ("gamma","Gamma","diseño","api","https://gamma.app/",
     "Presentaciones mediante API cuando exista cuenta apropiada.","configured_not_verified"),
    ("firefly","Adobe Firefly","imágenes","api","https://firefly.adobe.com/",
     "Generación de contenido visual con API oficial opcional.","configured_not_verified"),
)

def catalogue(category: str = "") -> dict:
    if category and (not isinstance(category,str) or len(category)>40):
        raise ValueError("Categoría inválida.")
    known={x["id"]:x for x in sky_integraciones.listar()}
    entries=[]
    for slug,name,domain,mode,url,purpose,policy in _ROWS:
        if category and domain!=category:
            continue
        integration=known.get(slug)
        configured=bool(integration and integration.get("lista"))
        # No runtime probes, process checks or package installations occur here.
        entries.append({"id":slug,"name":name,"domain":domain,"mode":mode,
             "official_url":url,"purpose":purpose,"state":policy,
             "configured":configured,"live_verified":False,
             "external_code_execution_allowed":False,
             "independent_owner_approval_required":True,
             "source_trusted_as_instruction":False})
    return {"owner":"SKY IA","primary_core":"SKY CORE",
            "extensions":entries,"total":len(entries),
            "auto_install":False,"auto_execute":False,
            "source_code_imported":False,"api_replaced":False,
            "status_note":"Los registros no prueban que una herramienta esté instalada ni disponible en tu equipo."}


def extension(identifier: str) -> dict:
    if not isinstance(identifier,str) or len(identifier)>60:
        raise ValueError("Identificador inválido.")
    return next((x for x in catalogue()["extensions"] if x["id"]==identifier),None) or {}


def learning_architecture()->dict:
    return {"memory":"smart_memory + sky_experience_learning (local owner controlled)",
            "skill_generation":"sky_skill_builder (sandbox + owner approval)",
            "task_execution":"sky_execution_cycle (one confirmed step at a time)",
            "observations":"only verified operational cycles, not model self-report",
            "external_installation":"manual security review required",
            "hardware_verified":False}
