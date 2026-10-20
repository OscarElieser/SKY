"""Google Gemini via SDK oficial; las claves siempre se leen del entorno local."""
import os

class GeminiError(RuntimeError):
    pass


def disponible():
    return bool(os.getenv('GEMINI_API_KEY','').strip())


def _cliente():
    key = os.environ.get('GEMINI_API_KEY','').strip()
    if not key:
        raise GeminiError('Configura GEMINI_API_KEY en tu archivo .env privado.')
    try:
        from google import genai
    except ImportError as exc:
        raise GeminiError('Instala dependencias: pip install -r requirements.txt') from exc
    return genai.Client(api_key=key)


def responder_gemini(mensajes, modelo=None, max_tokens=2500):
    """Mensajes estilo [{role,content}]; sin ejecutar herramientas externas."""
    modelo = modelo or os.getenv('GEMINI_MODEL','gemini-flash-latest')
    if not mensajes or mensajes[0].get('role') != 'system':
        raise ValueError('Falta la instrucción de sistema.')
    system = mensajes[0]['content']
    historial = [{'role':'model' if m['role']=='assistant' else 'user',
                  'parts':[{'text':str(m['content'])[:10000]}]}
                 for m in mensajes[1:] if m.get('role') in ('user','assistant')]
    if not historial or historial[-1]['role'] != 'user':
        raise ValueError('Se requiere una pregunta de usuario.')
    from google.genai import types
    client=_cliente()
    try:
        res=client.models.generate_content(
            model=modelo, contents=historial,
            config=types.GenerateContentConfig(system_instruction=system,
                temperature=0.2, max_output_tokens=max_tokens))
        texto=(res.text or '').strip()
        if not texto:
            raise GeminiError('Gemini devolvió una respuesta vacía; revisa límites y filtros del proveedor.')
        return texto
    except GeminiError:
        raise
    except Exception as exc:
        raise GeminiError(f'Gemini no respondió: {type(exc).__name__}: {exc}') from exc
    finally:
        client.close()


def analizar_imagen(pregunta, contenido, tipo_mime, modelo=None):
    """Análisis de imágenes JPEG, PNG, WebP. Máximo 8 MB por imagen."""
    if tipo_mime not in ('image/jpeg','image/png','image/webp'):
        raise ValueError('Formato de imagen no admitido')
    if len(contenido) > 8_000_000:
        raise ValueError('Imagen demasiado grande (máximo 8 MB)')
    from google.genai import types
    client=_cliente()
    try:
        resultado=client.models.generate_content(
            model=modelo or os.getenv('GEMINI_MODEL','gemini-flash-latest'),
            contents=[pregunta[:4000], types.Part.from_bytes(data=contenido,mime_type=tipo_mime)])
        return (resultado.text or '').strip() or 'El modelo no devolvió texto.'
    except Exception as exc:
        raise GeminiError(f'Error al analizar imagen: {type(exc).__name__}: {exc}') from exc
    finally:
        client.close()


def generar_imagen(descripcion, modelo=None):
    """Generación de imágenes si el modelo y la cuenta Gemini lo permiten."""
    if len(descripcion.strip()) < 4:
        raise ValueError('Escribe una descripción.')
    from google.genai import types
    client=_cliente()
    try:
        respuesta=client.models.generate_content(
            model=modelo or os.getenv('GEMINI_IMAGE_MODEL','gemini-3.1-flash-lite-image'),
            contents=descripcion[:3500],
            config=types.GenerateContentConfig(response_modalities=['IMAGE']))
        for candidato in (respuesta.candidates or []):
            for parte in (candidato.content.parts or []):
                imagen=getattr(parte,'inline_data',None)
                if imagen and getattr(imagen,'data',None):
                    return imagen.data, imagen.mime_type or 'image/png'
        raise GeminiError('No se generó una imagen. Verifica si el modelo admite salida IMAGE en tu cuenta.')
    except GeminiError:
        raise
    except Exception as exc:
        raise GeminiError(f'No se pudo generar la imagen: {type(exc).__name__}: {exc}') from exc
    finally:
        client.close()
