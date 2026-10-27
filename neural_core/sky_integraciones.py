"""SKY v12.4 — Centro de integraciones: qué plataforma usa SKY, por qué vía y si está lista.

Tener una cuenta de ChatGPT, Gemini, Claude, Canva o Adobe NO da acceso a sus APIs: cada plataforma pide su
propia clave, credenciales u OAuth, y algunas no tienen API pública. Este registro lo dice tal cual.

Vías:
    api      API oficial con clave en .env
    oauth    requiere autorizar una app con OAuth (pendiente de implementar en SKY)
    mcp      servidor MCP (para clientes como Claude; SKY no lo usa directamente)
    local    programa instalado en tu equipo
    agente   lo ejecuta el agente de SKY en cada dispositivo
    sin_api  no hay API pública: SKY prepara el contenido y vos lo usás en la plataforma
"""
from __future__ import annotations

import os
import re
import shutil


def _hay(*variables: str) -> bool:
    return all(os.getenv(v, '').strip() or os.getenv(v + '_FILE', '').strip() for v in variables)


INTEGRACIONES = [
    # id, nombre, vía, variables, para qué la usa SKY, nota honesta, documentación
    ('ollama', 'Ollama (IA local)', 'local', [], 'Cerebro con herramientas 100 % local', 'Gratis; corre en tu PC.', 'https://ollama.com'),
    ('openai', 'OpenAI (GPT)', 'api', ['OPENAI_API_KEY'], 'Cerebro en la nube, conversación e imágenes',
     'La suscripción de ChatGPT no incluye la API: se paga aparte en platform.openai.com.', 'https://platform.openai.com'),
    ('anthropic', 'Anthropic (Claude)', 'api', ['ANTHROPIC_API_KEY'], 'Cerebro en la nube y conversación',
     'Claude Pro/Max no incluye la API: se crea la clave en console.anthropic.com.', 'https://console.anthropic.com'),
    ('gemini', 'Google Gemini', 'api', ['GEMINI_API_KEY'], 'Cerebro en la nube y conversación',
     'Gemini Advanced no incluye la API: la clave se crea en Google AI Studio.', 'https://aistudio.google.com'),
    ('openai_imagenes', 'Imágenes con OpenAI', 'api', ['OPENAI_API_KEY'], 'Generar imágenes (sky-creative)',
     'Cada imagen consume créditos de la API.', 'https://developers.openai.com/api/docs/guides/image-generation'),
    ('firefly', 'Adobe Firefly Services', 'api', ['FIREFLY_CLIENT_ID', 'FIREFLY_CLIENT_SECRET'], 'Generar imágenes (sky-creative)',
     'Requiere credenciales server-to-server de Firefly Services (Adobe Developer Console, en general vía tu representante de Adobe). '
     'Creative Cloud solo no alcanza.', 'https://developer.adobe.com/firefly-services/docs/firefly-api/'),
    ('gamma', 'Gamma', 'api', ['GAMMA_API_KEY'], 'Presentaciones, documentos y webs (sky-creative)',
     'Las claves de API están disponibles en planes Pro, Ultra, Team y Business.', 'https://developers.gamma.app'),
    ('canva', 'Canva', 'oauth', [], 'Diseños en tu cuenta de Canva',
     'Canva Connect API exige una integración OAuth: pendiente en SKY. Mientras tanto SKY prepara textos y estructura.', 'https://www.canva.dev/docs/connect/'),
    ('suno', 'Suno (música)', 'sin_api', [], 'Canciones',
     'Suno no tiene API pública (sólo explora un programa de socios). SKY escribe la letra, la estructura y el estilo para pegar en Suno.',
     'https://suno.com'),
    ('github', 'GitHub', 'api', ['GITHUB_TOKEN'], 'Leer tus repositorios y ayudarte a programar',
     'Token personal de GitHub con permisos mínimos.', 'https://github.com/settings/tokens'),
    ('copilot', 'GitHub Copilot', 'local', [], 'Programar dentro de tu editor',
     'Copilot vive en VS Code; SKY abre VS Code y te ayuda con su Intérprete, pero no controla Copilot.', 'https://github.com/features/copilot'),
    ('correo', 'Correo (IMAP/SMTP)', 'api', ['SKY_MAIL_USER', 'SKY_MAIL_APP_PASSWORD'], 'Leer, redactar y enviar con tu aprobación',
     'Contraseña de aplicación, no tu contraseña real.', 'https://myaccount.google.com/apppasswords'),
    ('google_calendar', 'Google Calendar / Drive', 'oauth', [], 'Agenda y documentos en la nube',
     'Requiere OAuth con tu cuenta de Google: pendiente en SKY (la agenda local de SKY sí funciona).', 'https://developers.google.com/calendar'),
    ('whatsapp', 'WhatsApp (Meta Cloud API)', 'api', ['SKY_WA_TOKEN', 'SKY_WA_PHONE_ID', 'SKY_WA_APP_SECRET', 'SKY_WA_VERIFY_TOKEN', 'SKY_WA_OWNER'],
     'Hablarle a SKY desde el celular', 'Número de WhatsApp Business; 1000 mensajes de servicio gratis por mes.', 'docs/guias/SKY_WHATSAPP.md'),
    ('home_assistant', 'Home Assistant', 'api', ['SKY_HA_URL', 'SKY_HA_TOKEN'], 'Luces, clima, escenas y cerraduras (sky-smart-home)',
     'Token de larga duración de tu Home Assistant.', 'https://www.home-assistant.io'),
    ('youtube', 'YouTube Data API', 'api', ['YOUTUBE_API_KEY'], 'Reproductor interno', 'Clave gratuita de Google Cloud.', 'https://console.cloud.google.com'),
    ('piper', 'Piper (voz local)', 'local', [], 'Voz natural de SKY', 'Lo instala el instalador de SKY.', 'https://github.com/rhasspy/piper'),
    ('whisper', 'faster-whisper (escucha local)', 'local', [], 'Transcribir tu voz y tus notas de voz', 'Lo instala el instalador de SKY.', 'https://github.com/SYSTRAN/faster-whisper'),
    ('agente', 'Agente de SKY en cada equipo', 'agente', [], 'Abrir apps, música, ventanas, archivos',
     'Hay que instalarlo en cada computadora que SKY controla.', 'agente_dispositivo.py'),
    ('openrouter', 'OpenRouter (modelos opcionales)', 'api', ['OPENROUTER_API_KEY', 'OPENROUTER_MODEL'],
     'Modelo de conversación explícito, sin cambiar el proveedor automático',
     'Requiere clave, modelo y cuotas; no prueba de conexión.', 'https://openrouter.ai/docs/api_reference/overview'),
    ('huggingface', 'Hugging Face Inference', 'api', ['HF_TOKEN', 'HF_MODEL'],
     'Modelos adicionales de conversación a solicitud del dueño',
     'Requiere token con permisos de inferencia y modelo; pueden existir cargos.', 'https://huggingface.co/docs/inference-providers'),
    ('semantic_scholar', 'Semantic Scholar', 'api', ['SEMANTIC_SCHOLAR_API_KEY'],
     'Literatura científica y DOIs', 'Clave opcional para consultas; anónimo sujeto a límites.', 'https://api.semanticscholar.org/api-docs/'),
    ('zotero', 'Zotero (biblioteca privada)', 'api', ['SKY_ZOTERO_USER_ID', 'SKY_ZOTERO_API_KEY'],
     'Consultar referencias propias en modo lectura', 'No publica contenidos ni crea referencias automáticamente.', 'https://www.zotero.org/support/dev/web_api/v3/basics'),
    ('wolfram', 'Wolfram Alpha Short Answers', 'api', ['SKY_WOLFRAM_APP_ID'],
     'Respuestas computacionales puntuales', 'API y cuota aparte; validar las unidades y conclusiones.', 'https://products.wolframalpha.com/short-answers-api/documentation'),
    ('n8n', 'n8n controlado', 'api', ['SKY_N8N_URL', 'SKY_N8N_API_KEY'],
     'Consultar flujos y ejecuciones sin datos confidenciales',
     'Para disparar un flujo se necesita PIN, allowlist y aprobación explícita.', 'https://docs.n8n.io/api/'),
    ('hermes-agent', 'Hermes Agent (consultor)', 'local', ['SKY_HERMES_ENABLED', 'SKY_HERMES_KEY'],
     'Investigar, analizar y planificar a pedido («SKY, preguntale a Hermes…»)',
     'Corre aparte con hermes gateway; SKY sólo le pregunta y se niega si tiene herramientas que actúan sobre tu equipo.',
     'docs/guias/SKY_HERMES.md'),
    ('mcp', 'Servidores MCP', 'mcp', [], 'Conectar herramientas a clientes de IA',
     'SKY no ejecuta servidores MCP de terceros: para eso está el Skill Builder con pruebas aisladas y tu aprobación.', 'https://modelcontextprotocol.io'),
]


