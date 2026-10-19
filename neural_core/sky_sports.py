"""SKY Sports Center: consultas bajo demanda, predicciones explicables y TV oficial.

No hospeda, extrae, reproduce ni enlaza señales no autorizadas.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import exp, factorial
from os import getenv
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json
import re
import unicodedata

MADRID_ID = 86  # Identificador documentado por football-data.org
LIVE_STATES = {"IN_PLAY", "PAUSED", "EXTRA_TIME", "PENALTY_SHOOTOUT"}
API_BASE = "https://api.football-data.org/v4"
TZ_NICARAGUA = ZoneInfo("America/Managua")


class SportsDataError(RuntimeError):
    """Error recuperable o fuente deportiva no configurada."""


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto.lower())
                       if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes).strip()


def orden_ver_madrid(texto: str) -> bool:
    """Solo reconoce órdenes explícitas de transmisión del Real Madrid."""
    t = _normalizar(texto)
    orden = re.search(r"\b(muestrame|ponme|pon|abre|reproduce|reproduceme|quiero ver)\b", t)
    partido = re.search(r"\b(partido|encuentro|juego)\b", t)
    club = re.search(r"\b(real madrid|madrid)\b", t)
    directo = re.search(r"\b(en vivo|en directo|directo|transmision)\b", t)
    return bool(orden and partido and club and directo)


def partidos_equipo(equipo: int = MADRID_ID, *, estado: str | None = None,
                    desde: str | None = None, hasta: str | None = None,
                    limite: int = 12) -> list[dict]:
    """Cliente de solo lectura; destino HTTP fijo, credencial solo del servidor."""
    token = getenv("SKY_FOOTBALL_DATA_TOKEN", "").strip()
    if not token:
        raise SportsDataError("Configurá SKY_FOOTBALL_DATA_TOKEN para consultar partidos reales.")
    if type(equipo) is not int or equipo <= 0 or equipo > 100000:
        raise ValueError("ID de equipo inválido")
    if not 1 <= limite <= 100:
        raise ValueError("Límite fuera de rango")
    args: dict[str, str | int] = {"limit": limite}
    if estado:
        if estado not in {"FINISHED", "SCHEDULED", "LIVE", "IN_PLAY", "PAUSED"}:
            raise ValueError("Estado no permitido")
        args["status"] = estado
    for clave, valor in (("dateFrom", desde), ("dateTo", hasta)):
        if valor is not None:
            try:
                datetime.strptime(valor, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError("Fecha incorrecta, usá AAAA-MM-DD") from exc
            args[clave] = valor
    url = f"{API_BASE}/teams/{equipo}/matches?{urlencode(args)}"
    req = Request(url, headers={"X-Auth-Token": token,
                                "Accept": "application/json",
                                "User-Agent": "SKY-Sports-Center/1.0"})
    try:
        with urlopen(req, timeout=10) as response:
            data = response.read(800001)
    except HTTPError as exc:
        if exc.code == 429:
            raise SportsDataError("El proveedor limitó las consultas; reintentá más tarde.") from exc
        raise SportsDataError(f"El proveedor deportivo respondió HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise SportsDataError("No fue posible conectar con los resultados deportivos.") from exc
    if len(data) > 800000:
        raise SportsDataError("Respuesta demasiado grande")
    try:
        matches = json.loads(data).get("matches", [])
    except (ValueError, AttributeError) as exc:
        raise SportsDataError("Respuesta deportiva no válida") from exc
    if not isinstance(matches, list):
        raise SportsDataError("Formato de partidos no válido")
    return [x for x in matches if isinstance(x, dict)][:limite]


def partido_actual_o_proximo() -> tuple[dict | None, dict | None]:
    """Comprueba en vivo solo cuando el usuario ordena consultar/ver."""
    ahora = datetime.now(timezone.utc)
    desde = (ahora - timedelta(days=1)).strftime("%Y-%m-%d")
    hasta = (ahora + timedelta(days=2)).strftime("%Y-%m-%d")
    alrededor = partidos_equipo(desde=desde, hasta=hasta, limite=30)
    vivos = [m for m in alrededor if m.get("status") in LIVE_STATES]
    if vivos:
        return sorted(vivos, key=lambda m: m.get("utcDate", ""))[0], None
    futuros = [m for m in alrededor if m.get("status") in {"SCHEDULED", "TIMED"}]
    if not futuros:
        futuros = partidos_equipo(estado="SCHEDULED", limite=20)
    futuros.sort(key=lambda m: m.get("utcDate", ""))
    return None, futuros[0] if futuros else None


def descripcion_partido(match: dict) -> str:
    local = match.get("homeTeam") or {}
    visita = match.get("awayTeam") or {}
    nombre_local = local.get("shortName") or local.get("name") or "Local"
    nombre_visita = visita.get("shortName") or visita.get("name") or "Visitante"
    fecha = match.get("utcDate")
    try:
        hora = datetime.fromisoformat(fecha.replace("Z", "+00:00")).astimezone(TZ_NICARAGUA)
        horario = hora.strftime("%d/%m/%Y, %I:%M %p") + " (Nicaragua)"
    except (ValueError, AttributeError):
        horario = "Horario no confirmado"
    status = match.get("status") or "Sin estado"
    scores = (match.get("score") or {}).get("fullTime") or {}
    marcador = ""
    if status in LIVE_STATES | {"FINISHED"} and isinstance(scores.get("home"), int) and isinstance(scores.get("away"), int):
        marcador = f" · {scores['home']}-{scores['away']}"
    return f"{nombre_local} vs. {nombre_visita}{marcador} · {horario} · {status}"


def plataforma_oficial(match: dict) -> tuple[str, str]:
    """Guía legal territorial, NO URL de streaming ni enlace a un reproductor pirata."""
    codigo = (match.get("competition") or {}).get("code", "")
    if codigo == "PD":
        return "ViX Premium / Sky Sports (verificar plan y derechos en Nicaragua)", "https://vix.com/"
    if codigo == "CL":
        return "ESPN, operador señalado por UEFA para Centroamérica (consultar disponibilidad)", "https://www.espn.com/"
    return "Consultá los operadores autorizados por el torneo", "https://www.laliga.com/es-US/donde-ver-laliga-easports"


def respuesta_orden_madrid() -> tuple[str, str | None]:
    vivo, siguiente = partido_actual_o_proximo()
    if vivo is None:
        if siguiente:
            return ("⚽ No aparece un partido del Real Madrid en vivo en la fuente consultada. "
                    f"Próximo encuentro: {descripcion_partido(siguiente)}. "
                    "No se abrirá ningún reproductor sin una transmisión autorizada.", None)
        return ("⚽ No encontré un partido del Real Madrid en vivo en los datos disponibles. "
                "La cobertura de la API puede ser parcial.", None)
    plataforma, enlace = plataforma_oficial(vivo)
    return (f"🔴 Partido en vivo identificado: {descripcion_partido(vivo)}.\n\n"
            f"Operador oficial orientativo: {plataforma}. "
            "Abrí el servicio autorizado con tu suscripción; "
            "SKY no retransmite ni salta sus protecciones.", enlace)


def _goles(equipo: int, partidos: list[dict]) -> tuple[float, float, int]:
    jugados: list[tuple[int, int]] = []
    for m in partidos:
        if m.get("status") != "FINISHED":
            continue
        resultado = (m.get("score") or {}).get("fullTime") or {}
        casa, fuera = resultado.get("home"), resultado.get("away")
        if type(casa) is not int or type(fuera) is not int:
            continue
        if (m.get("homeTeam") or {}).get("id") == equipo:
            jugados.append((casa, fuera))
        elif (m.get("awayTeam") or {}).get("id") == equipo:
            jugados.append((fuera, casa))
    if not jugados:
        return 0.0, 0.0, 0
    ultimos = jugados[-10:]
    n = len(ultimos)
    return sum(x[0] for x in ultimos)/n, sum(x[1] for x in ultimos)/n, n


def pronostico_simple(proximo: dict, historial_local: list[dict],
                      historial_visita: list[dict]) -> dict:
    """Poisson orientativo con muestras verificables; nunca es certeza ni recomendación de apuestas."""
    local_id = (proximo.get("homeTeam") or {}).get("id")
    visita_id = (proximo.get("awayTeam") or {}).get("id")
    if not isinstance(local_id, int) or not isinstance(visita_id, int):
        raise SportsDataError("Faltan identificadores de equipos")
    gl, cl, nl = _goles(local_id, historial_local)
    gv, cv, nv = _goles(visita_id, historial_visita)
    if min(nl, nv) < 5:
        raise SportsDataError("Se necesitan al menos cinco resultados completos de cada equipo.")
    lam_local = min(4.5, max(0.15, (gl + cv)/2))
    lam_visita = min(4.5, max(0.15, (gv + cl)/2))
    ph = [exp(-lam_local)*lam_local**k/factorial(k) for k in range(10)]
    pa = [exp(-lam_visita)*lam_visita**k/factorial(k) for k in range(10)]
    gana_local = sum(ph[i]*pa[j] for i in range(10) for j in range(i))
    empate = sum(ph[i]*pa[i] for i in range(10))
    gana_visita = sum(ph[i]*pa[j] for j in range(10) for i in range(j))
    masa = gana_local + empate + gana_visita
    if masa == 0:
        raise SportsDataError("No fue posible estimar probabilidades")
    return {"local": round(100*gana_local/masa, 1),
            "empate": round(100*empate/masa, 1),
            "visitante": round(100*gana_visita/masa, 1),
            "muestra_local": nl, "muestra_visitante": nv,
            "modelo": "Poisson básico experimental; sin lesiones, alineaciones ni cuotas"}


def pronosticar_proximo() -> tuple[dict, dict]:
    _, siguiente = partido_actual_o_proximo()
    if not siguiente:
        raise SportsDataError("Sin próximo partido confirmado en el proveedor")
    local_id = (siguiente.get("homeTeam") or {}).get("id")
    visita_id = (siguiente.get("awayTeam") or {}).get("id")
    if not isinstance(local_id, int) or not isinstance(visita_id, int):
        raise SportsDataError("Equipos sin ID")
    historial_local = partidos_equipo(local_id, estado="FINISHED", limite=10)
    historial_visita = partidos_equipo(visita_id, estado="FINISHED", limite=10)
    return siguiente, pronostico_simple(siguiente, historial_local, historial_visita)
