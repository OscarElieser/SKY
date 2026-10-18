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


def hablar_texto(texto: str, idioma='es')->bytes:
    """Audio MP3 mediante gTTS; requiere Internet. No almacena audio."""
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise RuntimeError('Instalá gTTS: pip install gTTS') from exc
    buffer=io.BytesIO()
    gTTS(text=str(texto)[:3000],lang=idioma,slow=False).write_to_fp(buffer)
    return buffer.getvalue()
