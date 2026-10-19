"""SKY Sports Center: interfaz de agenda y canales inspirada en una guía deportiva.

No carga videos, iframes ni señales al consultar la agenda. El reproductor solo
se prepara tras una orden explícita del usuario y confirmar un partido en vivo.
"""
from __future__ import annotations

from datetime import date
from os import getenv
from urllib.parse import urlsplit

from .sky_sports import (
    SportsDataError, agenda_fecha, descripcion_partido, orden_ver_madrid,
    partido_actual_o_proximo, pronosticar_proximo, respuesta_orden_madrid,
)
from .actualidad import noticias

# Catálogo informativo; un canal listado NO implica derechos ni disponibilidad.
CANALES_GUIA = (
    ("ESPN 1", "Fútbol internacional y programas deportivos"),
    ("ESPN 2", "Competiciones y otras disciplinas"),
    ("ESPN 3", "Programación deportiva"),
    ("DSports", "Competiciones y cobertura internacional"),
    ("DSports 2", "Programación deportiva alternativa"),
    ("FOX Sports", "Noticias y eventos deportivos"),
    ("TUDN", "Cobertura deportiva según territorio"),
    ("Sky Sports", "Cobertura deportiva según territorio"),
)


def _embed_autorizado() -> str | None:
    """Solo admite URL HTTPS de dominio exacto autorizado por el administrador.

    La lista debe indicar dominios oficiales con permiso de incrustación.
    Sin configuración, NO se incrusta video.
    """
    url = getenv("SKY_SPORTS_EMBED_URL", "").strip()
    hosts = {h.strip().lower() for h in
             getenv("SKY_SPORTS_ALLOWED_EMBED_HOSTS", "").split(",") if h.strip()}
    if not url or not hosts:
        return None
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
        return None
    if host not in hosts:
        return None
    return url


def mostrar_reproductor_solicitado(st, enlace_oficial: str | None) -> None:
    """Mostrar player SOLO en respuesta a una orden explícita ya verificada.

    No se autoejecutan streams; si no hay embed con autorización, enlace oficial.
    """
    if not enlace_oficial:
        return
    st.markdown("#### 📺 Pantalla SKY — Real Madrid")
    embed = _embed_autorizado()
    if embed:
        st.caption("Reproductor autorizado configurado por el administrador. Pulsá ▶ para iniciar.")
        if "youtube.com" in (urlsplit(embed).hostname or "") or (urlsplit(embed).hostname or "") == "youtu.be":
            st.video(embed)
        else:
            import streamlit.components.v1 as components
            components.iframe(embed, height=480, scrolling=False)
        st.caption("Si el operador bloquea la incrustación, abrí su aplicación oficial.")
    else:
        st.info("Pantalla lista. Para visualizar el video dentro de SKY, el operador debe proporcionar una URL de inserción autorizada. Por ahora podés abrir su servicio oficial.")
    st.link_button("Abrir operador autorizado", enlace_oficial)


