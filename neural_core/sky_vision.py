"""SKY Vision — imagen local de cámara/archivo -> modelo de visión elegido explícitamente."""
import base64, os
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from .providers import PROVIDERS, ProviderError, choose_provider

SUPPORTED={'gemini','openai','anthropic','ollama'}


def _check(blob:bytes,mime:str):
    if mime not in {'image/png','image/jpeg','image/webp'}: raise ValueError('Tipo de imagen no admitido')
    if not blob or len(blob)>8_000_000: raise ValueError('Imagen vacía o superior a 8 MB')
    try:
        with Image.open(BytesIO(blob)) as im:
            if im.width * im.height > 12_000_000: raise ValueError('Resolución demasiado grande')
            im.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError('Archivo de imagen inválido o corrupto') from exc


def analizar(blob:bytes,mime:str,pregunta:str,proveedor:str='gemini',modelo:str|None=None)->str:
    _check(blob,mime)
    if not (pregunta or '').strip(): raise ValueError('Escribí tu pregunta sobre la imagen')
    if proveedor not in SUPPORTED: raise ValueError('Proveedor no integrado para análisis visual')
    proveedor,default=choose_provider(proveedor,'SKY Vision')
    modelo=modelo or default
    prompt='Analizá esta imagen y respondé en español con precisión. No adivinés datos no visibles. '+pregunta[:3500]
    if proveedor=='gemini':
        from .gemini_provider import analizar_imagen
        return analizar_imagen(prompt,blob,mime,modelo=modelo)
    if proveedor=='openai':
        from openai import OpenAI
        with OpenAI(api_key=os.environ['OPENAI_API_KEY'],timeout=60,max_retries=1) as cli:
            r=cli.responses.create(model=modelo,store=False,
                input=[{'role':'user','content':[{'type':'input_text','text':prompt},
                    {'type':'input_image','image_url':f'data:{mime};base64,{base64.b64encode(blob).decode("ascii")}'}]}],
                max_output_tokens=1300)
            return (r.output_text or '').strip()
    if proveedor=='anthropic':
        from anthropic import Anthropic
        with Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'],timeout=60,max_retries=1) as cli:
            r=cli.messages.create(model=modelo,max_tokens=1300,messages=[{'role':'user','content':[
                {'type':'text','text':prompt}, {'type':'image','source':{'type':'base64','media_type':mime,
                    'data':base64.b64encode(blob).decode('ascii')}}]}])
            return '\n'.join(p.text for p in r.content if getattr(p,'type',None)=='text')
    if proveedor=='ollama':
        from urllib import request
        import json
        payload=json.dumps({'model':modelo,'messages':[{'role':'user','content':prompt,
            'images':[base64.b64encode(blob).decode('ascii')]}],'stream':False}).encode()
        req=request.Request('http://127.0.0.1:11434/api/chat',payload,{'Content-Type':'application/json'},method='POST')
        with request.urlopen(req,timeout=120) as response:
            return str(json.load(response).get('message',{}).get('content','')).strip()
    raise ProviderError('Proveedor no compatible con visión')
