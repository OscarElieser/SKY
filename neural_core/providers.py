"""SKY v4.3: pasarela multi-proveedor solo de texto, sin acciones externas.

Las credenciales se leen en el proceso local. No se registran prompts ni secretos.
La elección automática sólo considera proveedores *configurados*; no cambia
silenciosamente a otro servicio después de errores (privacidad/costo).
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import os
from urllib import request, error

class ProviderError(RuntimeError):
    """Error de configuración o comunicación con el motor seleccionado."""

@dataclass(frozen=True)
class Provider:
    key: str
    name: str
    env: str
    model_env: str
    model_default: str
    cloud: bool

PROVIDERS = {
    'gemini': Provider('gemini','Google Gemini','GEMINI_API_KEY','GEMINI_MODEL','gemini-flash-latest',True),
    'openai': Provider('openai','OpenAI GPT','OPENAI_API_KEY','OPENAI_MODEL','gpt-4.1-mini',True),
    'anthropic': Provider('anthropic','Anthropic Claude','ANTHROPIC_API_KEY','ANTHROPIC_MODEL','claude-sonnet-4-5',True),
    'mistral': Provider('mistral','Mistral AI','MISTRAL_API_KEY','MISTRAL_MODEL','mistral-medium-latest',True),
    'groq': Provider('groq','Groq (Llama)','GROQ_API_KEY','GROQ_MODEL','llama-3.3-70b-versatile',True),
    'deepseek': Provider('deepseek','DeepSeek','DEEPSEEK_API_KEY','DEEPSEEK_MODEL','deepseek-chat',True),
    'ollama': Provider('ollama','Ollama local','','OLLAMA_MODEL','llama3.2',False),
    # Motor externo opcional, nunca se agrega a AUTO_ORDER ni reemplaza SKY.
    'openjarvis': Provider('openjarvis','OpenJarvis local (opcional)','SKY_OPENJARVIS_ENABLED','SKY_OPENJARVIS_MODEL','',False),
    'lmstudio': Provider('lmstudio','LM Studio local (opcional)','SKY_LMSTUDIO_ENABLED','SKY_LMSTUDIO_MODEL','',False),
    # Opt-in only: never silently send a prompt or incur usage on these new providers.
    'openrouter': Provider('openrouter','OpenRouter','OPENROUTER_API_KEY','OPENROUTER_MODEL','',True),
    'huggingface': Provider('huggingface','Hugging Face Inference','HF_TOKEN','HF_MODEL','',True),
}
AUTO_ORDER = ('gemini','openai','anthropic','mistral','groq','deepseek','ollama')
# Criterio simple y transparente: no es ranking de calidad ni estimación de costos.
DOMAIN_PREF = {
    'educación': ('gemini','openai','anthropic'),
    'investigación': ('gemini','anthropic','openai'),
    'programación': ('anthropic','openai','gemini'),
    'código': ('anthropic','openai','gemini'),
    'negocios': ('gemini','openai','anthropic'),
    'marketing': ('gemini','openai','anthropic'),
    'finanzas': ('gemini','openai','anthropic'),
    'sky voz': ('gemini','openai','anthropic'),
}

def provider_ready(name: str) -> bool:
    if name not in PROVIDERS: return False
    cfg=PROVIDERS[name]
    if name == 'openjarvis':
        from .sky_openjarvis import configured
        return configured()
    if name == 'lmstudio':
        from .sky_lmstudio import configured
        return configured()
    if not cfg.env:
        return True  # Ollama puede estar apagado; se comprueba al consultar.
    if name in ('openrouter','huggingface'):
        return bool(os.getenv(cfg.env,'').strip() and os.getenv(cfg.model_env,'').strip())
    return bool(os.getenv(cfg.env,'').strip())

def provider_summary() -> list[dict]:
    return [dict(id=k,proveedor=v.name,configurado=provider_ready(k),entorno=v.env or 'Servidor local',
                 modelo=os.getenv(v.model_env,v.model_default), nube=v.cloud)
            for k,v in PROVIDERS.items()]

def local_only() -> bool:
    """SKY_LOCAL_ONLY=1: ningún texto sale del equipo; sólo Ollama local."""
    return os.getenv('SKY_LOCAL_ONLY', '0').strip().lower() in ('1', 'true', 'si', 'sí', 'yes')

def choose_provider(name: str='auto', area: str='General') -> tuple[str,str]:
    if local_only():
        if name not in ('auto', 'sky', 'ollama', 'lmstudio'):
            raise ProviderError('Modo local: SKY sólo permite Ollama o LM Studio local.')
        if name in ('auto', 'sky'):
            name = 'lmstudio' if provider_ready('lmstudio') else 'ollama'
    if name in ('auto', 'sky'):
        a=area.casefold()
        preferred=next((pref for token,pref in DOMAIN_PREF.items() if token in a),AUTO_ORDER)
        candidates=tuple(preferred)+tuple(k for k in AUTO_ORDER if k not in preferred)
        name=next((k for k in candidates if provider_ready(k)),None)
        if not name: raise ProviderError('No hay proveedores disponibles. Configurá una clave API o Ollama local.')
    if name not in PROVIDERS: raise ValueError('Proveedor desconocido. Revisá el selector de SKY.')
    if not provider_ready(name):
        cfg=PROVIDERS[name]
        if name == 'openjarvis':
            raise ProviderError('Para OpenJarvis configurá SKY_OPENJARVIS_ENABLED=1 y SKY_OPENJARVIS_MODEL en .env.')
        if name == 'lmstudio':
            raise ProviderError('Configurá SKY_LMSTUDIO_ENABLED=1 y SKY_LMSTUDIO_MODEL en .env.')
        raise ProviderError(f'Falta {cfg.env} en .env para {cfg.name}.')
    cfg=PROVIDERS[name]
    model=os.getenv(cfg.model_env,cfg.model_default).strip() or cfg.model_default
    return name,model

def _messages(mensajes: list[dict]) -> tuple[str,list[dict]]:
    if not mensajes or mensajes[0].get('role')!='system':
        raise ValueError('Se requiere instrucción de sistema para SKY.')
    system=str(mensajes[0].get('content',''))[:20000]
    turns=[{'role':msg['role'],'content':str(msg.get('content',''))[:12000]}
           for msg in mensajes[1:] if msg.get('role') in {'user','assistant'}]
    if not turns or turns[-1]['role']!='user':
        raise ValueError('Se requiere una pregunta de usuario.')
    return system, turns

def _result(text: str, name: str):
    cleaned=(text or '').strip()
    if not cleaned: raise ProviderError(f'{PROVIDERS[name].name} devolvió una respuesta vacía.')
    return cleaned

def _openai_sdk(key, base_url=None):
    try: from openai import OpenAI
    except ImportError as exc: raise ProviderError('Falta el SDK OpenAI: instalá requirements.txt.') from exc
    kw={'api_key':key,'timeout':60.0,'max_retries':1}
    if base_url: kw['base_url']=base_url
    return OpenAI(**kw)

def reply(mensajes: list[dict], provider: str, model: str|None=None, max_output_tokens: int=2500):
    if provider=='auto': provider,chosen=choose_provider('auto')
    else: provider,chosen=choose_provider(provider)
    model=(model or chosen).strip()
    if provider in ('openrouter','huggingface') and not model:
        raise ProviderError('Debés configurar el modelo exacto del proveedor; SKY no adivina modelos ni cuotas.')
    if not model or len(model)>150: raise ValueError('Identificador de modelo inválido.')
    if max_output_tokens<1 or max_output_tokens>8192: raise ValueError('Límite de salida inválido.')
    system,turns=_messages(mensajes)
    try:
        if provider=='gemini':
            from neural_core.gemini_provider import responder_gemini
            return responder_gemini(mensajes,modelo=model,max_tokens=max_output_tokens)
        if provider=='openai':
            client=_openai_sdk(os.environ['OPENAI_API_KEY'])
            try:
                resp=client.responses.create(model=model,instructions=system,input=turns,
                                              max_output_tokens=max_output_tokens,store=False)
                return _result(getattr(resp,'output_text',''),provider)
            finally: client.close()
        if provider=='anthropic':
            try: from anthropic import Anthropic
            except ImportError as exc: raise ProviderError('Falta SDK Anthropic: instalá requirements.txt.') from exc
            client=Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'],timeout=60.0,max_retries=1)
            try:
                resp=client.messages.create(model=model,system=system,messages=turns,max_tokens=max_output_tokens)
                return _result('\n'.join(getattr(b,'text','') for b in resp.content if getattr(b,'type','')=='text'),provider)
            finally: client.close()
        if provider=='mistral':
            try: from mistralai.client import Mistral
            except ImportError:
                try: from mistralai import Mistral
                except ImportError as exc: raise ProviderError('Falta SDK Mistral: instalá requirements.txt.') from exc
            client=Mistral(api_key=os.environ['MISTRAL_API_KEY'])
            messages=[{'role':'system','content':system},*turns]
            resp=client.chat.complete(model=model,messages=messages,max_tokens=max_output_tokens,temperature=0.2)
            parts=resp.choices[0].message.content
            return _result(parts if isinstance(parts,str) else ''.join(str(p.get('text','')) if isinstance(p,dict) else str(getattr(p,'text','')) for p in parts),provider)
        if provider in ('openrouter','huggingface'):
            # OpenAI-compatible chat endpoints; model must be configured explicitly
            # to avoid guessing availability, cost or changing data residency.
            if not model:
                raise ProviderError('Configurá OPENROUTER_MODEL o HF_MODEL antes de utilizar el proveedor.')
            base={'openrouter':'https://openrouter.ai/api/v1',
                  'huggingface':'https://router.huggingface.co/v1'}[provider]
            client=_openai_sdk(os.environ[PROVIDERS[provider].env],base)
            try:
                resp=client.chat.completions.create(
                    model=model,messages=[{'role':'system','content':system},*turns],
                    max_tokens=max_output_tokens,temperature=0.2,stream=False)
                choice=resp.choices[0].message.content if resp.choices else None
                return _result(choice,provider)
            finally: client.close()
        if provider in ('groq','deepseek'):
            base={'groq':'https://api.groq.com/openai/v1',
                  'deepseek':'https://api.deepseek.com'}[provider]
            api_key=os.environ[PROVIDERS[provider].env]
            client=_openai_sdk(api_key,base)
            try:
                resp=client.chat.completions.create(model=model,messages=[{'role':'system','content':system},*turns],
                                                   max_tokens=max_output_tokens,temperature=0.2)
                return _result(resp.choices[0].message.content,provider)
            finally: client.close()
        if provider=='lmstudio':
            from .sky_lmstudio import chat
            return _result(chat([{'role':'system','content':system},*turns], model,
                                max_tokens=max_output_tokens), provider)
        if provider=='openjarvis':
            from .sky_openjarvis import chat
            # Solo texto, hacia loopback. Sin herramientas ni rutas nuevas en la API SKY.
            return _result(chat([{'role':'system','content':system}, *turns], model,
                                max_tokens=max_output_tokens), provider)
        if provider=='ollama':
            # Sólo localhost: no permitir URLs arbitrarias ni exposición accidental de contenido.
            payload=json.dumps({'model':model,'messages':[{'role':'system','content':system},*turns],
                                'stream':False,'options':{'num_predict':max_output_tokens,'temperature':0.2}}).encode('utf8')
            req=request.Request('http://127.0.0.1:11434/api/chat',data=payload,
                                headers={'Content-Type':'application/json'},method='POST')
            try:
                with request.urlopen(req,timeout=120) as r:
                    resp=json.load(r)
                return _result(resp.get('message',{}).get('content',''),provider)
            except (error.URLError,TimeoutError,OSError) as exc:
                raise ProviderError('Ollama no responde en localhost:11434. Iniciá ollama serve.') from exc
        raise ValueError('Proveedor no admitido.')
    except (ProviderError,ValueError): raise
    except Exception as exc:
        # No devolver la excepción cruda: varios SDK incorporan detalles del request.
        raise ProviderError(f'Error en {PROVIDERS[provider].name} ({type(exc).__name__}). Revisá modelo, acceso, cuotas y conexión.') from exc