def _cabecera(st):
    st.markdown(
        """<div style="background:linear-gradient(115deg,#0d1426,#172c55 58%,#394465);
        border-radius:18px;padding:24px 26px;color:white;margin-bottom:13px">
        <div style="font-size:12px;letter-spacing:.12em;color:#d4c6a2">SKY SPORTS CENTER</div>
        <div style="font-size:31px;font-weight:750;margin:7px 0">⚽ Pasión por el Real Madrid</div>
        <div style="font-size:14px;color:#e5e7eb">Agenda • Canales • Partido en vivo • Pronósticos • Noticias</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption("Guía inspirada en la navegación por partidos y canales de Fútbol Libre Full HD; interfaz y contenido propios. Los videos requieren licencia y disponibilidad regional.")


def render_sports_center(st) -> None:
    """Página deportiva: navegación libre, reproducción solo a petición."""
    _cabecera(st)
    st.markdown("### 🎙️ Pedime el partido del Madrid")
    frase = st.text_input(
        "Orden de voz transcrita o texto",
        placeholder="SKY, muéstrame el partido en vivo del Real Madrid",
        key="sky_sports_tv_command",
    )
    if st.button("📺 Mostrar partido en vivo de Madrid", key="sky_sports_tv_execute", type="primary"):
        if not orden_ver_madrid(frase):
            st.warning("La transmisión solo puede solicitarse con una orden explícita, como: SKY, muéstrame el partido en vivo del Real Madrid.")
            st.session_state.pop("sky_sports_tv_result", None)
        else:
            try:
                st.session_state["sky_sports_tv_result"] = respuesta_orden_madrid()
            except SportsDataError as exc:
                st.session_state["sky_sports_tv_result"] = (str(exc), None)
    resultado = st.session_state.get("sky_sports_tv_result")
    if resultado:
        mensaje, enlace = resultado
        st.write(mensaje)
        mostrar_reproductor_solicitado(st, enlace)

    tabs = st.tabs(["📅 Agenda de partidos", "📡 Canales deportivos", "🤍 Real Madrid", "📊 Predicciones", "📰 Noticias"])

    with tabs[0]:
        st.subheader("Agenda futbolística")
        fecha = st.date_input("Elegí la fecha de los partidos", value=date.today(), key="sky_sports_calendar")
        if st.button("🔄 Consultar agenda", key="sky_sports_load_schedule"):
            try:
                st.session_state["sky_sports_schedule"] = agenda_fecha(fecha.isoformat())
                st.session_state["sky_sports_schedule_date"] = fecha.isoformat()
            except (SportsDataError, ValueError) as exc:
                st.warning(str(exc))
                st.session_state.pop("sky_sports_schedule", None)
        agenda = st.session_state.get("sky_sports_schedule")
        if agenda is None:
            st.info("Consultá la agenda para cargar partidos reales. No se inicia reproducción.")
        else:
            st.caption("Fuente: football-data.org · " + st.session_state.get("sky_sports_schedule_date", ""))
            consulta = st.text_input("Buscar equipo o partido", key="sky_sports_search_event")
            torneos = sorted({str((m.get("competition") or {}).get("name") or "Otro") for m in agenda})
            torneo = st.selectbox("Filtrar por competición", ["Todas", *torneos], key="sky_sports_tournament")
            filtrados = []
            for m in agenda:
                rival = " ".join(str((m.get(pos) or {}).get("name") or "") for pos in ("homeTeam", "awayTeam"))
                liga = str((m.get("competition") or {}).get("name") or "Otro")
                if consulta.casefold() not in (rival + " " + liga).casefold():
                    continue
                if torneo != "Todas" and torneo != liga:
                    continue
                filtrados.append(m)
            st.caption(f"{len(filtrados)} encuentros en la selección")
            for m in filtrados[:80]:
                st.markdown("⚽ **" + descripcion_partido(m) + "**")
                st.caption(str((m.get("competition") or {}).get("name") or "Competición no informada"))
                st.divider()
            if not filtrados:
                st.write("No aparecen partidos con estos filtros en la fuente consultada.")

    with tabs[1]:
        st.subheader("Canales y programación deportiva")
        st.caption("Esta es una guía de canales, no una lista de transmisiones activas. SKY no enciende ningún canal sin la orden de ver al Real Madrid.")
        buscar_canal = st.text_input("Buscar canal", key="sky_sports_search_channel")
        canales = [(nombre, desc) for nombre, desc in CANALES_GUIA
                   if buscar_canal.casefold() in nombre.casefold()]
        if not canales:
            st.write("No hay canales con ese nombre.")
        for i in range(0, len(canales), 3):
            columnas = st.columns(3)
            for columna, (nombre, desc) in zip(columnas, canales[i:i+3]):
                with columna:
                    with st.container(border=True):
                        st.markdown("### 📺 " + nombre)
                        st.caption(desc)
                        st.caption("Consultar derechos y señal disponibles en Nicaragua")

    with tabs[2]:
        st.subheader("Próximos encuentros del Real Madrid")
        if st.button("Consultar Madrid", key="sky_sports_real_schedule"):
            try:
                vivo, proximo = partido_actual_o_proximo()
                st.session_state["sky_sports_real_match"] = vivo or proximo
            except SportsDataError as exc:
                st.warning(str(exc))
        madrid = st.session_state.get("sky_sports_real_match")
        if madrid:
            st.write(descripcion_partido(madrid))
            st.caption("El partido se mostrará en el área superior solo si está en vivo y lo solicitás expresamente.")

    with tabs[3]:
        st.subheader("Pronóstico verificable, no certeza")
        if st.button("Calcular predicción", key="sky_sports_make_prediction"):
            try:
                partido, valores = pronosticar_proximo()
                st.write(descripcion_partido(partido))
                col1, col2, col3 = st.columns(3)
                col1.metric("Victoria local", str(valores["local"]) + "%")
                col2.metric("Empate", str(valores["empate"]) + "%")
                col3.metric("Victoria visitante", str(valores["visitante"]) + "%")
                st.caption(valores["modelo"] + ". Basado en " + str(valores["muestra_local"]) +
                           " y " + str(valores["muestra_visitante"]) + " partidos anteriores.")
            except SportsDataError as exc:
                st.warning(str(exc))

    with tabs[4]:
        st.subheader("Actualidad madridista")
        if st.button("Buscar noticias recientes", key="sky_sports_get_news"):
            try:
                st.session_state["sky_sports_news"] = noticias("Real Madrid fútbol", limite=8)
            except Exception as exc:
                st.warning("No se pudieron cargar noticias: " + str(exc))
        for item in st.session_state.get("sky_sports_news", []):
            title = item["titular"].replace("[", "").replace("]", "")
            st.markdown("- [" + title + "](" + item["enlace"] + ")")
            st.caption(item["fecha"])
    st.caption("Las consultas a la API y RSS ocurren a petición. La reproducción nunca se inicia por abrir esta página.")
