"""Private SKY language preferences and explicitly requested translation."""
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,Field
from .api import require_key
from neural_core import sky_languages as lang

router=APIRouter()

class LanguagePref(BaseModel):
    language:str=Field(max_length=32,min_length=2)

class Translation(BaseModel):
    text:str=Field(min_length=1,max_length=6000)
    source:str='auto'
    target:str=Field(min_length=2,max_length=32)
    provider:str='none'
    consent:bool=False

@router.get('/api/i18n/languages')
def languages(request:Request):
    return {'languages':[{'code':k,'name':v,'ui_offline':bool(lang.glossary(k)), 'ui_coverage':lang.coverage(k)['reviewed_strings']} for k,v in lang.LANGUAGES.items()],
            'negotiated':lang.negotiate(request.headers.get('accept-language')),
            'fallback':'es','automatic_translation_requires_consent':True, 'catalogue_is_not_full_translation':True}

@router.get('/api/i18n/phrases')
def phrases(locale:str='es'):
    code=lang.normalize(locale)
    return {'locale':code,'offline':code.split('-')[0] in lang.PHRASES,
            'direction':'rtl' if code.split('-')[0] in ('ar','he','fa','ur') else 'ltr',
            'phrases':{k:lang.phrase(k,code) for k in lang.PHRASES['es']}}

@router.get('/api/i18n/preference',dependencies=[Depends(require_key)])
def preference():return {'language':lang.get_preference()}

@router.put('/api/i18n/preference',dependencies=[Depends(require_key)])
def update_preference(body:LanguagePref):
    try:return {'language':lang.set_preference(body.language)}
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.post('/api/i18n/translate',dependencies=[Depends(require_key)])
def translate(body:Translation):
    try:
        target=lang.normalize(body.target,strict=True)
        source=lang.normalize(body.source,strict=True) if body.source!='auto' else 'auto'
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    if source==target:return {'text':body.text,'target':target,'provider':'identity'}
    if body.provider=='none' or not body.consent:
        raise HTTPException(409,'Para enviar texto a un modelo externo, elegí proveedor y autorizá expresamente.')
    if body.provider not in ('gemini','ollama'):
        raise HTTPException(422,'La traducción solo está conectada a Gemini u Ollama local')
    # Do not attach memories, project data or previous conversation automatically.
    try:
        from neural_core.assistant import responder
        prompt=(f'Traducí únicamente el siguiente texto desde {source} hacia {target}. '
                'Conservá nombres propios, cifras y el significado. Devolvé solo la traducción.\n\n'+body.text)
        output,_=responder(prompt,'SKY Language',proveedor=body.provider)
        if not output.strip():raise RuntimeError('Respuesta vacía')
        return {'text':output[:24000],'target':target,'provider':body.provider,'review_recommended':True}
    except Exception as exc:
        raise HTTPException(503,'No se pudo completar la traducción. Verificá el proveedor autorizado.') from exc

@router.post('/api/i18n/script-hint',dependencies=[Depends(require_key)])
def identify_script(body:dict):
    text=body.get('text','')
    if not isinstance(text,str) or len(text)>6000:raise HTTPException(422,'Texto inválido')
    return lang.script_hint(text)


@router.get('/api/i18n/ui')
def global_ui(locale:str='es'):
    """Same-origin reviewed STATIC interface labels only; never user content."""
    try:code=lang.normalize(locale,strict=True)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    from neural_core.sky_global_ui import glossary, coverage
    mapped={**lang.PHRASES.get(code.split('-')[0],{}), **glossary(code)}
    return {'locale':code, 'direction':'rtl' if code.split('-')[0] in ('ar','he','fa','ur','ps') else 'ltr',
            'translations':mapped, 'coverage':coverage(code),
            'completeness':'core' if glossary(code) else 'fallback',
            'private_content_translated':False, 'provider_called':False}