def _estado_local(iid: str) -> bool:
    try:
        if iid == 'ollama':
            from .sky_cerebro import _ollama_ok
            return _ollama_ok()
        if iid == 'piper':
            from .sky_tts import disponible
            return disponible()
        if iid == 'whisper':
            from .sky_stt_local import capabilities
            return bool(capabilities().get('available'))
        if iid == 'copilot':
            return bool(shutil.which('code'))
        if iid == 'hermes-agent':
            from .sky_hermes import requisitos
            return not requisitos(probar_red=False)   # configurado; la conexión se comprueba al consultar
        if iid == 'agente':
            from .sky_asistente_personal import token_agente_local
            return len(token_agente_local()) >= 32
    except Exception:
        return False
    return False


def listar() -> list[dict]:
    salida = []
    for iid, nombre, via, variables, uso, nota, docs in INTEGRACIONES:
        if via == 'api':
            listo = _hay(*variables)
        elif via in ('local', 'agente'):
            listo = _estado_local(iid)
        else:
            listo = False
        salida.append({'id': iid, 'nombre': nombre, 'via': via, 'variables': variables, 'uso': uso, 'nota': nota,
                       'docs': docs, 'lista': listo,
                       'estado': 'lista' if listo else {'oauth': 'pendiente (OAuth)', 'sin_api': 'sin API pública',
                                                         'mcp': 'no aplica', 'local': 'no disponible',
                                                         'agente': 'no instalado'}.get(via, 'sin configurar')})
    return salida


def lista(iid: str) -> bool:
    return any(i['id'] == iid and i['lista'] for i in listar())


def describir() -> str:
    items = listar()
    listas = [i['nombre'] for i in items if i['lista']]
    faltan = [i['nombre'] for i in items if not i['lista'] and i['via'] == 'api']
    sin = [i['nombre'] for i in items if i['via'] in ('sin_api', 'oauth')]
    return (f"Listas: {', '.join(listas) or 'ninguna'}. Sin configurar: {', '.join(faltan) or 'ninguna'}. "
            f"Sin API pública o con OAuth pendiente: {', '.join(sin)}. El detalle está en Módulos → Habilidades.")


def interpretar(t: str) -> dict | None:
    if re.fullmatch(r'(?:que|cuales) integraciones (?:tengo|tienes|hay)|(?:muestra(?:me)?|mostra(?:me)?|ver) (?:las |mis )?integraciones|'
                    r'estado de (?:las )?integraciones', t):
        return {'tipo': 'respuesta', 'mensaje': describir(), 'proveedor': 'sky-integraciones', 'modulo': 'habilidades'}
    return None
