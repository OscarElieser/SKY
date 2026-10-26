"""Clasificación conservadora de herramientas del cerebro SKY.

Las herramientas siguen registradas en sky_cerebro.herramientas(): esta capa
sólo selecciona cuáles DESCRIBIR al modelo durante cada turno. No ejecuta
acciones ni cambia permisos/autorizaciones. Ante una orden ambigua, usa todo
el catálogo para conservar el comportamiento previo.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9:/._%-]+", " ", text)).strip()


# Las expresiones identifican acciones explícitas, no menciones incidentales
# de productos, apps o datos dentro de una conversación.
_GROUPS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = tuple(
    (re.compile(pattern), names) for pattern, names in (
        (r"\b(?:abre|abri|abrir|inicia|iniciar|lanza|ejecuta|usa)\b.{0,85}\b(?:word|excel|powerpoint|calculadora|navegador|chrome|firefox|vscode|vs code|editor|aplicacion|programa|app)\b",
         ("abrir_app",)),
        (r"\b(?:reproduce|reproduci|reproducir|ponme|poneme|pon|pone|escucha|escuchar|quiero escuchar|quiero ver)\b.{0,100}\b(?:musica|cancion|video|youtube|spotify|tema|playlist|lofi|artista|pelicula)\b",
         ("reproducir", "reproductor_sky")),
        (r"^(?:ponme|poneme|reproduce|reproduci|reproducir)\s+(?!el volumen\b).{2,100}$",
         ("reproducir", "reproductor_sky")),
        (r"\b(?:pausa|pausar|reanuda|reanudar|siguiente|anterior|proxima|detene|deten|continuar|silencia)\b.{0,45}\b(?:musica|cancion|tema|video|pista|reproduccion|reproductor)\b",
         ("multimedia", "reproductor_sky", "volumen")),
        (r"^(?:siguiente|anterior|next|otra cancion|otra|pausa|reanud[a-z]+|dale play)$",
         ("multimedia", "reproductor_sky")),
        (r"\b(?:sube|subi|baja|baji|reduce|aumenta|ajusta|pon|pone|silencia|quita)\b.{0,45}\b(?:volumen|sonido|audio)\b|\bvolumen\b|\b(?:mas fuerte|menos fuerte|mas alto|mas bajo)$",
         ("volumen",)),
        (r"\b(?:busca|buscar|buscame|investiga|consulta|navega)\b.{0,100}\b(?:internet|web|google|youtube|wikipedia|mapas|sitio|en linea|en la red)\b|\b(?:busca en google|busca en internet|busca en youtube)\b",
         ("buscar_web", "aprender_sobre")),
        (r"\b(?:abre|abri|abrir|visita|ingresa|navega)\b.{0,70}\b(?:web|pagina|sitio|https?://|www\.)",
         ("abrir_web",)),
        (r"\b(?:abre|abri|abrir|muestra|mostra|busca|encontra|encontrar)\b.{0,80}\b(?:carpeta|documentos|documento|descargas|escritorio|archivos|archivo|pdf)\b",
         ("abrir_carpeta_o_documento",)),
        (r"\b(?:minimiza|maximiza|restaura|cierra|cerra|organiza|enfoca|lista)\b.{0,65}\b(?:ventana|ventanas|aplicacion|escritorio)\b",
         ("ventanas", "reproductor_sky")),
        (r"\b(?:crea|crear|escribe|anota|guarda|agrega|agregar|elimina|borra)\b.{0,70}\b(?:nota|notas)\b|\b(?:en la nota)\b",
         ("nota",)),
        (r"\b(?:prepara|preparar|crea|crear|haz|hace|genera|generar)\b.{0,70}\b(?:presentacion|diapositivas|documento|informe)\b",
         ("tarea",)),
        (r"\b(?:recuerdame|recordame|avisame|notificame|pon|pone|crea|crear|programa)\b.{0,75}\b(?:recordatorio|alarma|en [0-9]+ minutos|manana|a las [0-9])\b",
         ("recordatorio", "notificacion")),
        (r"\b(?:captura|capturame|screenshot|pantallazo|captura de pantalla)\b",
         ("captura_pantalla",)),
        (r"\b(?:bloquea|bloquear|bloqueame)\b.{0,40}\b(?:equipo|pc|pantalla|computadora)\b",
         ("bloquear_equipo",)),
        (r"\b(?:notificame|muestra una notificacion|manda una notificacion|muestra un aviso)\b",
         ("notificacion",)),
        (r"\b(?:portapapeles|clipboard)\b",
         ("portapapeles",)),
        (r"\b(?:escribe|escribir|teclea|tipea|dicta)\b.{0,80}\b(?:ventana activa|aplicacion activa|en word|en excel|en el editor)\b",
         ("escribir_texto",)),
        (r"\b(?:estado|bateria|cpu|ram|memoria disponible|uso de memoria|recursos del equipo)\b.{0,35}\b(?:computadora|pc|equipo|sistema)\b|\b(?:cuanta ram|como esta mi equipo|estado del equipo)\b",
         ("estado_equipo",)),
        (r"\b(?:aprende|investiga|investigar|estudia|estudiar)\b.{0,75}\b(?:sobre|en internet|en la red)\b",
         ("aprender_sobre", "buscar_web")),
        (r"\b(?:recuerda|recorda|acordate|memoriza|guarda)\s+(?:que|esto|este dato|en tu memoria)\b",
         ("recordar_dato",)),
        (r"\b(?:noticias|titulares|actualidad)\b",
         ("noticias", "buscar_web")),
        (r"\b(?:rendimiento|estadisticas|metricas|kpi|latencia|tareas completadas|tareas fallidas)\b.{0,45}\b(?:sky|asistente|hoy|semana)\b|\b(?:kpis de sky|rendimiento de sky)\b",
         ("rendimiento_sky",)),
        (r"\b(?:enciende|apaga|prende|atenua|activa|desactiva|abre|cierra)\b.{0,65}\b(?:luz|luces|enchufe|clima|persiana|cortina|cerradura|escena)\b",
         ("casa",)),
        (r"\b(?:lee|leer|revisa|revisar|consulta|consultar)\b.{0,55}\b(?:correo|correos|email|emails|bandeja)\b",
         ("leer_correo",)),
    )
)

# La ausencia de coincidencias en una ORDEN no debe deshabilitar
# capacidades que el usuario ya poseía: en ese caso, catálogo completo.
_ACTION = re.compile(
    r"^(?:(?:sky|oye sky|mira sky|por favor)\s+)?"
    r"(?:abre|abri|abrir|cierra|cerra|cerrar|pon|pone|ponme|poneme|"
    r"reproduce|reproducir|haz|hace|hace|haceme|ejecuta|realiza|"
    r"busca|buscame|crea|crear|elimina|borra|muestra|mostra|"
    r"recuerda|recorda|activa|desactiva|envia|manda|programa|"
    r"necesito que|quiero que|podes|puedes)\b"
)
_QUESTION = re.compile(
    r"^(?:que|quien|cual|como|por que|para que|"
    r"explica|explicame|cuentame|hola|buenos dias|buenas tardes|"
    r"buenas noches|gracias|saludos)\b"
)
_CONTEXT_ACTIONS = re.compile(
    r"^(?:otra|siguiente|anterior|mas fuerte|menos fuerte|"
    r"subile|bajale|cerralo|cierralo|abri eso|abre eso|hacelo|hazlo|"
    r"detenlo|pausalo|reanudalo|continua|repite)\b"
)


def select_tool_names(text: str, available: Iterable[str]) -> list[str]:
    """Elige herramientas por turno, manteniendo el orden del catálogo original.

    - Conversaciones normales: no se envía ningún schema de herramienta.
    - Orden conocida: catálogo mínimo relativo a la solicitud.
    - Orden ambigua: catálogo entero para no perder capacidades.
    - Esta función no ejecuta nada ni altera la política de SKY.
    """
    present = list(dict.fromkeys(str(name) for name in available))
    utterance = _norm(text)
    if not utterance:
        return []
    # Una pregunta explicativa sobre Word, volumen o YouTube no es una orden.
    if _QUESTION.match(utterance) and not _ACTION.match(utterance):
        return []
    matched = set()
    for regex, names in _GROUPS:
        if regex.search(utterance):
            matched.update(names)
    if matched:
        return [name for name in present if name in matched]
    if _ACTION.match(utterance) or _CONTEXT_ACTIONS.match(utterance):
        return present
    return []


def select_tools(text: str, tools: list[dict]) -> list[dict]:
    names = select_tool_names(
        text, (tool.get("function", {}).get("name", "") for tool in tools)
    )
    enabled = set(names)
    return [tool for tool in tools if tool.get("function", {}).get("name") in enabled]
