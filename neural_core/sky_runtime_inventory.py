"""Auditoría no invasiva de motores, agentes, desktop y no-code de SKY.

El catálogo refleja CÓDIGO presente y paquetes instalados por separado.
No instala nada, no levanta servidores ni conecta cuentas automáticamente.
"""
from __future__ import annotations
import importlib.util
import os
import shutil
from .sky_comfyui_local import capabilities as comfy
from .sky_lmstudio import configured as lm_ready


PACKAGES={
    "crewai":("crewai", "Agentes CrewAI (opcional, todavía sin adaptador SKY)"),
    "autogen":("autogen_agentchat", "Microsoft AutoGen / AgentChat (opcional, sin adaptador)"),
    "langchain":("langchain", "LangChain (opcional, sin adaptador)"),
    "keyboard":("keyboard", "Control de teclado local (sujeto a permisos del agente)"),
    "pyautogui":("pyautogui", "Automatización de interfaz local (no autorizada por importar)"),
    "requests":("requests", "Cliente HTTP Python"),
    "diffusers":("diffusers", "Hugging Face Diffusers: carga de pesos por configurar"),
    "torch":("torch", "PyTorch: infraestructura de cómputo, no modelo generador"),
    "mcp":("mcp", "SDK MCP opcional"),
}
CODE={
    "ollama":("neural_core.providers", "Disponible como ruta de modelo; requiere servidor"),
    "lmstudio":("neural_core.sky_lmstudio", "Adaptador real local opcional"),
    "comfyui":("neural_core.sky_comfyui_local", "Generación local real mediante workflows"),
    "subprocess":("subprocess", "Biblioteca estándar; SKY la usa en controlador Windows"),
    "home_assistant":("neural_core.sky_home_assistant","Control REST con restricciones y confirmaciones"),
    "n8n":("neural_core.sky_n8n_bridge","Bridge de workflows con allowlist y autorización"),
    "make":(None,"No hay adaptador oficial activo; pendiente de OAuth/webhook seguro"),
    "no_code_low_code":(None,"n8n integrado; Make pendiente, no implica controlador universal"),
    "crewai":(None,"El supervisor SKY actual no depende de CrewAI"),
    "autogen":(None,"El supervisor SKY actual no depende de AutoGen"),
    "langchain":(None,"SKY dispone de funciones propias de RAG/modelos; LangChain no necesario"),
}


def installed(module):
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def report():
    from .sky_comfyui_local import capabilities as local_media
    from .sky_lmstudio import status as lm_status
    packages={name:{"module":module,"installed_here":installed(module),
                    "note":description}
              for name,(module,description) in PACKAGES.items()}
    tools={name:{"exists_in_repo":name not in ("make","no_code_low_code","crewai",
                                              "autogen","langchain"),
                 "note":description}
           for name,(_,description) in CODE.items()}
    tools["lmstudio"]["configured"]=lm_ready()
    tools["lmstudio"]["live_verified"]=False
    tools["comfyui"].update(local_media())
    tools["home_assistant"]["configured"]=bool(
        os.getenv("SKY_HA_URL") and (os.getenv("SKY_HA_TOKEN") or os.getenv("SKY_HA_TOKEN_FILE")))
    tools["n8n"]["configured"]=bool(os.getenv("SKY_N8N_URL") and os.getenv("SKY_N8N_API_KEY"))
    for name,exe in (("ffmpeg","ffmpeg"),("ffprobe","ffprobe"),
                     ("blender","blender")):
        tools[name]={"installed_here":bool(shutil.which(exe)),
                     "not_proof_of_working_model":True}
    return {"controller":"SKY","inspected_environment":"SKY process host",
            "packages":packages,"modules":tools,
            "note":"Inspección del servidor actual, no del PC del propietario si corre remoto. "
                   "Configurado no significa operativo y no concede permisos."}
