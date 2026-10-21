"""Audio push-to-talk en el navegador: transcripción Gemini y voz TTS opcional."""
from __future__ import annotations
import io
import os
from .gemini_provider import _cliente, GeminiError


def transcribir_audio(audio: bytes, mime: str='audio/wav',modelo: str|None=None)->str:
    if mime!='audio/wav' or not audio or len(audio)>10_000_000:
        raise ValueError('Grabá un audio WAV de hasta 10 MB.')
    from google.genai import types
    client=_cliente()
    try:
        output=client.models.generate_content(
            model=modelo or os.getenv('GEMINI_MODEL','gemini-flash-latest'),
            contents=[types.Part.from_bytes(data=audio,mime_type=mime),
                      'Transcribe exactamente en español lo que dice la persona. Devuelve únicamente la transcripción, sin explicaciones.'])
        result=(output.text or '').strip()
        if not result: raise GeminiError('No se escuchó o transcribió voz. Repetí la grabación.')
        return result[:7000]
    except GeminiError: raise
    except Exception as exc: raise GeminiError(f'No se pudo transcribir el audio: {exc}') from exc
    finally: client.close()


def hablar_texto(texto: str, idioma='es')->bytes | None:
    """Audio MP3 mediante gTTS; genera voz clara para el navegador."""
    try:
        import re
        from gtts import gTTS
        clean_text = re.sub(r'[*_#`\[\]\(\)\<\>]', '', str(texto))
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()[:1000]
        if not clean_text:
            return None
        buffer=io.BytesIO()
        gTTS(text=clean_text,lang=idioma,slow=False).write_to_fp(buffer)
        return buffer.getvalue()
    except Exception:
        return None


def hablar_local(texto: str) -> None:
    """Habla en el altavoz local de Windows mediante pyttsx3 sin latencia."""
    try:
        import re, pyttsx3
        clean = re.sub(r'[*_#`\[\]\(\)\<\>]', '', str(texto))
        clean = re.sub(r'\s+', ' ', clean).strip()[:1000]
        if clean:
            engine = pyttsx3.init()
            engine.say(clean)
            engine.runAndWait()
    except Exception:
        pass
