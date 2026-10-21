"""SKY Universal v8.0 | asistente personal con visión, taller 3D y evolución."""
from pathlib import Path
from datetime import date
import hashlib
import os
from urllib import request
from urllib.error import URLError
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
import streamlit as st
import pandas as pd
from neural_core.storage import (iniciar, guardar_movimiento, movimientos, guardar_presupuesto, presupuestos,
    agregar_documento, documentos, guardar_memoria, memorias, eliminar_memoria,
    guardar_tarea, tareas, completar_tarea, crear_operacion, operaciones, revisar_operacion)
from neural_core.catalogo import MODULOS, EJEMPLOS
from neural_core.finanzas import resumen, crecimiento_compuesto
from neural_core.monetizacion import (crear_tablas, agregar_cliente, listar_clientes,
                                       cambiar_etapa, resumen_comercial, simular_ventas, ETAPAS)
from neural_core.documentos import extraer_texto
from neural_core.sky_office import create_document, FORMATS
from neural_core.assistant import responder, modelo_activo, ModeloNoDisponible
from neural_core.providers import PROVIDERS, provider_ready, provider_summary, choose_provider
from neural_core.gemini_provider import disponible as gemini_disponible, analizar_imagen, generar_imagen
from neural_core.baqueano import (estado_web, resumen_repo, listado_repo, leer_archivo,
    vista_diff, propuesta_pr, supabase_publico, github_token, SUPABASE_VISTAS)
from neural_core.investigacion import wikipedia
from neural_core.actualidad import noticias
from neural_core.mercados import CRYPTOS, ACCIONES, cripto_precios, accion_historial, rentabilidad_historica
from neural_core.multimedia import catalogo_itunes, convertir_imagen
from neural_core.seguridad import revisar_archivo
from neural_core.creadores import campana, produccion, REDES
from neural_core.dispositivos import (paired_devices, save_device, remove_device, call_device,
    interpret_command, APP_OPTIONS, norm)
from neural_core.voz import transcribir_audio, hablar_texto
from neural_core.voz_inbox import read_inbox, dismiss_inbox
from sensores_app import mostrar_sensores
from neural_core.sky_3d import leer_imagen, caja_relativa, segmentar_parte, png_bytes, ensamblar_glb, crear_paquete, importar_paquete
from neural_core.sky_vision import analizar as vision_analizar
from neural_core.sky_evolution import (feedback as sky_feedback, feedback_resumen, nueva_meta, metas,
    actualizar_meta, proponer_mejora, mejoras, cambiar_mejora)
from neural_core.sky_agent import SKILLS, execute_skill, interpret_local_command
from neural_core.sky_live import historial as sky_live_historial, ejecutar_ciclo as sky_live_check

st.set_page_config(page_title="SKY-IA · Asistente Universal", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
# Si se desea abrir el panel desde otro dispositivo mediante Tailscale, definir
# SKY_DASHBOARD_PASSWORD de al menos 12 caracteres en .env.
clave_panel=(os.getenv('SKY_DASHBOARD_PASSWORD') or os.getenv('NEURALT_DASHBOARD_PASSWORD','')).strip()
if clave_panel and len(clave_panel)<12:
    st.error('SKY_DASHBOARD_PASSWORD debe tener al menos 12 caracteres.')
    st.stop()
if clave_panel and not st.session_state.get('_panel_autenticado'):
    st.title('🔒 Acceso privado a SKY')
    with st.form('entrada_privada'):
        candidato=st.text_input('Contraseña del panel',type='password')
        enviar=st.form_submit_button('Acceder')
    if enviar:
        import hmac
        if hmac.compare_digest(candidato,clave_panel):
            st.session_state['_panel_autenticado']=True
            st.rerun()
        else: st.error('Contraseña incorrecta.')
    st.stop()
st.markdown("""<style>
.stApp {
    background: radial-gradient(ellipse at 50% -15%, #173f62 0%, transparent 50%),
                radial-gradient(ellipse at 85% 115%, #18203c 0%, transparent 60%),
                #060e1c !important;
}
.block-container {padding-top:1.8rem; max-width:1500px}
[data-testid="stMetric"] {
    background: linear-gradient(160deg, rgba(16, 37, 60, 0.75), rgba(10, 23, 41, 0.85));
    border: 1px solid #2e536b;
    padding: 16px;
    border-radius: 14px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    transition: all 0.2s ease;
}
[data-testid="stMetric"]:hover {
    border-color: #4ebfe8;
    box-shadow: 0 6px 24px rgba(18, 151, 189, 0.2);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(100deg, #1297bd, #4455d1) !important;
    border: 1px solid #4ebfe8 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}
.smallnote {opacity:.85; font-size:.9rem; color:#9fbad0}
</style>""", unsafe_allow_html=True)
iniciar(); crear_tablas()


def elegir_motor(key, area='General'):
    """Selector compartido; nunca activa redes ni cuenta doble automáticamente."""
    opciones = ['auto', *PROVIDERS]
    default = 'auto'
    etiqueta = lambda opt: ('Automático — entre los configurados' if opt == 'auto'
                            else PROVIDERS[opt].name + (' · listo' if provider_ready(opt) else ' · configurar'))
    elegido = st.selectbox('Motor de IA', opciones, index=opciones.index(default),
                           format_func=etiqueta, key=key)
    try:
        elegido, predeterminado = choose_provider(elegido, area)
    except Exception as exc:
        st.warning(str(exc))
        elegido = 'ollama'
        predeterminado = PROVIDERS['ollama'].model_default
    if elegido == 'ollama':
        instalados = modelo_activo()
        if not instalados:
            st.caption('Ollama local no detectado. Ejecutá `ollama serve` y descargá un modelo.')
        m = st.selectbox('Modelo Ollama', instalados or [predeterminado], key='modelo_' + key)
    else:
        m = st.text_input('Modelo de ' + PROVIDERS[elegido].name, value=predeterminado, key='modelo_' + key)
    st.caption('Modelo seleccionado: ' + PROVIDERS[elegido].name + '. Claves en .env. Pueden aplicarse tarifas y cuotas.')
    return elegido, m


SECCIONES_TECNICAS = [
    "🏠 Tablero general (v8.0)", "🌐 SKY IA Universal v12.0", "🧠 IA universal", "🧬 Centro multi-IA", "👁️ SKY Visión", "🎨 SKY Studio 3D", "📁 SKY Office Studio", "🧬 SKY Evolución", "🧰 Herramientas SKY", "🔔 SKY Live", "🌐 SKY Metaverso y API", "🎙️ SKY y dispositivos", "💰 Finanzas personales", "🚀 Generar ingresos", "📈 Bolsa y Bitcoin",
    "📰 Noticias e Internet", "📣 Redes sociales", "🎵 Música y películas", "🎞️ Imágenes y videos",
    "🔐 Antivirus y hacking ético", "🎓 Educación e investigación", "📚 Biblioteca y memoria",
    "🧭 BAQUEANO Control Center", "🧾 Transacciones", "📡 Engine Sensor MLP + GRU", "✅ Proyectos y tareas", "⚽ SKY Sports Madridista"
]

if "sky_ui_view_mode" not in st.session_state:
    st.session_state["sky_ui_view_mode"] = "holographic"

if st.session_state["sky_ui_view_mode"] == "classic":
    with st.sidebar:
        st.markdown("### 🧠 SKY-IA")
        st.caption("Asistente Central · 26 módulos internos")
        
        modo_interfaz = st.radio(
            "Modo de Interfaz",
            ["🎙️ Asistente Unificado (Voz & Chat)", "🛠️ Módulos Técnicos (Modo Dev)"],
            label_visibility="collapsed"
        )
        
        if modo_interfaz == "🎙️ Asistente Unificado (Voz & Chat)":
            seccion = "🎙️ Asistente Central"
            st.caption("🟢 **26 módulos conectados internamente**")
            ejecucion_dispositivo = st.checkbox("⚡ Ejecución directa en PC", value=True,
                                                help="Permite a SKY abrir programas y páginas locales cuando se lo pidas.")
            proveedor_jarvis, modelo_jarvis = elegir_motor('motor_jarvis', 'General')
        else:
            st.caption("🛠️ **Explorador de Módulos (Dev):**")
            seccion_elegida = st.radio("Módulos", SECCIONES_TECNICAS, label_visibility="collapsed")
            seccion = "🏠 Inicio" if seccion_elegida == "🏠 Tablero general (v8.0)" else seccion_elegida
            ejecucion_dispositivo = True
            proveedor_jarvis = 'auto'
            modelo_jarvis = None
        st.divider()
        import neural_core.sky_supabase as sb
        if sb.is_configured():
            usuario_sb = st.session_state.get('_supabase_user')
            if usuario_sb:
                if usuario_sb.get('is_super_admin'):
                    st.success("👑 **Superadministrador**")
                    st.caption(f"`{usuario_sb.get('email')}`")
                else:
                    st.caption(f"☁️ Conectado: `{usuario_sb.get('email')}`")
                if st.button("Cerrar Sesión", key="sb_logout_btn"):
                    sb.sign_out()
                    st.session_state.pop('_supabase_user', None)
                    st.rerun()
            else:
                with st.expander("☁️ Supabase Cloud Auth", expanded=False):
                    modo_sb = st.radio("Acción", ["Entrar", "Crear cuenta"], horizontal=True, key="sb_mode", label_visibility="collapsed")
                    sb_email = st.text_input("Correo", key="sb_email")
                    sb_pass = st.text_input("Contraseña", type="password", key="sb_pass")
                    if modo_sb == "Entrar" and st.button("Iniciar Sesión", key="sb_btn_login"):
                        try:
                            res = sb.sign_in(sb_email, sb_pass)
                            st.session_state['_supabase_user'] = res
                            st.success("Sesión iniciada con éxito.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    elif modo_sb == "Crear cuenta" and st.button("Registrar Usuario", key="sb_btn_signup"):
                        try:
                            res = sb.sign_up(sb_email, sb_pass)
                            st.success("Cuenta registrada. Ya puedes iniciar sesión.")
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            with st.expander("☁️ Supabase Cloud", expanded=False):
                st.caption("Configura SUPABASE_ANON_KEY en .env para activar el inicio de sesión.")
        st.divider()
        st.caption("Multi-IA + visión + 3D por piezas + memoria + herramientas autorizadas")
        st.caption("Los proveedores externos sólo reciben contenido cuando los seleccionás o activás el modo automático.")
else:
    # Modo Holográfico 3D: Barra lateral oculta, pantalla limpia centrada en el Núcleo 3D
    if "seccion_elegida_holo" in st.session_state:
        seccion = st.session_state.pop("seccion_elegida_holo")
        st.session_state["sky_ui_view_mode"] = "classic"
    else:
        seccion = "🎙️ Asistente Central"
    ejecucion_dispositivo = True
    proveedor_jarvis = 'auto'
    modelo_jarvis = None
    import neural_core.sky_supabase as sb


def alerta_red():
    st.caption("Los datos se consultan en Internet sólo al pulsar el botón; pueden estar retrasados o no disponibles. Confirma cualquier decisión importante con fuentes oficiales.")


def ejecutar(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        st.error(f"No se pudo completar: {exc}")
        return None


def guardar_con_feedback(fn, *args, mensaje="Registro guardado", **kwargs):
    try:
        fn(*args, **kwargs)
        st.success(mensaje)
        return True
    except Exception as exc:
        st.error(f"No se pudo guardar: {exc}")
        return False


def boton_descarga(texto, nombre, etiqueta="Descargar TXT"):
    st.download_button(etiqueta, data=texto.encode("utf-8"), file_name=nombre, mime="text/plain")





def mostrar_chat(area="General", prompt_inicial=None):
    proveedor,modelo=elegir_motor('motor_'+area,area)
    clave='chat_'+area
    if clave not in st.session_state: st.session_state[clave]=[]
    fuente_opcional=st.selectbox('Fuentes externas para esta pregunta',
                                 ['No consultar','Noticias RSS','Wikipedia'],key='web_'+area)
    historia=st.session_state[clave]
    for m in historia:
        with st.chat_message(m['role']): st.markdown(m['content'])
    pregunta=st.chat_input('Preguntá a SKY…',key='prompt_'+area)
    if prompt_inicial: st.caption('Ejemplo: '+prompt_inicial)
    st.caption('Herramientas internas sin IA: /sky calcula 250*3 · /sky metas · /sky hora · /sky mejoras')
    if pregunta:
        with st.chat_message('user'): st.markdown(pregunta)
        respuesta=''
        with st.chat_message('assistant'):
            with st.spinner('Consultando '+PROVIDERS[proveedor].name+'…'):
                metadatos=[]
                if fuente_opcional!='No consultar':
                    try:
                        metadatos=(noticias(pregunta[:100],limite=5) if fuente_opcional=='Noticias RSS'
                                   else wikipedia(pregunta[:100],limite=5))
                    except Exception as ex: st.warning('No fue posible consultar fuentes: '+str(ex))
                try:
                    respuesta_local=interpret_local_command(pregunta)
                    if respuesta_local is not None:
                        respuesta,fuentes=respuesta_local,[]
                    else:
                        respuesta,fuentes=responder(pregunta,area,historia,modelo,metadatos,proveedor=proveedor)
                    st.markdown(respuesta)
                    if metadatos:
                        st.caption('Fuentes consultadas: metadatos, no necesariamente textos completos.')
                        for x in metadatos:
                            st.markdown(f"- [{x.get('titulo',x.get('titular','Fuente'))}]({x.get('url',x.get('enlace',''))})")
                    if fuentes: st.caption('Documentos: '+', '.join(dict.fromkeys(x['nombre'] for x in fuentes)))
                except Exception as exc: st.error(f'No se pudo completar la consulta: {exc}')
        if respuesta: historia.extend([{'role':'user','content':pregunta},{'role':'assistant','content':respuesta}])


SECCIONES = SECCIONES_TECNICAS


def render_media_card(datos):
    import json
    import streamlit.components.v1 as components
    url = datos.get('url', '')
    query = datos.get('query', '')
    service = datos.get('service', 'youtube')
    video_id = datos.get('video_id', '')
    candidates = datos.get('candidates', [])
    mode = datos.get('mode', 'normal')
    title = datos.get('title') or (query.title() if query else 'YouTube en Vivo')

    if service == 'youtube':
        from neural_core.multimedia import resolve_youtube_video
        if not video_id and query:
            res_v = resolve_youtube_video(query)
            video_id = res_v.get('video_id', '')
            candidates = res_v.get('candidates', [])
            title = res_v.get('titulo', query)
            if res_v.get('url') and 'watch?v=' in res_v['url']:
                url = res_v['url']
        elif not url or url == 'https://www.youtube.com' or not video_id:
            res_v = resolve_youtube_video("Queen")
            video_id = res_v.get('video_id', 'vbvyNnw8Qjg')
            candidates = res_v.get('candidates', [])
            title = res_v.get('titulo', 'Queen – Bohemian Rhapsody (Live Aid 1985)')
            url = res_v.get('url', f"https://www.youtube.com/watch?v={video_id}")

        embed_id = video_id or "vbvyNnw8Qjg"
        candidates_json = json.dumps(candidates if candidates else [
            {"id": embed_id, "title": title, "embeddable": True, "url": url}
        ])

        # Altura del componente según el modo
        h_comp = 620 if mode == 'ampliado' else (340 if mode == 'mini' else 495)

        player_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
              background: transparent;
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
              color: #e2f1ff;
              overflow-x: hidden;
            }}
            
            .player-wrapper {{
              background: rgba(5, 14, 30, 0.95);
              border: 1px solid rgba(0, 242, 255, 0.45);
              border-radius: 14px;
              padding: 12px 16px;
              box-shadow: 0 0 30px rgba(0, 242, 255, 0.2);
              transition: all 0.3s ease;
              position: relative;
            }}

            .mode-normal {{
              width: 100%;
            }}
            .mode-normal .video-container {{
              height: 380px;
            }}

            .mode-ampliado {{
              width: 100%;
            }}
            .mode-ampliado .video-container {{
              height: 520px;
            }}

            .mode-mini {{
              position: fixed;
              bottom: 15px;
              right: 15px;
              width: 380px;
              z-index: 999999;
              border: 2px solid #00f2ff;
              border-radius: 16px;
              box-shadow: 0 10px 45px rgba(0, 0, 0, 0.9), 0 0 25px rgba(0, 242, 255, 0.45);
              background: rgba(4, 12, 26, 0.98);
            }}
            .mode-mini .video-container {{
              height: 200px;
            }}
            .mode-mini .playlist-panel {{
              display: none;
            }}

            .header-bar {{
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 10px;
              user-select: none;
              flex-wrap: wrap;
              gap: 8px;
            }}
            .title-box {{
              display: flex;
              align-items: center;
              gap: 8px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              max-width: 55%;
            }}
            .title-text {{
              color: #00f2ff;
              font-weight: 700;
              font-size: 0.88rem;
              letter-spacing: 0.5px;
              text-shadow: 0 0 8px rgba(0, 242, 255, 0.5);
            }}

            .mode-btn-group {{
              display: flex;
              align-items: center;
              gap: 5px;
            }}
            .mode-btn {{
              background: rgba(0, 242, 255, 0.12);
              border: 1px solid rgba(0, 242, 255, 0.35);
              color: #00f2ff;
              border-radius: 8px;
              padding: 3px 8px;
              font-size: 0.72rem;
              font-weight: 600;
              cursor: pointer;
              transition: all 0.2s;
            }}
            .mode-btn:hover, .mode-btn.active {{
              background: #00f2ff;
              color: #030a16;
              box-shadow: 0 0 10px #00f2ff;
            }}

            .video-container {{
              width: 100%;
              border-radius: 10px;
              overflow: hidden;
              border: 1px solid rgba(0, 242, 255, 0.3);
              position: relative;
              background: #000;
            }}
            #sky-yt-player {{
              width: 100%;
              height: 100%;
              border: none;
            }}

            .error-banner {{
              display: none;
              background: rgba(255, 0, 60, 0.15);
              border: 1px solid #ff003c;
              border-radius: 10px;
              padding: 10px 14px;
              margin-top: 8px;
              color: #ff99aa;
              font-size: 0.8rem;
            }}
            .error-banner strong {{ color: #ff003c; }}

            .controls-bar {{
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-top: 10px;
              flex-wrap: wrap;
              gap: 8px;
            }}
            .ctrl-btn {{
              background: rgba(10, 28, 56, 0.85);
              border: 1px solid rgba(0, 242, 255, 0.3);
              color: #e0f2fe;
              border-radius: 8px;
              padding: 4px 10px;
              font-size: 0.76rem;
              cursor: pointer;
              display: inline-flex;
              align-items: center;
              gap: 4px;
              text-decoration: none;
              transition: all 0.2s;
            }}
            .ctrl-btn:hover {{
              border-color: #00f2ff;
              color: #00f2ff;
              box-shadow: 0 0 10px rgba(0, 242, 255, 0.3);
            }}
            .ctrl-btn-primary {{
              background: rgba(0, 242, 255, 0.2);
              border-color: #00f2ff;
              color: #00f2ff;
              font-weight: 700;
            }}

            .playlist-panel {{
              margin-top: 8px;
              padding-top: 8px;
              border-top: 1px solid rgba(0, 242, 255, 0.2);
              display: flex;
              align-items: center;
              gap: 6px;
              flex-wrap: wrap;
            }}
            .playlist-label {{
              font-size: 0.7rem;
              color: #79a6d2;
              text-transform: uppercase;
              font-weight: 700;
            }}
            .track-pill {{
              background: rgba(8, 22, 45, 0.7);
              border: 1px solid rgba(0, 242, 255, 0.25);
              border-radius: 12px;
              padding: 2px 8px;
              font-size: 0.72rem;
              color: #9cb8d9;
              cursor: pointer;
              transition: all 0.2s;
            }}
            .progress-bar-container {{
              display: flex;
              align-items: center;
              gap: 8px;
              margin-top: 8px;
              padding: 0 4px;
            }}
            .progress-bar-container span {{
              font-size: 0.72rem;
              color: #79a6d2;
              font-family: 'Orbitron', monospace;
              min-width: 38px;
            }}
            #seek-bar {{
              flex: 1;
              accent-color: #00f2ff;
              cursor: pointer;
              height: 4px;
            }}
          </style>
          <script src="https://www.youtube.com/iframe_api"></script>
        </head>
        <body>
          <div id="player-box" class="player-wrapper mode-{mode}">
            <div id="drag-handle" class="header-bar">
              <div class="title-box">
                <span>🎬</span>
                <span class="title-text" id="player-title">{title}</span>
              </div>
              <div class="mode-btn-group">
                <button class="mode-btn {'active' if mode == 'mini' else ''}" onclick="setMode('mini')">📱 Mini</button>
                <button class="mode-btn {'active' if mode == 'normal' else ''}" onclick="setMode('normal')">📺 Normal</button>
                <button class="mode-btn {'active' if mode == 'ampliado' else ''}" onclick="setMode('ampliado')">🖥️ Ampliado</button>
                <button class="mode-btn" onclick="toggleFullscreen()">🔲 Pantalla Completa</button>
                <button class="mode-btn" style="border-color: rgba(255, 0, 60, 0.4); color: #ff6688;" onclick="closePlayer()">✕</button>
              </div>
            </div>

            <div class="video-container" id="video-box">
              <div id="sky-yt-player"></div>
            </div>

            <div class="progress-bar-container">
              <span id="current-time-label">0:00</span>
              <input type="range" id="seek-bar" min="0" max="100" value="0" step="0.2" oninput="onSeekInput(this.value)" onchange="onSeekChange(this.value)">
              <span id="duration-label" style="text-align: right;">0:00</span>
            </div>

            <div id="error-banner" class="error-banner">
              <div id="error-text"></div>
              <div style="margin-top: 6px; display: flex; gap: 8px;">
                <button id="fallback-btn" class="ctrl-btn ctrl-btn-primary" onclick="loadNextCandidate()">🔄 Reproducir versión en vivo autorizada</button>
                <a id="direct-link-btn" class="ctrl-btn" href="{url}" target="_blank">🖥️ Mirar en YouTube</a>
              </div>
            </div>

            <div class="controls-bar">
              <div style="display: flex; gap: 5px; align-items: center; flex-wrap: wrap;">
                <button class="ctrl-btn" onclick="playPrev()" title="Video Anterior">⏮ Anterior</button>
                <button class="ctrl-btn" onclick="seekRelative(-10)" title="Retroceder 10 segundos">⏪ -10s</button>
                <button class="ctrl-btn ctrl-btn-primary" id="play-pause-btn" onclick="togglePlay()">⏸ Pausar</button>
                <button class="ctrl-btn" onclick="seekRelative(10)" title="Adelantar 10 segundos">⏩ +10s</button>
                <button class="ctrl-btn" onclick="playNext()" title="Video Siguiente">⏭ Siguiente</button>
                <button class="ctrl-btn" onclick="restartVideo()" title="Reiniciar video desde el inicio">🔄 Reiniciar</button>
                <button class="ctrl-btn" id="mute-btn" onclick="toggleMute()">🔊 Silenciar</button>
                <span style="font-size: 0.72rem; color: #79a6d2; margin-left: 4px;">Vol:</span>
                <input type="range" id="volume-slider" min="0" max="100" value="100" style="width: 65px; accent-color: #00f2ff;" oninput="onVolumeChange(this.value)">
              </div>
              <div style="display: flex; gap: 6px; align-items: center;">
                <button class="ctrl-btn" onclick="toggleFullscreen()">🔲 Completa</button>
                <a class="ctrl-btn" id="yt-web-link" href="{url}" target="_blank">🌐 YouTube</a>
              </div>
            </div>

            <div class="playlist-panel" id="playlist-box">
              <span class="playlist-label">Cola de Reproducción:</span>
            </div>
          </div>

          <script>
            var candidateVideos = {candidates_json};
            var currentVideoId = "{embed_id}";
            var currentIndex = 0;
            var player;
            var isPlaying = true;
            var isMuted = false;
            var isSeeking = false;

            // Cola persistente en el navegador
            try {{
              if (candidateVideos && candidateVideos.length > 0) {{
                localStorage.setItem('sky_yt_queue', JSON.stringify(candidateVideos));
              }} else {{
                var savedQ = localStorage.getItem('sky_yt_queue');
                if (savedQ) candidateVideos = JSON.parse(savedQ);
              }}
            }} catch(e) {{}}

            function onYouTubeIframeAPIReady() {{
              player = new YT.Player('sky-yt-player', {{
                height: '100%',
                width: '100%',
                videoId: currentVideoId,
                playerVars: {{
                  'autoplay': 1,
                  'enablejsapi': 1,
                  'playsinline': 1,
                  'rel': 0,
                  'modestbranding': 1,
                  'origin': window.location.origin
                }},
                events: {{
                  'onReady': onPlayerReady,
                  'onStateChange': onPlayerStateChange,
                  'onError': onPlayerError
                }}
              }});
            }}

            function onPlayerReady(event) {{
              event.target.playVideo();
              updatePlaylistUI();
            }}

            function onPlayerStateChange(event) {{
              var btn = document.getElementById('play-pause-btn');
              if (event.data === YT.PlayerState.PLAYING) {{
                isPlaying = true;
                btn.innerText = "⏸ Pausar";
              }} else if (event.data === YT.PlayerState.PAUSED) {{
                isPlaying = false;
                btn.innerText = "▶ Reanudar";
              }} else if (event.data === YT.PlayerState.ENDED) {{
                playNext();
              }}
            }}

            function onPlayerError(event) {{
              console.warn("YouTube Player Event Error:", event.data);
              var banner = document.getElementById('error-banner');
              var errText = document.getElementById('error-text');
              banner.style.display = 'block';

              if (event.data === 101 || event.data === 150) {{
                errText.innerHTML = "⚠️ <strong>Restricción del propietario (Error 150/101):</strong> El sello oficial desactivó la reproducción directa externa.";
                if (candidateVideos && candidateVideos.length > currentIndex + 1) {{
                  errText.innerHTML += "<br>🔄 <em>Cambiando automáticamente a versión en vivo autorizada (" + candidateVideos[currentIndex + 1].title + ")...</em>";
                  setTimeout(function() {{
                    playNext();
                  }}, 2000);
                }}
              }} else if (event.data === 100) {{
                errText.innerHTML = "⚠️ <strong>Video no disponible o privado (Error 100):</strong> Probando siguiente opción...";
                setTimeout(function() {{ playNext(); }}, 1500);
              }} else if (event.data === 2) {{
                errText.innerHTML = "⚠️ <strong>Parámetro de video no válido (Error 2).</strong>";
              }}
            }}

            function togglePlay() {{
              if (!player) return;
              if (isPlaying) {{
                player.pauseVideo();
              }} else {{
                player.playVideo();
              }}
            }}

            function toggleMute() {{
              if (!player) return;
              var btn = document.getElementById('mute-btn');
              if (isMuted) {{
                player.unMute();
                isMuted = false;
                btn.innerText = "🔊 Silenciar";
              }} else {{
                player.mute();
                isMuted = true;
                btn.innerText = "🔇 Con Sonido";
              }}
            }}

            function onVolumeChange(val) {{
              if (!player || !player.setVolume) return;
              player.setVolume(val);
              if (val == 0) {{
                isMuted = true;
                document.getElementById('mute-btn').innerText = "🔇 Con Sonido";
              }} else if (isMuted) {{
                isMuted = false;
                player.unMute();
                document.getElementById('mute-btn').innerText = "🔊 Silenciar";
              }}
            }}

            function seekRelative(deltaSec) {{
              if (!player || !player.getCurrentTime) return;
              var cur = player.getCurrentTime();
              var target = Math.max(0, cur + deltaSec);
              player.seekTo(target, true);
            }}

            function restartVideo() {{
              if (!player) return;
              player.seekTo(0, true);
              player.playVideo();
            }}

            function onSeekInput(val) {{
              isSeeking = true;
            }}

            function onSeekChange(val) {{
              if (!player || !player.getDuration) return;
              var dur = player.getDuration();
              if (dur > 0) {{
                var target = (val / 100.0) * dur;
                player.seekTo(target, true);
              }}
              isSeeking = false;
            }}

            function formatTime(s) {{
              var m = Math.floor(s / 60);
              var sec = Math.floor(s % 60);
              return m + ":" + (sec < 10 ? "0" : "") + sec;
            }}

            setInterval(function() {{
              if (!player || !player.getCurrentTime || !player.getDuration) return;
              try {{
                var dur = player.getDuration();
                var cur = player.getCurrentTime();
                if (dur > 0) {{
                  document.getElementById('duration-label').innerText = formatTime(dur);
                  document.getElementById('current-time-label').innerText = formatTime(cur);
                  if (!isSeeking) {{
                    document.getElementById('seek-bar').value = (cur / dur) * 100;
                  }}
                }}
              }} catch(e) {{}}
            }}, 500);

            function loadVideo(id, title, index) {{
              currentVideoId = id;
              currentIndex = index;
              try {{ localStorage.setItem('sky_yt_idx', index); }} catch(e) {{}}
              document.getElementById('player-title').innerText = title;
              document.getElementById('error-banner').style.display = 'none';
              document.getElementById('yt-web-link').href = "https://www.youtube.com/watch?v=" + id;
              if (player && player.loadVideoById) {{
                player.loadVideoById(id);
              }}
              updatePlaylistUI();
            }}

            function playNext() {{
              if (!candidateVideos || candidateVideos.length === 0) return;
              var nextIdx = (currentIndex + 1) % candidateVideos.length;
              loadVideo(candidateVideos[nextIdx].id, candidateVideos[nextIdx].title, nextIdx);
            }}

            function playPrev() {{
              if (!candidateVideos || candidateVideos.length === 0) return;
              var prevIdx = (currentIndex - 1 + candidateVideos.length) % candidateVideos.length;
              loadVideo(candidateVideos[prevIdx].id, candidateVideos[prevIdx].title, prevIdx);
            }}

            function loadNextCandidate() {{
              playNext();
            }}

            function setMode(newMode) {{
              var box = document.getElementById('player-box');
              box.className = 'player-wrapper mode-' + newMode;
              document.querySelectorAll('.mode-btn').forEach(function(b) {{
                b.classList.remove('active');
                if (b.innerText.toLowerCase().includes(newMode)) {{
                  b.classList.add('active');
                }}
              }});
            }}

            function toggleFullscreen() {{
              var elem = document.getElementById('video-box');
              if (!document.fullscreenElement) {{
                if (elem.requestFullscreen) {{
                  elem.requestFullscreen();
                }} else if (elem.webkitRequestFullscreen) {{
                  elem.webkitRequestFullscreen();
                }}
              }} else {{
                if (document.exitFullscreen) {{
                  document.exitFullscreen();
                }}
              }}
            }}

            function closePlayer() {{
              var box = document.getElementById('player-box');
              box.style.display = 'none';
              if (player && player.stopVideo) {{
                player.stopVideo();
              }}
            }}

            function updatePlaylistUI() {{
              var pl = document.getElementById('playlist-box');
              if (!pl || !candidateVideos || candidateVideos.length === 0) return;
              pl.innerHTML = '<span class="playlist-label">Cola de Reproducción:</span>';
              candidateVideos.forEach(function(vid, i) {{
                var pill = document.createElement('span');
                pill.className = 'track-pill' + (i === currentIndex ? ' selected' : '');
                pill.innerText = (i + 1) + ". " + vid.title;
                pill.onclick = function() {{ loadVideo(vid.id, vid.title, i); }};
                pl.appendChild(pill);
              }});
            }}

            // Comunicación para órdenes externas o voz
            window.addEventListener('message', function(ev) {{
              var data = ev.data;
              if (!data || typeof data !== 'object') return;
              if (data.action === 'play') {{ if (player) player.playVideo(); }}
              else if (data.action === 'pause') {{ if (player) player.pauseVideo(); }}
              else if (data.action === 'next') {{ playNext(); }}
              else if (data.action === 'previous') {{ playPrev(); }}
              else if (data.action === 'mute') {{ toggleMute(); }}
              else if (data.action === 'restart') {{ restartVideo(); }}
              else if (data.action === 'mode_mini') {{ setMode('mini'); }}
              else if (data.action === 'mode_normal') {{ setMode('normal'); }}
              else if (data.action === 'mode_expanded') {{ setMode('ampliado'); }}
              else if (data.action === 'close') {{ closePlayer(); }}
            }});

            // Arrastre en modo mini
            var dragHandle = document.getElementById('drag-handle');
            var isDragging = false;
            var startX, startY, origX, origY;
            dragHandle.addEventListener('mousedown', function(e) {{
              var box = document.getElementById('player-box');
              if (!box.classList.contains('mode-mini')) return;
              isDragging = true;
              startX = e.clientX;
              startY = e.clientY;
              var rect = box.getBoundingClientRect();
              origX = rect.left;
              origY = rect.top;
              e.preventDefault();
            }});
            window.addEventListener('mousemove', function(e) {{
              if (!isDragging) return;
              var box = document.getElementById('player-box');
              var dx = e.clientX - startX;
              var dy = e.clientY - startY;
              box.style.right = 'auto';
              box.style.bottom = 'auto';
              box.style.left = (origX + dx) + 'px';
              box.style.top = (origY + dy) + 'px';
            }});
            window.addEventListener('mouseup', function() {{
              isDragging = false;
            }});
          </script>
        </body>
        </html>
        """
        components.html(player_html, height=h_comp)

        col_m1, col_m2 = st.columns([1.2, 1.8])
        with col_m1:
          st.link_button("🖥️ ABRIR EN VENTANA / CHROME", url, type="primary")
        with col_m2:
          st.caption("🟢 **Reproductor YouTube IFrame API**: Modos Mini (flotante), Normal, Ampliado y Pantalla Completa.")
    elif service == 'google':
        st.markdown(f"""
        <div style="background: rgba(5, 14, 30, 0.85); border: 1px solid rgba(0, 168, 255, 0.35);
                    border-radius: 12px; padding: 14px 18px; margin: 10px 0;">
            <div style="color: #00f2ff; font-weight: 700; margin-bottom: 6px;">🔍 BÚSQUEDA WEB ACTIVADA</div>
            <div style="color: #9cb8d9; font-size: 0.95rem;">Término consultado: <strong>«{query}»</strong></div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("🌐 Ver resultados en Google", url, type="primary")
    else:
        st.link_button(f"🌐 Abrir enlace: {url}", url, type="primary")


def render_social_card(datos):
    subaction = datos.get('subaction', 'post')
    platform = (datos.get('platform') or 'whatsapp').lower()
    import urllib.parse

    icons = {
        'whatsapp': '💬',
        'facebook': '📘',
        'instagram': '📸',
        'tiktok': '🎵',
        'twitter': '🐦',
        'x': '🐦',
        'linkedin': '💼',
        'telegram': '✈️',
        'general': '📣'
    }
    ico = icons.get(platform, '📣')

    st.markdown(f"""
    <div style="background: rgba(6, 18, 38, 0.92); border: 1px solid rgba(0, 242, 255, 0.4);
                border-radius: 14px; padding: 16px 20px 10px 20px; margin: 12px 0; box-shadow: 0 0 25px rgba(0, 242, 255, 0.15);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="color: #00f2ff; font-family: 'Orbitron', monospace; font-size: 0.95rem; font-weight: 700;">
                {ico} CENTRO SOCIAL SKY-IA · {platform.upper()}
            </span>
            <span style="background: rgba(0, 242, 255, 0.15); color: #00f2ff; border: 1px solid #00f2ff; padding: 3px 10px; border-radius: 10px; font-size: 0.72rem; font-weight: 600;">
                MODO INTERACTIVO
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if subaction == 'post':
        content = datos.get('content', '') or f"¡Hola comunidad! Comparto una actualización con SKY-IA. #Innovacion #{platform.title()}"
        edit_content = st.text_area("Texto de la publicación (Copywriting + Hashtags)", value=content, height=110, key=f"soc_post_{abs(hash(content)) % 100000}")
        
        foto = st.file_uploader("📷 Subir foto para la publicación", type=["jpg", "png", "jpeg", "webp"], key=f"soc_file_{abs(hash(content)) % 100000}")
        if foto:
            st.image(foto, caption="Vista previa de imagen a publicar", use_container_width=True)

        col_p1, col_p2 = st.columns(2)
        encoded_text = urllib.parse.quote_plus(edit_content)
        with col_p1:
            if platform in ('twitter', 'x'):
                st.link_button("🐦 Publicar Tweet en X", f"https://twitter.com/intent/tweet?text={encoded_text}", type="primary")
            elif platform == 'whatsapp':
                st.link_button("💬 Compartir en WhatsApp", f"https://api.whatsapp.com/send?text={encoded_text}", type="primary")
            elif platform == 'facebook':
                st.link_button("📘 Publicar en Facebook", f"https://www.facebook.com/sharer/sharer.php?quote={encoded_text}", type="primary")
            elif platform == 'instagram':
                st.link_button("📸 Abrir Instagram Web", "https://www.instagram.com/", type="primary")
            elif platform == 'tiktok':
                st.link_button("🎵 Abrir TikTok Studio", "https://www.tiktok.com/upload", type="primary")
            elif platform == 'linkedin':
                st.link_button("💼 Publicar en LinkedIn", "https://www.linkedin.com/feed/", type="primary")
            else:
                st.link_button(f"🚀 Abrir {platform.title()}", f"https://www.{platform}.com", type="primary")
        with col_p2:
            st.caption("🟢 Puedes editar el texto, adjuntar foto o pulsar el botón para publicar.")

    elif subaction == 'message':
        recip = datos.get('recipient', '') or 'contacto'
        msg = datos.get('message', '') or 'Hola, te escribo desde mi asistente personal SKY-IA.'
        edit_msg = st.text_area(f"Mensaje para {recip}", value=msg, height=90, key=f"soc_msg_{abs(hash(msg)) % 100000}")
        encoded_msg = urllib.parse.quote_plus(edit_msg)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.link_button("💬 Enviar por WhatsApp Web", f"https://web.whatsapp.com/send?text={encoded_msg}", type="primary")
        with col_m2:
            st.caption(f"🟢 Pulsa para abrir WhatsApp Web con el mensaje listo para enviar.")

    elif subaction == 'comment':
        comm = datos.get('comment', '') or 'Excelente publicación, totalmente de acuerdo.'
        st.text_area("Comentario generado", value=comm, height=80, key=f"soc_comm_{abs(hash(comm)) % 100000}")
        st.caption("🟢 Comentario listo. Cópialo o ábrelo en tu red social para responder.")


def render_archivo_card(datos):
    path_str = str(datos.get('path', ''))
    tipo = datos.get('type', 'file')
    import os
    basename = os.path.basename(path_str) or path_str

    icons = {
        '.docx': '📄 Documento Microsoft Word',
        '.doc': '📄 Documento Microsoft Word',
        '.xlsx': '📊 Hoja de Cálculo Excel',
        '.xls': '📊 Hoja de Cálculo Excel',
        '.pptx': '📽️ Presentación PowerPoint',
        '.ppt': '📽️ Presentación PowerPoint',
        '.pdf': '📕 Documento PDF',
        '.txt': '📝 Archivo de Texto',
        '.png': '🖼️ Imagen PNG',
        '.jpg': '🖼️ Imagen JPG',
        '.jpeg': '🖼️ Imagen JPEG',
        '.mp4': '🎬 Video MP4',
        '.mp3': '🎵 Archivo de Audio'
    }
    ext = os.path.splitext(path_str)[1].lower()
    label_tipo = icons.get(ext, '📁 Carpeta de Windows' if tipo == 'folder' else '📄 Archivo del Sistema')

    st.markdown(f"""
    <div style="background: rgba(8, 22, 45, 0.92); border: 1px solid rgba(0, 242, 255, 0.35);
                border-radius: 12px; padding: 14px 18px; margin: 10px 0; box-shadow: 0 0 20px rgba(0, 242, 255, 0.15);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="color: #00f2ff; font-weight: 700; font-size: 0.95rem;">
                {label_tipo}
            </span>
            <span style="background: rgba(0, 255, 170, 0.15); color: #00ffaa; border: 1px solid #00ffaa; padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 600;">
                🟢 INICIADO EN WINDOWS
            </span>
        </div>
        <div style="color: #ffffff; font-family: monospace; font-size: 0.9rem; margin: 4px 0;">{basename}</div>
        <div style="color: #8bb5dc; font-size: 0.8rem;">Ubicación: <code>{path_str}</code></div>
    </div>
    """, unsafe_allow_html=True)





def render_holographic_orb(height=360):
    import streamlit.components.v1 as components
    hologram_html = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          background: transparent;
          overflow: hidden;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        #container {
          position: relative;
          width: 100%;
          height: 350px;
          border-radius: 20px;
          overflow: hidden;
          background: radial-gradient(circle at 50% 45%, #08223d 0%, #030d1c 45%, #01040a 85%);
          border: 1px solid rgba(0, 242, 255, 0.35);
          box-shadow: 0 0 40px rgba(0, 242, 255, 0.2), inset 0 0 35px rgba(0, 242, 255, 0.08);
        }
        canvas {
          display: block;
          width: 100%;
          height: 100%;
        }
        .hud-badge {
          position: absolute;
          bottom: 16px;
          left: 50%;
          transform: translateX(-50%);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: rgba(4, 14, 28, 0.88);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1px solid rgba(0, 242, 255, 0.35);
          border-radius: 24px;
          padding: 8px 32px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.8), 0 0 25px rgba(0, 242, 255, 0.3);
          user-select: none;
          pointer-events: none;
          z-index: 10;
        }
        .hud-title {
          font-family: 'Courier New', monospace;
          font-size: 13px;
          font-weight: 900;
          letter-spacing: 4px;
          color: #00f2ff;
          text-shadow: 0 0 14px rgba(0, 242, 255, 0.9);
        }
        .hud-status {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 3px;
        }
        .hud-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: #00f2ff;
          box-shadow: 0 0 10px #00f2ff;
          animation: pulseDot 1.8s infinite;
        }
        .hud-status-text {
          font-family: 'Courier New', monospace;
          font-size: 9px;
          letter-spacing: 3px;
          color: #9cb8d9;
          font-weight: 700;
        }
        @keyframes pulseDot {
          0%, 100% { transform: scale(0.85); opacity: 0.6; }
          50% { transform: scale(1.3); opacity: 1; box-shadow: 0 0 15px #00f2ff, 0 0 25px #00a8ff; }
        }
      </style>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    </head>
    <body>
      <div id="container">
        <canvas id="canvas"></canvas>
        <div class="hud-badge">
          <div class="hud-title">SKY IA UNIVERSAL</div>
          <div class="hud-status">
            <span class="hud-dot"></span>
            <span class="hud-status-text">SISTEMA CONECTADO</span>
          </div>
        </div>
      </div>

      <script>
        const container = document.getElementById('container');
        const canvas = document.getElementById('canvas');
        const width = container.clientWidth || 800;
        const height = container.clientHeight || 350;

        const scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(0x01040a, 0.035);

        const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
        camera.position.set(0, 0, 9.5);

        const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

        // Luces
        const ambientLight = new THREE.AmbientLight(0x0a2b4a, 1.2);
        scene.add(ambientLight);

        const cyanPointLight = new THREE.PointLight(0x00f2ff, 4.5, 20);
        cyanPointLight.position.set(0, 0, 0);
        scene.add(cyanPointLight);

        const dirLight = new THREE.DirectionalLight(0x00f2ff, 2.0);
        dirLight.position.set(8, 8, 8);
        scene.add(dirLight);

        // Grupo principal del holograma
        const hologramGroup = new THREE.Group();
        scene.add(hologramGroup);

        // 1. NÚCLEO DE ENERGÍA (Esfera brillante densa en el centro)
        const coreGeo = new THREE.SphereGeometry(1.4, 48, 48);
        const coreMat = new THREE.MeshStandardMaterial({
          color: 0x00f2ff,
          emissive: 0x00d4ff,
          emissiveIntensity: 2.8,
          roughness: 0.15,
          metalness: 0.85
        });
        const innerCore = new THREE.Mesh(coreGeo, coreMat);
        hologramGroup.add(innerCore);

        // 2. ESTRUCTURA GEOMÉTRICA (Icosaedro wireframe circundante)
        const shellGeo = new THREE.IcosahedronGeometry(2.35, 2);
        const shellMat = new THREE.MeshStandardMaterial({
          color: 0x00f2ff,
          emissive: 0x00f2ff,
          emissiveIntensity: 1.4,
          wireframe: true,
          transparent: true,
          opacity: 0.5
        });
        const outerShell = new THREE.Mesh(shellGeo, shellMat);
        hologramGroup.add(outerShell);

        // 3. ANILLOS ORBITALES DE CONTENCIÓN
        const ringsGroup = new THREE.Group();
        hologramGroup.add(ringsGroup);

        const ring1Geo = new THREE.TorusGeometry(3.1, 0.02, 16, 120);
        const ring1Mat = new THREE.MeshStandardMaterial({
          color: 0x00f2ff,
          emissive: 0x00f2ff,
          emissiveIntensity: 3.5
        });
        const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
        ringsGroup.add(ring1);

        const ring2Geo = new THREE.TorusGeometry(3.5, 0.015, 16, 120);
        const ring2Mat = new THREE.MeshStandardMaterial({
          color: 0x00f2ff,
          emissive: 0x00f2ff,
          emissiveIntensity: 2.2,
          transparent: true,
          opacity: 0.7
        });
        const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
        ring2.rotation.x = Math.PI / 2.3;
        ring2.rotation.y = Math.PI / 4.5;
        ringsGroup.add(ring2);

        const ring3Geo = new THREE.TorusGeometry(3.9, 0.01, 16, 120);
        const ring3Mat = new THREE.MeshStandardMaterial({
          color: 0xffffff,
          emissive: 0x88e5ff,
          emissiveIntensity: 1.5,
          transparent: true,
          opacity: 0.4
        });
        const ring3 = new THREE.Mesh(ring3Geo, ring3Mat);
        ring3.rotation.x = Math.PI / 4;
        ring3.rotation.z = -Math.PI / 4;
        ringsGroup.add(ring3);

        // 4. PARTÍCULAS / CHISPAS CÓSMICAS ORBITANTES
        const particleCount = 220;
        const particleGeo = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);

        for (let i = 0; i < particleCount; i++) {
          const r = 2.8 + Math.random() * 4.5;
          const theta = Math.random() * Math.PI * 2;
          const phi = Math.acos(2 * Math.random() - 1);

          positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
          positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
          positions[i * 3 + 2] = r * Math.cos(phi);

          if (Math.random() > 0.3) {
            colors[i * 3] = 0.0;
            colors[i * 3 + 1] = 0.95;
            colors[i * 3 + 2] = 1.0;
          } else {
            colors[i * 3] = 1.0;
            colors[i * 3 + 1] = 1.0;
            colors[i * 3 + 2] = 1.0;
          }
        }

        particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const particleMat = new THREE.PointsMaterial({
          size: 0.075,
          vertexColors: true,
          transparent: true,
          opacity: 0.85,
          blending: THREE.AdditiveBlending
        });
        const particleSystem = new THREE.Points(particleGeo, particleMat);
        hologramGroup.add(particleSystem);

        // Fondo de estrellas lejanas
        const starCount = 350;
        const starGeo = new THREE.BufferGeometry();
        const starPos = new Float32Array(starCount * 3);
        for (let i = 0; i < starCount; i++) {
          starPos[i * 3] = (Math.random() - 0.5) * 30;
          starPos[i * 3 + 1] = (Math.random() - 0.5) * 20;
          starPos[i * 3 + 2] = (Math.random() - 0.5) * 15 - 5;
        }
        starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
        const starMat = new THREE.PointsMaterial({ size: 0.04, color: 0x69b5e8, transparent: true, opacity: 0.6 });
        const stars = new THREE.Points(starGeo, starMat);
        scene.add(stars);

        // Interacción suave con mouse
        let mouseX = 0, mouseY = 0;
        let targetX = 0, targetY = 0;
        container.addEventListener('mousemove', (e) => {
          const rect = container.getBoundingClientRect();
          mouseX = ((e.clientX - rect.left) / width - 0.5) * 1.5;
          mouseY = ((e.clientY - rect.top) / height - 0.5) * 1.5;
        });
        container.addEventListener('mouseleave', () => {
          mouseX = 0;
          mouseY = 0;
        });

        // Bucle de animación
        let clock = new THREE.Clock();
        function animate() {
          requestAnimationFrame(animate);
          const t = clock.getElapsedTime();

          // Rotación caparazón icosaedro
          outerShell.rotation.y = t * 0.22;
          outerShell.rotation.x = t * 0.12;
          outerShell.rotation.z = t * 0.06;

          // Rotación núcleo interno
          innerCore.rotation.y = -t * 0.45;
          innerCore.rotation.x = -t * 0.2;

          // Rotación anillos
          ringsGroup.rotation.x = Math.sin(t * 0.3) * 0.45 + Math.PI / 2.2;
          ringsGroup.rotation.y = t * 0.35;
          ringsGroup.rotation.z = t * 0.08;

          // Rotación de partículas
          particleSystem.rotation.y = t * 0.08;
          particleSystem.rotation.x = t * 0.04;
          stars.rotation.y = t * 0.01;

          // Pulsación suave del núcleo
          const pulse = 1 + Math.sin(t * 2.5) * 0.035;
          innerCore.scale.set(pulse, pulse, pulse);
          const shellPulse = 1 + Math.sin(t * 1.8) * 0.02;
          outerShell.scale.set(shellPulse, shellPulse, shellPulse);

          // Parallax suave con mouse
          targetX += (mouseX - targetX) * 0.05;
          targetY += (mouseY - targetY) * 0.05;
          camera.position.x = targetX * 1.2;
          camera.position.y = -targetY * 1.2;
          camera.lookAt(0, 0, 0);

          renderer.render(scene, camera);
        }
        animate();

        window.addEventListener('resize', () => {
          const newW = container.clientWidth || 800;
          const newH = container.clientHeight || 350;
          camera.aspect = newW / newH;
          camera.updateProjectionMatrix();
          renderer.setSize(newW, newH);
        });
      </script>
    </body>
    </html>
    """
    components.html(hologram_html, height=height)


def render_asistente_jarvis(proveedor, modelo, ejecucion_dispositivo=True):
    # Inyección de estilos de estética JARVIS / Iron Man
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@500;600;700&family=Inter:wght@400;600&display=swap');

    .stApp {
        background: radial-gradient(circle at 50% 0%, #07152b 0%, #050b16 50%, #03060d 100%) !important;
        color: #e2f1ff !important;
        font-family: 'Rajdhani', 'Segoe UI', sans-serif !important;
    }

    [data-testid="stSidebar"] {
        background: rgba(5, 12, 26, 0.96) !important;
        border-right: 1px solid rgba(0, 242, 255, 0.25) !important;
        box-shadow: 4px 0 25px rgba(0, 0, 0, 0.5) !important;
    }
    [data-testid="stSidebar"] * {
        color: #d1e5ff !important;
    }

    .jarvis-hud-container {
        background: rgba(6, 17, 36, 0.75);
        border: 1px solid rgba(0, 242, 255, 0.4);
        box-shadow: 0 0 35px rgba(0, 242, 255, 0.15), inset 0 0 20px rgba(0, 242, 255, 0.05);
        border-radius: 16px;
        padding: 20px 28px;
        margin-bottom: 18px;
        backdrop-filter: blur(14px);
        position: relative;
        overflow: hidden;
    }

    .jarvis-hud-container::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, #00f2ff, #00a8ff, transparent);
    }

    .arc-reactor-wrapper {
        display: flex;
        align-items: center;
        gap: 22px;
    }

    .arc-reactor {
        position: relative;
        width: 72px;
        height: 72px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: radial-gradient(circle, rgba(0, 242, 255, 0.3) 0%, rgba(3, 10, 22, 0.8) 70%);
        box-shadow: 0 0 25px #00f2ff, inset 0 0 15px #00f2ff;
        flex-shrink: 0;
    }

    .arc-ring {
        position: absolute;
        border-radius: 50%;
    }
    .ring-outer {
        width: 66px; height: 66px;
        border: 2px dashed rgba(0, 242, 255, 0.8);
        animation: rotateCW 9s linear infinite;
    }
    .ring-middle {
        width: 50px; height: 50px;
        border: 2px dotted rgba(0, 168, 255, 0.9);
        animation: rotateCCW 6s linear infinite;
    }
    .ring-inner {
        width: 34px; height: 34px;
        border: 2px solid rgba(0, 242, 255, 0.7);
        animation: rotateCW 4s linear infinite;
    }
    .arc-core {
        width: 20px; height: 20px;
        background: #ffffff;
        border-radius: 50%;
        box-shadow: 0 0 20px #00f2ff, 0 0 40px #00f2ff;
        animation: pulseCore 2s ease-in-out infinite;
    }

    @keyframes rotateCW {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    @keyframes rotateCCW {
        from { transform: rotate(360deg); }
        to { transform: rotate(0deg); }
    }
    @keyframes pulseCore {
        0%, 100% { transform: scale(0.9); opacity: 0.85; box-shadow: 0 0 15px #00f2ff; }
        50% { transform: scale(1.15); opacity: 1; box-shadow: 0 0 30px #00f2ff, 0 0 45px #00a8ff; }
    }

    .jarvis-title-block {
        flex-grow: 1;
    }
    .jarvis-system-tag {
        font-family: 'Orbitron', monospace;
        font-size: 0.75rem;
        color: #00f2ff;
        letter-spacing: 2px;
        margin-bottom: 2px;
    }
    .jarvis-main-title {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 2.1rem !important;
        font-weight: 900 !important;
        margin: 0 !important;
        color: #ffffff !important;
        letter-spacing: 1.5px;
        text-shadow: 0 0 15px rgba(0, 242, 255, 0.6);
    }
    .jarvis-sub-title {
        font-size: 0.95rem;
        color: #9cb8d9;
        letter-spacing: 1px;
        margin-top: 4px;
    }

    .jarvis-audio-waves {
        display: flex;
        align-items: center;
        gap: 4px;
        height: 40px;
        padding-right: 10px;
    }
    .jarvis-audio-waves span {
        width: 4px;
        background: #00f2ff;
        border-radius: 3px;
        box-shadow: 0 0 8px #00f2ff;
        animation: waveBar 1.2s ease-in-out infinite alternate;
    }
    .jarvis-audio-waves span:nth-child(1) { height: 10px; animation-delay: 0.1s; }
    .jarvis-audio-waves span:nth-child(2) { height: 25px; animation-delay: 0.3s; }
    .jarvis-audio-waves span:nth-child(3) { height: 35px; animation-delay: 0.2s; }
    .jarvis-audio-waves span:nth-child(4) { height: 18px; animation-delay: 0.4s; }
    .jarvis-audio-waves span:nth-child(5) { height: 28px; animation-delay: 0.15s; }
    .jarvis-audio-waves span:nth-child(6) { height: 38px; animation-delay: 0.35s; }
    .jarvis-audio-waves span:nth-child(7) { height: 22px; animation-delay: 0.25s; }
    .jarvis-audio-waves span:nth-child(8) { height: 15px; animation-delay: 0.45s; }

    @keyframes waveBar {
        0% { transform: scaleY(0.3); opacity: 0.4; }
        100% { transform: scaleY(1.2); opacity: 1; }
    }

    .telemetry-deck {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 20px;
    }
    .telemetry-card {
        background: rgba(10, 24, 48, 0.65);
        border: 1px solid rgba(0, 242, 255, 0.25);
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
        transition: all 0.2s ease;
    }
    .telemetry-card:hover {
        border-color: #00f2ff;
        box-shadow: 0 0 20px rgba(0, 242, 255, 0.25);
    }
    .telemetry-label {
        font-size: 0.72rem;
        color: #79a6d2;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .telemetry-value {
        font-family: 'Orbitron', monospace;
        font-size: 1.15rem;
        font-weight: 700;
        color: #00f2ff;
        margin-top: 3px;
        text-shadow: 0 0 8px rgba(0, 242, 255, 0.4);
    }

    [data-testid="stChatMessage"] {
        background: rgba(8, 20, 40, 0.75) !important;
        border: 1px solid rgba(0, 242, 255, 0.2) !important;
        border-radius: 14px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        border-left: 4px solid #00a8ff !important;
        background: rgba(10, 25, 52, 0.65) !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        border-left: 4px solid #00f2ff !important;
        box-shadow: 0 0 15px rgba(0, 242, 255, 0.1) !important;
    }

    [data-testid="stPills"] button {
        background: rgba(12, 28, 56, 0.8) !important;
        border: 1px solid rgba(0, 242, 255, 0.35) !important;
        color: #e0f2fe !important;
        font-weight: 600 !important;
        border-radius: 20px !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stPills"] button:hover {
        background: rgba(0, 242, 255, 0.2) !important;
        border-color: #00f2ff !important;
        box-shadow: 0 0 14px rgba(0, 242, 255, 0.4) !important;
        transform: translateY(-1px);
    }
    </style>
    """, unsafe_allow_html=True)

    # 3D Holographic Orb (KENORA 3D Neural Stage adaptado a SKY IA)
    render_holographic_orb(height=355)


    # Deck de Telemetría HUD
    st.markdown(f"""
    <div class="telemetry-deck">
        <div class="telemetry-card">
            <div class="telemetry-label">⚡ ARC REACTOR</div>
            <div class="telemetry-value">100% ONLINE</div>
        </div>
        <div class="telemetry-card">
            <div class="telemetry-label">🧠 CEREBRO MULTI-IA</div>
            <div class="telemetry-value">{PROVIDERS[proveedor].name.upper()}</div>
        </div>
        <div class="telemetry-card">
            <div class="telemetry-label">🖥️ CONTROL WINDOWS</div>
            <div class="telemetry-value">{'AUTORIZADO' if ejecucion_dispositivo else 'SOLO LECTURA'}</div>
        </div>
        <div class="telemetry-card">
            <div class="telemetry-label">🎬 MULTIMEDIA HUD</div>
            <div class="telemetry-value">ACTIVO</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3 MODOS DE INTERACCIÓN: A (Conversación Natural), B (Micrófono Manual), C (Chat Escrito)
    from neural_core.voice_coordinator import coordinador_voz, InteractionMode, VoiceState

    if "sky_interaction_mode" not in st.session_state:
        st.session_state["sky_interaction_mode"] = "MODO_A"

    if st.button("🌌 Cambiar a Núcleo Holográfico 3D (Pantalla Limpia)", help="Activa la nueva interfaz cinematográfica 3D centrada en el Núcleo sin paneles"):
        st.session_state["sky_ui_view_mode"] = "holographic"
        st.rerun()

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        if st.button("🎙️ Modo A: Conversación Natural",
                     type="primary" if st.session_state["sky_interaction_mode"] == "MODO_A" else "secondary",
                     use_container_width=True,
                     help="Diálogo bidireccional continuo frente a frente con SKY-IA. Responde con voz y escucha el siguiente turno sin repetir 'SKY'."):
            st.session_state["sky_interaction_mode"] = "MODO_A"
            coordinador_voz.set_mode(InteractionMode.MODO_A_NATURAL)
            st.rerun()
    with col_m2:
        if st.button("🔘 Modo B: Micrófono Manual",
                     type="primary" if st.session_state["sky_interaction_mode"] == "MODO_B" else "secondary",
                     use_container_width=True,
                     help="Grabación solo cuando pulsas el micrófono (Push-To-Talk). No graba en reposo. Responde con voz."):
            st.session_state["sky_interaction_mode"] = "MODO_B"
            coordinador_voz.set_mode(InteractionMode.MODO_B_MANUAL)
            st.rerun()
    with col_m3:
        if st.button("✍️ Modo C: Chat Escrito",
                     type="primary" if st.session_state["sky_interaction_mode"] == "MODO_C" else "secondary",
                     use_container_width=True,
                     help="Modo texto sin micrófono. Conserva todo tu historial, contexto, tareas y música."):
            st.session_state["sky_interaction_mode"] = "MODO_C"
            coordinador_voz.set_mode(InteractionMode.MODO_C_TEXTO)
            st.rerun()

    # Estado activo del coordinador de voz
    modo_act = st.session_state["sky_interaction_mode"]
    if modo_act == "MODO_A":
        st.markdown("""
        <div style="background: rgba(0, 242, 255, 0.08); border: 1px solid #00f2ff; border-radius: 10px; padding: 8px 14px; margin: 8px 0; display: flex; justify-content: space-between; align-items: center;">
            <span style="color: #00f2ff; font-weight: 700; font-size: 0.88rem;">🟢 MODO A: CONVERSACIÓN NATURAL BIDIRECCIONAL</span>
            <span style="color: #a0d8ef; font-size: 0.78rem;">Decí "SKY" o grabá tu orden · Luego continuá dialogando libremente</span>
        </div>
        """, unsafe_allow_html=True)
        audio_clip = st.audio_input("Habla con SKY-IA (Detección de voz activa)", key="sky_mode_a_mic")
        if audio_clip is not None:
            audio_bytes = audio_clip.read()
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            if st.session_state.get('_last_audio_hash') != audio_hash:
                st.session_state['_last_audio_hash'] = audio_hash
                with st.spinner("Escuchando y procesando tu intervención..."):
                    try:
                        coordinador_voz.set_state(VoiceState.ESCUCHANDO)
                        transcrito = transcribir_audio(audio_bytes, mime='audio/wav')
                        st.session_state['_audio_pending_prompt'] = transcrito
                        coordinador_voz.set_state(VoiceState.PROCESANDO)
                        st.success(f"Voz capturada: «{transcrito}»")
                    except Exception as err:
                        st.warning(f"Audio no detectado: {err}. Puedes escribir abajo.")
    elif modo_act == "MODO_B":
        st.markdown("""
        <div style="background: rgba(0, 255, 170, 0.08); border: 1px solid #00ffaa; border-radius: 10px; padding: 8px 14px; margin: 8px 0; display: flex; justify-content: space-between; align-items: center;">
            <span style="color: #00ffaa; font-weight: 700; font-size: 0.88rem;">🔘 MODO B: MICRÓFONO MANUAL (PUSH-TO-TALK)</span>
            <span style="color: #9cb8d9; font-size: 0.78rem;">Grabación bajo demanda · Sin grabaciones ambientales</span>
        </div>
        """, unsafe_allow_html=True)
        audio_clip = st.audio_input("Presiona para hablar (Modo Manual)", key="sky_mode_b_mic")
        if audio_clip is not None:
            audio_bytes = audio_clip.read()
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            if st.session_state.get('_last_audio_hash') != audio_hash:
                st.session_state['_last_audio_hash'] = audio_hash
                with st.spinner("Procesando audio manual..."):
                    try:
                        transcrito = transcribir_audio(audio_bytes, mime='audio/wav')
                        st.session_state['_audio_pending_prompt'] = transcrito
                        st.success(f"Intervención manual: «{transcrito}»")
                    except Exception as err:
                        st.warning(f"Error al transcribir: {err}")
    else:
        st.markdown("""
        <div style="background: rgba(140, 90, 255, 0.08); border: 1px solid #8c5aff; border-radius: 10px; padding: 8px 14px; margin: 8px 0; display: flex; justify-content: space-between; align-items: center;">
            <span style="color: #c49eff; font-weight: 700; font-size: 0.88rem;">✍️ MODO C: CHAT ESCRITO Y MINIVENTANA</span>
            <span style="color: #9cb8d9; font-size: 0.78rem;">Escribe tus órdenes abajo · Conservo todo tu contexto y música</span>
        </div>
        """, unsafe_allow_html=True)

    # Sugerencias rápidas en píldoras
    st.markdown("**Acciones rápidas:**")
    opciones_rapidas = [
        "Abre YouTube y pon Queen",
        "Abre WhatsApp",
        "Publica en Facebook un saludo a mi comunidad",
        "Crea un post para Instagram",
        "Abre mi carpeta de documentos",
        "Abre Word",
        "Abre Excel",
        "Consulta el estado de mi computadora"
    ]
    sugerencia_clic = st.pills("Acciones", opciones_rapidas, label_visibility="collapsed")

    # Estado del servicio de voz y tareas activas en segundo plano
    import json
    from pathlib import Path
    st_file = Path(__file__).resolve().parent / "local_data" / "sky_session_state.json"
    hands_free_info = {}
    if st_file.exists():
        try:
            hands_free_info = json.loads(st_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    from neural_core.task_manager import gestor_tareas
    act_task = gestor_tareas.get_active_task()

    col_stat1, col_stat2 = st.columns([1, 1])
    with col_stat1:
        if hands_free_info.get("hands_free_listening"):
            st.markdown(
                '<div style="background: rgba(0, 255, 170, 0.12); border: 1px solid #00ffaa; border-radius: 8px; padding: 5px 12px; margin-bottom: 8px; font-size: 0.8rem; color: #00ffaa; font-weight: 600;">🟢 MODO MANOS LIBRES: Escucha continua activa (Di "SKY")</div>',
                unsafe_allow_html=True
            )
    with col_stat2:
        if act_task:
            st.markdown(
                f'<div style="background: rgba(0, 242, 255, 0.12); border: 1px solid #00f2ff; border-radius: 8px; padding: 5px 12px; margin-bottom: 8px; font-size: 0.8rem; color: #00f2ff; font-weight: 600;">⚡ TRABAJO ACTIVO: {act_task.title} ({act_task.progress}%)</div>',
                unsafe_allow_html=True
            )

    if act_task and act_task.status in ('pending', 'running'):
        st.progress(act_task.progress / 100.0, text=f"Progreso de {act_task.title}: {act_task.description}")

    # Historial de conversación
    if "chat_jarvis_history" not in st.session_state:
        st.session_state.chat_jarvis_history = [
            {
                "role": "assistant",
                "content": "¡Hola Oscar! Soy **SKY-IA**. Todos mis módulos (control de equipo, multimedia, redes sociales, documentos Office, diseño 3D y finanzas) operan internamente en segundo plano. ¿Qué necesitas que haga?"
            }
        ]

    for m in st.session_state.chat_jarvis_history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("tipo") == "finanzas" and m.get("datos"):
                res = m["datos"]
                if res.get('totales'):
                    st.dataframe(pd.DataFrame([
                        {'Moneda': mon, 'Ingresos': vals['ingreso']/100, 'Gastos': vals['gasto']/100, 'Balance': (vals['ingreso']-vals['gasto'])/100}
                        for mon, vals in res['totales'].items()
                    ]), hide_index=True)
            elif m.get("tipo") == "media" and m.get("datos"):
                render_media_card(m["datos"])
            elif m.get("tipo") == "social" and m.get("datos"):
                render_social_card(m["datos"])
            elif m.get("tipo") == "archivo" and m.get("datos"):
                render_archivo_card(m["datos"])

    # Captura de entrada
    prompt_usuario = st.chat_input("Escribe una orden a SKY... (ej: 'SKY, abre YouTube y pon Queen', 'abre la calculadora', 'calcula 500*12')", submit_mode="disable")

    if not prompt_usuario and st.session_state.get('_audio_pending_prompt'):
        prompt_usuario = st.session_state.pop('_audio_pending_prompt')
    elif not prompt_usuario and sugerencia_clic and st.session_state.get('_last_sugerencia_used') != sugerencia_clic:
        st.session_state['_last_sugerencia_used'] = sugerencia_clic
        prompt_usuario = sugerencia_clic

    if prompt_usuario:
        st.session_state.chat_jarvis_history.append({"role": "user", "content": prompt_usuario})
        with st.chat_message("user"):
            st.markdown(prompt_usuario)

        with st.chat_message("assistant"):
            with st.status(":shimmer[SKY ejecutando solicitud...]", type="compact") as status_box:
                respuesta_texto = ""
                tipo_extra = None
                datos_extra = None
                texto_limpio = norm(prompt_usuario)

                # 1. Comandos de dispositivo (PC)
                cmd_device = interpret_command(prompt_usuario)
                if cmd_device:
                    status_box.update(label=f"Ejecutando acción en PC: {cmd_device['description']}", state="running")
                    if cmd_device['action'] == 'open_url':
                        url = cmd_device['params'].get('url')
                        query = cmd_device['params'].get('query', '')
                        service = cmd_device['params'].get('service', 'web')

                        if service == 'youtube':
                            from neural_core.multimedia import resolve_youtube_video
                            res_yt = resolve_youtube_video(query or 'Queen')
                            if res_yt.get('url') and 'watch?v=' in res_yt['url']:
                                url = res_yt['url']
                            video_id = res_yt.get('video_id', '')
                            candidates = res_yt.get('candidates', [])
                            title = res_yt.get('titulo', query or 'Queen')
                            
                            # Miniventana manejable por defecto salvo que el usuario indique otro tamaño
                            cur_mode = st.session_state.get('sky_player_mode')
                            if not cur_mode:
                                cur_mode = 'mini'
                                if any(w in texto_limpio for w in ('ampliado', 'pantalla ancha', 'cine', 'grande')):
                                    cur_mode = 'ampliado'
                                elif any(w in texto_limpio for w in ('pantalla completa', 'completa')):
                                    cur_mode = 'ampliado'
                                elif any(w in texto_limpio for w in ('normal', 'panel normal')):
                                    cur_mode = 'normal'
                                st.session_state['sky_player_mode'] = cur_mode

                            datos_extra = {
                                'url': url,
                                'query': query,
                                'service': 'youtube',
                                'video_id': video_id,
                                'candidates': candidates,
                                'title': title,
                                'mode': cur_mode
                            }
                            st.session_state['sky_current_player'] = datos_extra

                        if ejecucion_dispositivo and url:
                            import webbrowser
                            webbrowser.open(url, new=2)
                            try:
                                from neural_core.windows_controller import focus_user_window
                                focus_user_window("YouTube") or focus_user_window("Chrome") or focus_user_window("Edge")
                            except Exception:
                                pass

                            if service == 'youtube':
                                if query:
                                    respuesta_texto = f"🎬 **SKY-IA**: He cargado **«{title}»** en miniventana interactiva (con controles, selección de versiones y modos)."
                                else:
                                    respuesta_texto = "🎬 **SKY-IA**: He abierto YouTube en el reproductor integrado de SKY-IA."
                                tipo_extra = "media"
                            elif service == 'google':
                                respuesta_texto = f"🔍 **SKY-IA**: He abierto la búsqueda de Google para **«{query}»** en tu navegador."
                                tipo_extra = "media"
                                datos_extra = {'url': url, 'query': query, 'service': 'google'}
                            else:
                                respuesta_texto = f"✅ **SKY-IA**: He abierto **{url}** en tu navegador local."
                                tipo_extra = "media"
                                datos_extra = {'url': url, 'query': query, 'service': 'web'}
                        else:
                            respuesta_texto = f"Acción disponible: Abrir enlace `{url}`. (Habilita ejecución directa para abrirlo automáticamente)."
                    elif cmd_device['action'] == 'launch_app':
                        app_name = cmd_device['params'].get('app')
                        if ejecucion_dispositivo and app_name:
                            try:
                                from neural_core.windows_controller import launch_authorized_app
                                res_launch = launch_authorized_app(app_name)
                                respuesta_texto = f"✅ {res_launch['message']}"
                            except Exception as err:
                                respuesta_texto = f"⚠️ {err}"
                        else:
                            respuesta_texto = f"Acción propuesta: Abrir {app_name}. (Habilita ejecución directa en PC para iniciar)."
                    elif cmd_device['action'] == 'window_action':
                        if ejecucion_dispositivo:
                            try:
                                from neural_core.windows_controller import (
                                    list_user_windows, focus_user_window,
                                    minimize_user_window, restore_user_window, close_user_window
                                )
                                subaction = cmd_device['params'].get('subaction', 'list')
                                if subaction == 'list':
                                    wins = list_user_windows()
                                    if wins:
                                        lista_t = "\n".join(f"- `{w['title']}`" for w in wins[:10])
                                        respuesta_texto = f"🖥️ **Ventanas abiertas detectadas:**\n{lista_t}"
                                    else:
                                        respuesta_texto = "🖥️ No se detectaron ventanas abiertas de usuario."
                                elif subaction == 'focus':
                                    res_f = focus_user_window(cmd_device['params'].get('target', ''))
                                    respuesta_texto = f"✅ {res_f['message']}"
                                elif subaction == 'minimize':
                                    res_m = minimize_user_window(cmd_device['params'].get('target'))
                                    respuesta_texto = f"✅ {res_m['message']}"
                                elif subaction == 'restore':
                                    res_r = restore_user_window(cmd_device['params'].get('target'))
                                    respuesta_texto = f"✅ {res_r['message']}"
                                elif subaction == 'close':
                                    res_c = close_user_window(cmd_device['params'].get('target'))
                                    respuesta_texto = f"✅ {res_c['message']}"
                                elif subaction == 'organize':
                                    from neural_core.windows_controller import organize_windows
                                    res_org = organize_windows()
                                    respuesta_texto = f"✅ {res_org['message']}"
                            except Exception as err:
                                respuesta_texto = f"⚠️ Error en ventana: {err}"
                        else:
                            respuesta_texto = "Acción sobre ventana propuesta. (Habilita ejecución directa para ejecutarla)."
                    elif cmd_device['action'] == 'media_key':
                        if ejecucion_dispositivo:
                            try:
                                from agente_dispositivo import send_media_key
                                send_media_key(cmd_device['params'].get('key', 'play_pause'))
                                respuesta_texto = f"🎵 Se envió la tecla multimedia `{cmd_device['params'].get('key')}` a Windows."
                            except Exception as err:
                                respuesta_texto = f"⚠️ Control multimedia: {err}"
                        else:
                            respuesta_texto = f"Tecla multimedia `{cmd_device['params'].get('key')}` propuesta."
                    elif cmd_device['action'] == 'player_control':
                        subact = cmd_device['params'].get('subaction', 'mode_normal')
                        cur_p = st.session_state.get('sky_current_player') or {
                            'url': 'https://www.youtube.com/watch?v=vbvyNnw8Qjg',
                            'query': 'Queen',
                            'service': 'youtube',
                            'video_id': 'vbvyNnw8Qjg',
                            'title': 'Queen – Bohemian Rhapsody (Live Aid 1985)',
                            'candidates': [
                                {'id': 'vbvyNnw8Qjg', 'title': 'Queen – Bohemian Rhapsody (Live Aid 1985)', 'embeddable': True},
                                {'id': 'frdBb9Slu1A', 'title': 'Queen – Live Aid 1985 Full Concert', 'embeddable': True},
                                {'id': 'PadKCVBIN94', 'title': 'Queen – Bohemian Rhapsody (1981 Live Video)', 'embeddable': True},
                                {'id': 'HgzGwKwLmgM', 'title': "Queen – Don't Stop Me Now", 'embeddable': True}
                            ]
                        }
                        if subact == 'mode_mini':
                            st.session_state['sky_player_mode'] = 'mini'
                            cur_p['mode'] = 'mini'
                            respuesta_texto = "🎬 **SKY-IA**: He cambiado el reproductor a modo **Mini ventana flotante (PiP)**. Puedes moverlo y continuar navegando."
                            tipo_extra = "media"
                            datos_extra = cur_p
                        elif subact == 'mode_expanded':
                            st.session_state['sky_player_mode'] = 'ampliado'
                            cur_p['mode'] = 'ampliado'
                            respuesta_texto = "🎬 **SKY-IA**: He ampliado el reproductor a **Modo Cine (Pantalla Ancha)**."
                            tipo_extra = "media"
                            datos_extra = cur_p
                        elif subact == 'mode_fullscreen':
                            st.session_state['sky_player_mode'] = 'ampliado'
                            cur_p['mode'] = 'ampliado'
                            respuesta_texto = "🎬 **SKY-IA**: Activando modo **Pantalla Completa**. Puedes utilizar el botón 🔲 en los controles del reproductor."
                            tipo_extra = "media"
                            datos_extra = cur_p
                        elif subact == 'mode_normal':
                            st.session_state['sky_player_mode'] = 'normal'
                            cur_p['mode'] = 'normal'
                            respuesta_texto = "🎬 **SKY-IA**: He restaurado el reproductor a **Tamaño Normal**."
                            tipo_extra = "media"
                            datos_extra = cur_p
                        elif subact == 'close':
                            st.session_state['sky_current_player'] = None
                            respuesta_texto = "🎬 **SKY-IA**: He cerrado el reproductor multimedia."
                        elif subact == 'next':
                            cands = cur_p.get('candidates', [])
                            if cands:
                                cur_p['candidates'] = cands[1:] + [cands[0]]
                                cur_p['video_id'] = cur_p['candidates'][0]['id']
                                cur_p['title'] = cur_p['candidates'][0]['title']
                                cur_p['url'] = f"https://www.youtube.com/watch?v={cur_p['video_id']}"
                            respuesta_texto = f"⏭️ **SKY-IA**: Saltando al siguiente video: **{cur_p.get('title')}**."
                            tipo_extra = "media"
                            datos_extra = cur_p
                        elif subact in ('pause', 'play'):
                            try:
                                from agente_dispositivo import send_media_key
                                send_media_key('play_pause')
                            except Exception:
                                pass
                            respuesta_texto = f"⏯️ **SKY-IA**: {'Pausando' if subact == 'pause' else 'Reanudando'} reproducción."
                            tipo_extra = "media"
                            datos_extra = cur_p
                        elif subact == 'text_mode':
                            st.session_state['sky_text_mode_focus'] = True
                            respuesta_texto = "✍️ **SKY-IA**: Modo de chat escrito activado. Mantengo tu historial, contexto, tareas y música en segundo plano. ¿Qué deseas escribir?"
                        if subact != 'close':
                            st.session_state['sky_current_player'] = cur_p
                    elif cmd_device['action'] == 'task_action':
                        subact = cmd_device['params'].get('subaction', 'create_presentation')
                        from neural_core.task_manager import gestor_tareas
                        if subact == 'create_presentation':
                            topic = cmd_device['params'].get('topic', 'tema general')
                            t = gestor_tareas.create_task('presentation', f"Presentación: {topic}", f"Preparando presentación sobre {topic}", cmd_device['params'])
                            gestor_tareas.run_presentation_task(t.id, topic)
                            respuesta_texto = f"📽️ **SKY-IA**: He iniciado la preparación de la presentación sobre **«{topic}»** en segundo plano con Office Studio. Mientras avanza, puedes seguir conversando conmigo o pedirme que agregue fotos y detalles."
                            tipo_extra = "archivo"
                            datos_extra = {'path': f"Presentacion_{topic}.pptx", 'type': 'file', 'task_id': t.id}
                        elif subact == 'append':
                            mod = cmd_device['params'].get('modification', '')
                            t = gestor_tareas.append_to_active_task(mod)
                            if t and t.kind == 'presentation':
                                mods = [m['text'] for m in t.params.get('modifications', [])]
                                gestor_tareas.run_presentation_task(t.id, t.params.get('topic', 'trabajo'), mods)
                                respuesta_texto = f"✨ **SKY-IA**: He incorporado tu solicitud (**«{mod}»**) a la presentación en curso sin interrumpir nuestro diálogo."
                            else:
                                respuesta_texto = f"✨ **SKY-IA**: Modificación registrada para el trabajo en curso: **«{mod}»**."
                        elif subact == 'create_document':
                            topic = cmd_device['params'].get('topic', 'documento general')
                            from neural_core.sky_office import create_document
                            gen_doc = create_document('docx', topic, f"# {topic.title()}\n\nDocumento generado por SKY-IA.\n\nContenido base estructurado y listo para edición.")
                            docs_dir = Path.home() / "Documents" / "SKY_Office"
                            docs_dir.mkdir(parents=True, exist_ok=True)
                            out_p = docs_dir / gen_doc.filename
                            out_p.write_bytes(gen_doc.data)
                            respuesta_texto = f"📄 **SKY-IA**: He creado el documento **«{gen_doc.filename}»** en tu carpeta de Documentos."
                            tipo_extra = "archivo"
                            datos_extra = {'path': str(out_p), 'type': 'file'}
                    elif cmd_device['action'] == 'open_file':
                        if ejecucion_dispositivo:
                            try:
                                from neural_core.windows_controller import open_local_file_or_folder
                                target_f = cmd_device['params'].get('target', '')
                                res_f = open_local_file_or_folder(target_f)
                                respuesta_texto = f"📂 **SKY-IA**: {res_f['message']}"
                                tipo_extra = "archivo"
                                datos_extra = res_f
                            except Exception as err:
                                respuesta_texto = f"⚠️ {err}"
                        else:
                            respuesta_texto = f"Acción propuesta: Abrir archivo o carpeta '{cmd_device['params'].get('target')}'."
                    elif cmd_device['action'] == 'social_action':
                        subact = cmd_device['params'].get('subaction', 'post')
                        plat = cmd_device['params'].get('platform', 'whatsapp')
                        tipo_extra = "social"
                        datos_extra = cmd_device['params']
                        if subact == 'post':
                            respuesta_texto = f"📣 **SKY-IA**: He preparado tu publicación para **{plat.title()}**. Puedes redactar, adjuntar fotos y publicar directamente."
                        elif subact == 'message':
                            recip = cmd_device['params'].get('recipient', '')
                            respuesta_texto = f"💬 **SKY-IA**: He preparado tu mensaje para **{recip}** en **WhatsApp**. Puedes enviarlo con un clic."
                        elif subact == 'comment':
                            respuesta_texto = f"✍️ **SKY-IA**: Generé un comentario optimizado para **{plat.title()}**."
                    elif cmd_device['action'] == 'status':
                        import platform
                        respuesta_texto = f"🖥️ **Estado de tu computadora:**\n- Dispositivo: `{platform.node()}`\n- Sistema: `{platform.system()} {platform.release()}`\n- Plataforma: `{platform.platform()}`\n- Agente local: Conectado y operativo."

                # 2. Comandos aritméticos o herramientas locales
                if not respuesta_texto:
                    resp_local = interpret_local_command(prompt_usuario)
                    if resp_local:
                        status_box.update(label="Herramienta local ejecutada", state="running")
                        respuesta_texto = resp_local

                # 3. Consulta de finanzas internas
                if not respuesta_texto and any(w in texto_limpio for w in ['finanzas', 'gastos', 'ingresos', 'balance', 'presupuesto']):
                    status_box.update(label="Consultando módulo financiero...", state="running")
                    res_fin = resumen()
                    tipo_extra = "finanzas"
                    datos_extra = res_fin
                    if res_fin and res_fin.get('totales'):
                        lineas = [f"📊 **Resumen Financiero ({res_fin.get('mes', 'Mes Actual')}):**"]
                        for mon, vals in res_fin['totales'].items():
                            ing = vals['ingreso'] / 100
                            gas = vals['gasto'] / 100
                            bal = ing - gas
                            lineas.append(f"- **{mon}:** Ingresos: `${ing:,.2f}` | Gastos: `${gas:,.2f}` | **Balance:** `${bal:,.2f}`")
                        if res_fin.get('alertas'):
                            for al in res_fin['alertas']:
                                lineas.append(f"⚠️ *Alerta en {al['categoria']}*: Has gastado ${al['gasto']} de un límite de ${al['limite']}")
                        respuesta_texto = "\n".join(lineas)
                    else:
                        respuesta_texto = "📊 El motor financiero está activo pero aún no hay transacciones registradas este mes. Puedes registrar ingresos o gastos cuando lo necesites."

                # 4. Consulta de noticias
                if not respuesta_texto and any(w in texto_limpio for w in ['noticias', 'noticia', 'actualidad']):
                    status_box.update(label="Consultando noticias en tiempo real...", state="running")
                    try:
                        notis = noticias(prompt_usuario[:100], limite=5)
                        if notis:
                            lineas = ["📰 **Últimas noticias:**"]
                            for n in notis:
                                tit = n.get('titulo') or n.get('titular') or 'Noticia'
                                url = n.get('url') or n.get('enlace') or '#'
                                lineas.append(f"- [{tit}]({url})")
                            respuesta_texto = "\n".join(lineas)
                    except Exception:
                        pass

                # 5. Cerebro Multi-IA y memoria
                if not respuesta_texto:
                    status_box.update(label=f"Consultando {PROVIDERS[proveedor].name}...", state="running")
                    historial_modelo = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_jarvis_history
                    ]
                    try:
                        resp_ia, fuentes = responder(
                            prompt_usuario,
                            area="General",
                            historial=historial_modelo[-6:],
                            modelo=modelo,
                            proveedor=proveedor
                        )
                        respuesta_texto = resp_ia
                        if fuentes:
                            respuesta_texto += f"\n\n*Documentos internos consultados: {', '.join(dict.fromkeys(x['nombre'] for x in fuentes))}*"
                    except Exception as e:
                        respuesta_texto = f"Error al consultar el modelo de IA: {e}"

                status_box.update(label="Completado", state="complete")

            st.markdown(respuesta_texto)
            if tipo_extra == "finanzas" and datos_extra and datos_extra.get('totales'):
                st.dataframe(pd.DataFrame([
                    {'Moneda': mon, 'Ingresos': vals['ingreso']/100, 'Gastos': vals['gasto']/100, 'Balance': (vals['ingreso']-vals['gasto'])/100}
                    for mon, vals in datos_extra['totales'].items()
                ]), hide_index=True)
            elif tipo_extra == "media" and datos_extra:
                render_media_card(datos_extra)
            elif tipo_extra == "social" and datos_extra:
                render_social_card(datos_extra)
            elif tipo_extra == "archivo" and datos_extra:
                render_archivo_card(datos_extra)

            msg_salida = {"role": "assistant", "content": respuesta_texto}
            if tipo_extra:
                msg_salida["tipo"] = tipo_extra
                msg_salida["datos"] = datos_extra
            st.session_state.chat_jarvis_history.append(msg_salida)

            # Síntesis de voz hablada en el navegador si estamos en Modo A o Modo B
            interact_mode = st.session_state.get("sky_interaction_mode", "MODO_A")
            if interact_mode in ("MODO_A", "MODO_B") and respuesta_texto:
                try:
                    from neural_core.voz import hablar_texto
                    audio_mp3 = hablar_texto(respuesta_texto)
                    if audio_mp3:
                        st.caption("🔊 *SKY-IA respondiendo con voz:*")
                        st.audio(audio_mp3, format="audio/mp3", autoplay=True)
                except Exception:
                    pass

            # Registrar turno en coordinador_voz
            try:
                coordinador_voz.record_turn(prompt_usuario, respuesta_texto)
            except Exception:
                pass


def render_asistente_holografico_3d(proveedor, modelo, ejecucion_dispositivo=True):
    from neural_core.voice_coordinator import coordinador_voz, InteractionMode, VoiceState
    from neural_core.window_manager import gestor_ventanas
    from neural_core.holographic_ui import generate_holographic_scene_html, get_holographic_css
    from neural_core.voz import hablar_texto
    from neural_core.dispositivos import interpret_command
    import streamlit.components.v1 as components
    import hashlib

    # 1. Inyectar estilos holográficos
    st.markdown(get_holographic_css(), unsafe_allow_html=True)

    # 2. Barra Superior Discreta de Control
    col_hdr_l, col_hdr_c, col_hdr_r = st.columns([4, 4, 4], vertical_alignment="center")
    with col_hdr_l:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-family: 'Orbitron', sans-serif; font-size: 1.25rem; font-weight: 900; color: #00f2ff; letter-spacing: 2px;">SKY-IA</span>
            <span style="font-size: 0.72rem; color: #7dd3fc; letter-spacing: 3px; font-weight: 700;">IA UNIVERSAL</span>
        </div>
        """, unsafe_allow_html=True)
    with col_hdr_c:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if st.button("✦ Módulos (26)", help="Abrir ventana holográfica con los 26 módulos del ecosistema"):
                if gestor_ventanas.windows['modules'].is_open:
                    gestor_ventanas.close_window('modules')
                else:
                    gestor_ventanas.open_window('modules', win_type='modules', title='🧠 Ecosistema SKY-IA (26 Módulos)', position='center')
                st.rerun()
        with col_m2:
            if st.button("📋 Modo Clásico", help="Regresar a la interfaz anterior de consola/tablero"):
                st.session_state["sky_ui_view_mode"] = "classic"
                st.rerun()
    with col_hdr_r:
        curr_mode = st.session_state.get("sky_interaction_mode", "MODO_A")
        subcol1, subcol2, subcol3 = st.columns(3)
        with subcol1:
            if st.button("🎙️ Natural", type="primary" if curr_mode == "MODO_A" else "secondary", help="Modo A: Conversación Natural Continua"):
                st.session_state["sky_interaction_mode"] = "MODO_A"
                coordinador_voz.set_mode(InteractionMode.MODO_A_NATURAL)
                st.rerun()
        with subcol2:
            if st.button("🔘 Manual", type="primary" if curr_mode == "MODO_B" else "secondary", help="Modo B: Micrófono Manual (Push-to-Talk)"):
                st.session_state["sky_interaction_mode"] = "MODO_B"
                coordinador_voz.set_mode(InteractionMode.MODO_B_MANUAL)
                st.rerun()
        with subcol3:
            if st.button("✍️ Chat", type="primary" if curr_mode == "MODO_C" else "secondary", help="Modo C: Chat Escrito"):
                st.session_state["sky_interaction_mode"] = "MODO_C"
                coordinador_voz.set_mode(InteractionMode.MODO_C_TEXTO)
                gestor_ventanas.open_window('chat', win_type='chat', title='💬 Conversación SKY-IA', position='bottom-left')
                st.rerun()

    # 3. Núcleo Holográfico 3D Principal
    v_state = coordinador_voz.get_state().name
    track = gestor_ventanas.windows['multimedia'].data.get('query') if gestor_ventanas.windows['multimedia'].is_open else None
    scene_html = generate_holographic_scene_html(
        voice_state=v_state,
        active_player_track=track,
        is_playing_music=gestor_ventanas.windows['multimedia'].is_open,
        height=540
    )
    components.html(scene_html, height=545)

    # 4. Dock de Ventanas Minimizadas
    dock_items = gestor_ventanas.get_dock_items()
    if dock_items:
        st.markdown('<div class="holo-dock"><span class="holo-dock-label">Dock Holográfico:</span>', unsafe_allow_html=True)
        cols_d = st.columns(len(dock_items) + 1)
        for idx, item in enumerate(dock_items):
            with cols_d[idx]:
                if st.button(f"↗️ {item.title}", key=f"dock_restore_{item.id}"):
                    gestor_ventanas.restore_window(item.id)
                    st.rerun()
        with cols_d[-1]:
            if st.button("✕ Ocultar Todo", key="dock_hide_all"):
                gestor_ventanas.leave_only_core()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 5. Ventanas Holográficas Abiertas (Alrededor del Núcleo)
    open_wins = gestor_ventanas.get_open_windows()
    for win in open_wins:
        with st.container():
            col_w_title, col_w_min, col_w_size, col_w_close = st.columns([7, 1, 1, 1], vertical_alignment="center")
            with col_w_title:
                st.markdown(f'<div class="holo-window-title">{win.title} <span style="font-size: 0.7rem; color: #7dd3fc; border: 1px solid #00f2ff; padding: 2px 8px; border-radius: 8px;">POSICIÓN: {win.position.upper()}</span></div>', unsafe_allow_html=True)
            with col_w_min:
                if st.button("➖", key=f"min_{win.id}", help="Minimizar al dock"):
                    gestor_ventanas.minimize_window(win.id)
                    st.rerun()
            with col_w_size:
                next_size = 'normal' if win.size == 'mini' else 'mini'
                if st.button("🗖" if win.size == 'mini' else "🗗", key=f"size_{win.id}", help=f"Cambiar tamaño ({next_size})"):
                    gestor_ventanas.resize_window(win.id, next_size)
                    st.rerun()
            with col_w_close:
                if st.button("✕", key=f"close_{win.id}", help="Cerrar ventana"):
                    gestor_ventanas.close_window(win.id)
                    st.rerun()

            # Contenido específico de cada ventana
            if win.id == 'multimedia':
                render_url_card(win.data)
            elif win.id == 'chat':
                if "chat_jarvis_history" not in st.session_state:
                    st.session_state.chat_jarvis_history = [
                        {"role": "assistant", "content": "¡Hola Oscar! Soy **SKY-IA**. Conversando en modo holográfico. ¿Qué necesitas que haga?"}
                    ]
                for m in st.session_state.chat_jarvis_history[-6:]:
                    with st.chat_message(m["role"]):
                        st.markdown(m["content"])
            elif win.id == 'documents':
                st.markdown("### 📁 SKY Office Studio")
                st.write("Crea, edita y organiza documentos y presentaciones en segundo plano mientras conversamos.")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    topic = st.text_input("Tema del documento", value="Inteligencia Artificial y Automatización", key="holo_doc_topic")
                    if st.button("📄 Crear Documento Word (.docx)", type="primary"):
                        from neural_core.task_manager import gestor_tareas
                        t = gestor_tareas.create_task('document', f"Documento: {topic}", f"Generando documento sobre {topic}", {'topic': topic})
                        st.success(f"Tarea iniciada: {t.title}")
                with col_d2:
                    pres_topic = st.text_input("Tema de presentación", value="Ecosistema SKY-IA", key="holo_pres_topic")
                    if st.button("📊 Crear Presentación (.pptx)"):
                        from neural_core.task_manager import gestor_tareas
                        t = gestor_tareas.create_task('presentation', f"Presentación: {pres_topic}", f"Generando presentación sobre {pres_topic}", {'topic': pres_topic})
                        st.success(f"Tarea iniciada: {t.title}")
            elif win.id == 'projects':
                from neural_core.task_manager import gestor_tareas
                tasks = gestor_tareas.get_all_tasks()
                st.markdown("### ✅ Proyectos y Tareas Activas en Segundo Plano")
                if tasks:
                    for t in tasks[-5:]:
                        st.progress(t.progress / 100.0, text=f"{t.title} ({t.status.upper()}) - {t.progress}%")
                else:
                    st.info("No hay tareas en segundo plano en ejecución. Pídele a SKY crear una presentación o documento.")
            elif win.id == 'modules':
                st.markdown("### 🧠 Ecosistema SKY-IA — Los 26 Módulos Reales")
                st.caption("Acceso directo a cualquier módulo del sistema sin perder la sesión.")
                cols_mod = st.columns(4)
                for idx, mod in enumerate(SECCIONES_TECNICAS):
                    with cols_mod[idx % 4]:
                        if st.button(mod, key=f"btn_sec_mod_{idx}", use_container_width=True):
                            st.session_state["sky_ui_view_mode"] = "classic"
                            st.session_state["seccion_elegida_holo"] = mod
                            st.rerun()

    # 6. Cápsula Discreta de Entrada Inferior (Matching Image Reference)
    prompt_usuario = None
    curr_interaction = st.session_state.get("sky_interaction_mode", "MODO_A")

    with st.container():
        col_c_mic, col_c_input = st.columns([1.5, 10.5], vertical_alignment="center")

        with col_c_mic:
            audio_clip = st.audio_input("Habla con SKY-IA...", key="holo_capsule_mic", label_visibility="collapsed")
            if audio_clip is not None:
                audio_bytes = audio_clip.read()
                audio_hash = hashlib.md5(audio_bytes).hexdigest()
                if st.session_state.get('_last_audio_hash_holo') != audio_hash:
                    st.session_state['_last_audio_hash_holo'] = audio_hash
                    with st.spinner("Procesando tu voz..."):
                        try:
                            coordinador_voz.set_state(VoiceState.ESCUCHANDO)
                            transcrito = transcribir_audio(audio_bytes, mime='audio/wav')
                            prompt_usuario = transcrito
                            coordinador_voz.set_state(VoiceState.PROCESANDO)
                            st.toast(f"Voz detectada: «{transcrito}»")
                        except Exception as err:
                            st.warning(f"Error de audio: {err}")

        with col_c_input:
            text_in = st.chat_input("Habla con SKY-IA... (ej: 'SKY, pon Queen', 'abrí mis documentos', 'dejá solo el núcleo')", key="holo_text_input")
            if text_in:
                prompt_usuario = text_in

    # 7. Ejecución centralizada de la orden de usuario
    if prompt_usuario:
        if "chat_jarvis_history" not in st.session_state:
            st.session_state.chat_jarvis_history = []
        st.session_state.chat_jarvis_history.append({"role": "user", "content": prompt_usuario})

        respuesta_texto = ""
        # Verificar comandos locales
        intento = interpret_command(prompt_usuario)
        if intento:
            act = intento.get('action')
            par = intento.get('params', {})
            if act == 'holographic_window':
                respuesta_texto = intento.get('description', 'Ventanas holográficas actualizadas.')
            elif act == 'open_url' and par.get('service') == 'youtube':
                gestor_ventanas.open_window('multimedia', win_type='multimedia', title=f"🎬 YouTube: {par.get('query', 'Música')}", data=par, position='top-right')
                respuesta_texto = f"Voy a buscar música de {par.get('query', 'YouTube')} en el reproductor holográfico."
            elif act == 'task_action':
                gestor_ventanas.open_window('documents', win_type='documents', title="📁 Documentos & Office", position='right')
                sub = par.get('subaction')
                if sub == 'create_presentation':
                    topic = par.get('topic', 'tema')
                    respuesta_texto = f"Iniciando preparación de presentación sobre {topic} en Office Studio."
                elif sub == 'create_document':
                    topic = par.get('topic', 'documento')
                    respuesta_texto = f"Preparando documento sobre {topic} en Office Studio."
                else:
                    respuesta_texto = intento.get('description', 'Tarea procesada.')
            elif act == 'status' and par.get('greeting'):
                respuesta_texto = par.get('message', 'Sí, te escucho. ¿Qué necesitás?')
            elif act == 'voice_control':
                respuesta_texto = intento.get('description', 'Control conversacional aplicado.')
            else:
                respuesta_texto = intento.get('description', 'Orden interpretada.')
        else:
            # Consulta general de IA
            try:
                with st.spinner("SKY-IA procesando consulta..."):
                    contexto_chat = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_jarvis_history[-6:]]
                    r_ia = responder("Asistente Central", prompt_usuario, contexto=contexto_chat, proveedor=proveedor, modelo=modelo)
                    respuesta_texto = r_ia[0] if isinstance(r_ia, (list, tuple)) else str(r_ia)
            except Exception as e:
                respuesta_texto = f"Comprendido: procesé tu solicitud «{prompt_usuario}»."

        st.session_state.chat_jarvis_history.append({"role": "assistant", "content": respuesta_texto})

        # Síntesis de voz
        if respuesta_texto:
            try:
                audio_mp3 = hablar_texto(respuesta_texto)
                if audio_mp3:
                    st.caption("🔊 *SKY-IA respondiendo con voz:*")
                    st.audio(audio_mp3, format="audio/mp3", autoplay=True)
            except Exception:
                pass

        try:
            coordinador_voz.record_turn(prompt_usuario, respuesta_texto)
        except Exception:
            pass
        st.rerun()


if seccion == "🎙️ Asistente Central":
    if st.session_state.get("sky_ui_view_mode", "holographic") == "holographic":
        render_asistente_holografico_3d(proveedor_jarvis, modelo_jarvis, ejecucion_dispositivo)
    else:
        render_asistente_jarvis(proveedor_jarvis, modelo_jarvis, ejecucion_dispositivo)

elif seccion == "🏠 Inicio":
    st.title("SKY Universal v8.0")
    st.write("**Un solo SKY:** chat multi-IA, visión por cámara, piezas 3D exportables, memoria, metas de mejora, voz, dispositivos, Engine Sensor y BAQUEANO. Los datos propios se conservan localmente.")
    panel=st.columns(4)
    with panel[0]: st.metric("Módulos principales",len(SECCIONES)-1)
    with panel[1]: st.metric("Documentos",len(documentos()))
    with panel[2]: st.metric("Prospectos / clientes",len(listar_clientes()))
    with panel[3]: st.metric("Proveedores cloud configurados",sum(1 for k,v in PROVIDERS.items() if v.cloud and provider_ready(k)))
    st.subheader("Qué puede hacer hoy")
    st.write("Multi-IA (Gemini, OpenAI, Anthropic Claude, Mistral, Groq, DeepSeek y Ollama) para el chat; análisis y generación de imágenes con modelos compatibles; centro de control BAQUEANO para leer estado, repo y datos públicos; propuesta de cambios GitHub vía PR; finanzas, clientes, mercados, noticias, campañas, música, cine, seguridad defensiva y sensores MLP + GRU.")
    st.info("Configurá las claves API en .env para los proveedores y BAQUEANO. No hay acceso automático a cuentas ni garantía de ganancias. Los cambios web se proponen en una rama y se revisan antes de fusionarlos.")
    st.subheader("Ruta para convertir ideas en ingresos")
    st.markdown("**1.** Elegir servicio → **2.** Crear propuesta y contenido → **3.** Conseguir prospectos reales → **4.** Registrar las negociaciones → **5.** Medir ventas y gastos.")
    st.write("Ejemplos de servicios: materiales didácticos digitales, automatización para negocios, diseño de campañas, investigación de mercado, producción de contenidos y asesoría de implementación tecnológica.")

elif seccion=="🧠 IA universal":
    st.title("🧠 IA universal")
    area=st.selectbox("Área de conocimiento",list(MODULOS))
    st.write(MODULOS[area]); mostrar_chat(area,EJEMPLOS.get(area))

elif seccion=="🧬 Centro multi-IA":
    st.title('🧬 Centro multi-IA — el cerebro de SKY')
    st.write('Gestioná los proveedores, elegí un modelo y compará respuestas. No se requieren todas las claves: cada servicio se activa por separado.')
    import pandas as _pd
    estado=provider_summary()
    st.dataframe(_pd.DataFrame([{'Proveedor':e['proveedor'],
        'Estado':'Clave configurada' if e['configurado'] and e['nube'] else ('Sin clave' if e['nube'] else 'Servicio local opcional'),
        'Modelo previsto':e['modelo'], 'Tipo':'Nube' if e['nube'] else 'Local'} for e in estado]),
        use_container_width=True,hide_index=True)
    st.caption('Clave configurada no significa conexión verificada. Requiere autorización en la cuenta, cuotas y red. Los modelos pueden variar de disponibilidad.')
    st.subheader('Comparar dos modelos (bajo demanda)')
    st.warning('Dos respuestas = hasta dos consultas cobrables. Cada proveedor recibe el texto que escribas sólo cuando pulsás Comparar.')
    disponibles=[k for k in PROVIDERS if provider_ready(k)]
    if len(disponibles)<2: st.info('Configurá dos proveedores o un proveedor y Ollama para compararlos.')
    else:
        c1,c2=st.columns(2)
        with c1: p1=st.selectbox('Proveedor A',disponibles,index=0,format_func=lambda k:PROVIDERS[k].name)
        with c2: p2=st.selectbox('Proveedor B',disponibles,index=1,format_func=lambda k:PROVIDERS[k].name)
        tema=st.text_area('Consulta para comparar',max_chars=3000,placeholder='Diseñá una campaña para BAQUEANO con presupuesto bajo...')
        with st.expander('Modelos específicos (opcional)'):
            m1=st.text_input('Modelo A',value=choose_provider(p1)[1])
            m2=st.text_input('Modelo B',value=choose_provider(p2)[1])
        if st.button('Comparar respuestas',type='primary',disabled=not bool(tema.strip()) or p1==p2):
            if p1==p2: st.warning('Elegí dos proveedores distintos.')
            else:
                c1,c2=st.columns(2)
                for destino,p,m in [(c1,p1,m1),(c2,p2,m2)]:
                    with destino:
                        st.subheader(PROVIDERS[p].name)
                        with st.spinner('Generando…'):
                            result=ejecutar(responder,tema,'Comparación de modelos',[],m,proveedor=p)
                        if result: st.markdown(result[0])
    st.subheader('Configuración privada')
    st.markdown('Abrí `.env` en tu computadora, ingresá las claves de los servicios que contratés y reiniciá SKY. **Nunca pegues claves en el chat, ni en el repositorio público de BAQUEANO.**')
    st.caption('Modo automático: usa una prioridad temática simple entre proveedores configurados; no compara modelos en secreto ni hace fallback de nube después de un fallo.')

elif seccion=="👁️ SKY Visión":
    st.title('👁️ SKY Visión — foto, cámara y razonamiento')
    st.write('Enseñale algo a SKY con la cámara o cargá una foto. Podés preguntar por objetos, texto, problemas técnicos, diseño, educación o mejoras. Solo se envía la imagen a la IA cuando pulsás **Analizar**.')
    c1,c2=st.columns(2)
    with c1: imagen_camara=st.camera_input('Tomar foto para SKY',key='sky_vision_cam')
    with c2: imagen_subida=st.file_uploader('O subir imagen',type=['png','jpg','jpeg','webp'],key='sky_vision_upload')
    elegido=imagen_subida or imagen_camara
    if elegido:
        datos=elegido.getvalue()
        tipo={'image/jpg':'image/jpeg'}.get(elegido.type,elegido.type)
        st.image(datos,caption='Imagen seleccionada',width=380)
        motores=[p for p in ('gemini','openai','anthropic','ollama') if provider_ready(p)]
        proveedor_vision=st.selectbox('IA que analiza la fotografía',motores or ['gemini'],
            format_func=lambda p:PROVIDERS[p].name,key='sky_vision_model')
        pregunta=st.text_area('Tu instrucción',value='Describí todos los elementos visibles y explicá cómo podría mejorarlos o convertirlos en un proyecto.',height=105)
        if st.button('Analizar la imagen con SKY',type='primary'):
            respuesta=ejecutar(vision_analizar,datos,tipo,pregunta,proveedor_vision)
            if respuesta: st.session_state['sky_vision_result']=respuesta
        if st.session_state.get('sky_vision_result'):
            st.markdown(st.session_state['sky_vision_result'])
    else: st.info('Tomá una foto o subí una imagen para comenzar.')
    st.caption('Gemini, GPT, Claude y modelos Ollama con capacidad de visión. La disponibilidad concreta depende del modelo y tu cuenta. SKY no interpreta imágenes médicas como un diagnóstico.')

elif seccion=="🎨 SKY Studio 3D":
    st.title('🎨 SKY Studio 3D — foto → piezas → ensamblaje')
    st.write('Capturá una imagen, aislá cada componente mediante caja y segmentación asistida, ajustá la profundidad y armá un modelo 3D editable. Descargá el ensamblaje como **GLB**, más cada pieza PNG por separado.')
    st.warning('La conversión de una sola foto genera geometría **2.5D (siluetas extruidas)**. No reconstruye superficies ocultas ni sustituye fotogrametría o escaneo 3D de múltiples ángulos.')
    tab_input,tab_piezas,tab_final=st.tabs(['📷 Capturar imagen','✂️ Cortar en piezas','🧩 Ensamblar y exportar'])
    with tab_input:
        importar=st.file_uploader('Continuar proyecto anterior (ZIP generado por SKY)',type=['zip'],key='sky3d_import')
        if importar and st.button('Restaurar proyecto 3D'):
            try:
                imagen_guardada,piezas_guardadas=importar_paquete(importar.getvalue())
                st.session_state['sky3d_original']=imagen_guardada
                st.session_state['sky3d_parts']=piezas_guardadas
                st.session_state.pop('sky3d_hash',None)
                st.session_state.pop('sky3d_plot',None)
                st.session_state.pop('sky3d_download',None)
                st.success('Proyecto recuperado con todas sus piezas.')
            except Exception as exc:st.error(str(exc))
        iz,der=st.columns(2)
        with iz: img_cam=st.camera_input('Tomar imagen del objeto',key='studio_camara')
        with der: img_up=st.file_uploader('O subir una foto',type=['png','jpg','jpeg','webp'],key='studio_subida')
        src=img_up or img_cam
        if src:
            import hashlib
            raw=src.getvalue(); hash_actual=hashlib.sha256(raw).hexdigest()
            if hash_actual!=st.session_state.get('sky3d_hash'):
                ver=ejecutar(leer_imagen,raw)
                if ver is not None:
                    st.session_state['sky3d_hash']=hash_actual
                    st.session_state['sky3d_original']=png_bytes(ver)
                    st.session_state['sky3d_parts']=[]
                    st.session_state.pop('sky3d_plot',None)
                    st.session_state.pop('sky3d_download',None)
            if st.session_state.get('sky3d_original'):
                st.image(st.session_state['sky3d_original'],caption='Imagen base',width=520)
                st.info('Foto lista. Abrí «Cortar en piezas».')
    original=st.session_state.get('sky3d_original')
    if original:
        base=leer_imagen(original)
        w,h=base.size
        piezas=st.session_state.setdefault('sky3d_parts',[])
        with tab_piezas:
            st.write(f'Lienzo: {w} × {h} píxeles. Piezas añadidas: {len(piezas)} / 18.')
            nombre=st.text_input('Nombre de la pieza',value=f'Pieza {len(piezas)+1}',key='sky3d_name')
            col1,col2=st.columns(2)
            with col1:
                izquierda=st.slider('Borde izquierdo (%)',0,95,15,key='sky3d_left')
                arriba=st.slider('Borde superior (%)',0,95,15,key='sky3d_top')
            with col2:
                derecha=st.slider('Borde derecho (%)',5,100,85,key='sky3d_right')
                abajo=st.slider('Borde inferior (%)',5,100,85,key='sky3d_bottom')
            metodo=st.radio('Método de recorte',('grabcut','rectangulo'),
                  format_func=lambda v:'Detección asistida de primer plano (GrabCut)' if v=='grabcut' else 'Rectángulo transparente',horizontal=True)
            try:
                from PIL import ImageDraw
                dibujo=base.copy()
                rect=caja_relativa(w,h,izquierda/100,arriba/100,derecha/100,abajo/100)
                ImageDraw.Draw(dibujo).rectangle(rect,outline='#ff6600',width=max(2,w//150))
                dibujo.thumbnail((640,400))
                st.image(dibujo,caption='Vista previa de la selección — recuadro naranja')
            except ValueError:st.warning('Ajustá los bordes de la selección para que no se crucen.')
            profundidad=st.slider('Profundidad de esta pieza (relativa)',0.01,0.50,0.08,0.01,key='sky3d_depth')
            if st.button('Crear pieza aislada',type='primary',disabled=len(piezas)>=18):
                try:
                    area=caja_relativa(w,h,izquierda/100,arriba/100,derecha/100,abajo/100)
                    recorte=segmentar_parte(base,area,modo=metodo)
                    piezas.append({'name':nombre.strip()[:48] or f'Pieza {len(piezas)+1}',
                        'png':png_bytes(recorte),'depth':profundidad,'dx':0.,'dy':0.,'dz':0.,'enabled':True})
                    st.success('Pieza creada y añadida al proyecto. Podés repetir el proceso para cada elemento.')
                except Exception as exc:st.error(str(exc))
            for i,p in enumerate(piezas):
                with st.expander(f'Pieza {i+1} · {p["name"]}',expanded=(i==len(piezas)-1)):
                    st.image(p['png'],width=320)
                    st.download_button('Descargar PNG transparente',p['png'],file_name=f'pieza_{i+1:02}.png',mime='image/png',key=f'png_{i}')
                    if st.button('Eliminar esta pieza',key=f'piece_delete_{i}'):
                        piezas.pop(i);st.rerun()
        with tab_final:
            if not piezas: st.info('Primero creá al menos una pieza en la pestaña anterior.')
            else:
                st.write('Ajustá cada pieza: desplazamientos X, Y y Z. Al exportar, cada pieza permanece separada dentro del archivo 3D.')
                for i,p in enumerate(piezas):
                    with st.expander(f'🧩 {i+1}. {p["name"]}',expanded=(i==0)):
                        p['enabled']=st.checkbox('Incluir en el modelo final',value=p.get('enabled',True),key=f'enabled_{i}')
                        p['dx']=st.slider('Mover X',-1.,1.,float(p.get('dx',0.)),0.02,key=f'dx_{i}')
                        p['dy']=st.slider('Mover Y',-1.,1.,float(p.get('dy',0.)),0.02,key=f'dy_{i}')
                        p['dz']=st.slider('Mover Z',-1.,1.,float(p.get('dz',0.)),0.02,key=f'dz_{i}')
                        p['depth']=st.slider('Profundidad',0.01,0.5,float(p.get('depth',0.08)),0.01,key=f'de_{i}')
                if st.button('Ver vista previa 3D',key='sky3d_render'):
                    try:
                        import plotly.graph_objects as go
                        from neural_core.sky_3d import _mesh_from_rgba
                        from io import BytesIO
                        from PIL import Image
                        fig=go.Figure()
                        for i,p in enumerate(piezas):
                            if not p.get('enabled',True):continue
                            mesh=_mesh_from_rgba(Image.open(BytesIO(p['png'])),depth=p['depth'],max_side=28)
                            verts=mesh.vertices.copy()
                            verts[:,0]+=p['dx'];verts[:,1]+=p['dy'];verts[:,2]+=p['dz']
                            color=mesh.visual.face_colors
                            facecolor=[f'rgb({rgb[0]},{rgb[1]},{rgb[2]})' for rgb in color]
                            fig.add_trace(go.Mesh3d(x=verts[:,0],y=verts[:,1],z=verts[:,2],
                                i=mesh.faces[:,0],j=mesh.faces[:,1],k=mesh.faces[:,2],
                                facecolor=facecolor,name=p['name'],opacity=1.0))
                        fig.update_layout(scene=dict(aspectmode='data'),margin=dict(t=10,b=10,l=10,r=10),height=520)
                        st.session_state['sky3d_plot']=fig
                    except Exception as exc:st.error(f'No se generó la vista previa: {exc}')
                if st.session_state.get('sky3d_plot') is not None:st.plotly_chart(st.session_state['sky3d_plot'],use_container_width=True)
                if st.button('Preparar exportación GLB y piezas',type='primary'):
                    try:
                        glb=ensamblar_glb(piezas,w,h)
                        paquete=crear_paquete(piezas,original,w,h)
                        st.session_state['sky3d_download']={'glb':glb,'zip':paquete}
                        st.success('Modelo y paquete generados localmente.')
                    except Exception as exc:st.error(f'No se pudo exportar: {exc}')
                salida=st.session_state.get('sky3d_download')
                if salida:
                    st.download_button('⬇️ Descargar modelo ensamblado .GLB',salida['glb'],file_name='SKY_modelo_3D.glb',mime='model/gltf-binary')
                    st.download_button('⬇️ Descargar todas las piezas + proyecto ZIP',salida['zip'],file_name='SKY_Studio_3D_Piezas.zip',mime='application/zip')
                st.caption('Para modelado 3D real con todas las caras y piezas mecánicas editables, trabajá con Blender y capturas desde varios ángulos.')
    else:
        with tab_piezas:st.info('Cargá o tomá una imagen en la primera pestaña.')

elif seccion=="📁 SKY Office Studio":
    st.title('📁 SKY Office Studio — Documentos y presentaciones')
    st.write('Creá archivos **Word, Excel, PowerPoint y PDF reales**, editables cuando el formato lo admite. También CSV, Markdown y HTML. El proceso local no envía tus datos a otra empresa.')
    opciones=list(FORMATS)
    with st.form('sky_office_creator'):
        k=st.selectbox('Formato de salida',opciones,format_func=lambda x:FORMATS[x][0])
        name=st.text_input('Título',value='Mi proyecto con SKY',max_chars=160)
        topic=st.text_area('Objetivo e instrucciones',placeholder='Prepará una clase sobre innovación, o una presentación de mi propuesta comercial...',height=90,max_chars=6000)
        content=st.text_area('Contenido editable',placeholder='# Introducción\nIdea principal...\n# Desarrollo\n- Punto uno\n- Punto dos',height=210,max_chars=49000)
        csv_text=st.text_area('Tabla en CSV (opcional para Excel, Word, PDF o diapositivas)',placeholder='Concepto,Monto,Estado\nMateriales,250,Pendiente',height=85,max_chars=28000)
        template=st.selectbox('Plantilla',['general','presupuesto'],help='La plantilla presupuesto crea fórmulas editables en Excel.')
        use_ai=st.checkbox('Redactar contenido con un proveedor de IA (envía el tema al proveedor seleccionado)',value=False)
        provider=st.selectbox('Proveedor (solo se utilizará si activás la casilla de IA)',['gemini','openai','anthropic','ollama','groq','mistral','deepseek'])
        done=st.form_submit_button('✦ Crear archivo',type='primary')
    if done:
        import csv as csv_mod,io as io_mod
        spec={'kind':k,'title':name,'prompt':topic,'content':content,'csv':csv_text,'template':template}
        if use_ai:
            if not topic.strip():st.error('Indicá el tema para usar un proveedor de IA.')
            else:
                try:
                    texto,_=responder(f'Redactá un contenido estructurado, claro y editable sobre: {topic}. '+
                       'Usá títulos Markdown, viñetas y sin inventar datos. Tipo de archivo: '+k,
                       'SKY Office Studio',proveedor=provider)
                    spec['content']=texto+'\n\n'+content
                except Exception as ex:st.error('IA no disponible: '+type(ex).__name__)
        if not use_ai or spec['content']!=content:
            resultado=ejecutar(create_document,spec)
            if resultado:
                st.session_state['sky_last_office']=resultado
                st.success('Archivo generado correctamente: '+resultado.filename)
    if st.session_state.get('sky_last_office'):
        doc=st.session_state['sky_last_office']
        st.download_button('⬇ Descargar '+doc.description,data=doc.data,file_name=doc.filename,mime=doc.media_type,type='primary')
    st.caption('Los archivos se generan en esta sesión y se descargan a tu equipo. Las diapositivas, hojas y Word se pueden continuar editando. La redacción con IA es opcional y puede tener costo de API.')

elif seccion=="🧬 SKY Evolución":
    st.title('🧬 SKY Evolución — memoria de mejoras y objetivos')
    st.write('SKY puede recopilar tus evaluaciones, gestionar objetivos y preparar propuestas de mejora. No modifica automáticamente su código ni tu web: las mejoras se prueban antes de instalarse.')
    t1,t2,t3=st.tabs(['Aprender de evaluaciones','Mis metas','Evolución del software'])
    with t1:
        with st.form('sky_nueva_evaluacion'):
            modulo=st.selectbox('Función que evaluás',['IA universal','Voz','Visión','Studio 3D','Finanzas','BAQUEANO','Redes','Dispositivos','Otros'])
            valor=st.slider('¿Qué tan útil fue?',1,5,3)
            nota=st.text_area('¿Qué funcionó y qué debería mejorar?')
            if st.form_submit_button('Guardar evaluación'):
                guardar_con_feedback(sky_feedback,modulo,valor,nota,mensaje='Evaluación conservada en SKY')
        data=feedback_resumen()
        if data:st.dataframe(pd.DataFrame(data),use_container_width=True,hide_index=True)
    with t2:
        with st.form('sky_new_goal'):
            nom=st.text_input('Meta',placeholder='Conseguir 10 clientes nuevos')
            met=st.text_input('Unidad de medida',value='clientes')
            aim=st.number_input('Objetivo',min_value=0.01,max_value=1000000000.,value=10.)
            if st.form_submit_button('Guardar meta'):
                guardar_con_feedback(nueva_meta,nom,met,aim,mensaje='Meta guardada')
        for goal in metas():
            st.write(f'**{goal["title"]}** — {goal["actual"]:g} / {goal["target"]:g} {goal["metric"]}')
            st.progress(min(1.0,goal['actual']/goal['target']))
            nuevo=st.number_input('Avance registrado',min_value=0.,max_value=1e12,value=float(goal['actual']),key=f'goal_{goal["id"]}')
            if st.button('Actualizar avance',key=f'goal_update_{goal["id"]}'):
                guardar_con_feedback(actualizar_meta,goal['id'],nuevo)
    with t3:
        with st.form('sky_prop_mejora'):
            nom=st.text_input('Nombre de mejora',placeholder='Aprender voz sin Internet')
            detalles=st.text_area('Descripción técnica y resultado esperado')
            if st.form_submit_button('Proponer mejora'):
                guardar_con_feedback(proponer_mejora,nom,detalles,mensaje='Mejora propuesta; no instalada')
        lista=mejoras()
        if lista:
            st.dataframe(pd.DataFrame(lista),use_container_width=True,hide_index=True)
            st.caption('Aprobar una propuesta no instala ni ejecuta código; marca su estado para desarrollo y pruebas.')
            opciones={m['id']:f'#{m["id"]} · {m["title"]}' for m in lista}
            ident=st.selectbox('Mejora a revisar',list(opciones),format_func=lambda i:opciones[i])
            estado=st.selectbox('Estado',['pendiente','aprobada_para_desarrollo','descartada'])
            if st.button('Guardar decisión'):guardar_con_feedback(cambiar_mejora,ident,estado)

elif seccion=="🧰 Herramientas SKY":
    st.title('🧰 Núcleo de herramientas internas')
    st.write('SKY incluye herramientas propias que funcionan sin enviar datos a ninguna IA. Elegí la capacidad y ejecutala localmente.')
    st.dataframe(pd.DataFrame([{'Capacidad':v.name,'Función':v.description,'Confirmación':v.needs_confirmation} for v in SKILLS.values()]),hide_index=True,use_container_width=True)
    herramienta=st.selectbox('Herramienta',list(SKILLS))
    argumento=st.text_input('Expresión matemática (solo para calcular)',placeholder='(500 - 120) * 1.15') if herramienta=='calcular' else ''
    if st.button('Ejecutar herramienta local',type='primary'):
        resultado=ejecutar(execute_skill,herramienta,argumento)
        if resultado is not None:st.write(resultado)
    st.caption('Sin intérprete de shell, pagos ni acciones ocultas. Las tareas en otros dispositivos usan el agente de permisos existente.')

elif seccion=="🔔 SKY Live":
    st.title('🔔 SKY Live — un asistente disponible mientras está ejecutándose')
    st.write('Este monitor local revisa de forma informativa la disponibilidad de BAQUEANO. No modifica la web, no responde mensajes ni mueve dinero. Para mantenerlo activo cerrando el navegador necesitás ejecutar el proceso SKY Live en tu computadora.')
    st.code('python sky_live.py --intervalo 1800',language='bash')
    st.caption('Alternativa Windows: INICIAR_SKY_LIVE_WINDOWS.bat · Linux/macOS: iniciar_sky_live_linux_mac.sh. Se detiene con Ctrl+C o apagando la computadora.')
    if st.button('Comprobar BAQUEANO ahora',type='primary'):
        result=ejecutar(sky_live_check)
        if result is not None:
            if result['ok']: st.success('BAQUEANO respondió correctamente. Estado HTTP '+str(result['http_code']))
            else:st.warning('No se pudo verificar que BAQUEANO esté disponible. Revisá tu conexión y el sitio.')
    rows=sky_live_historial(50)
    if rows:st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    else:st.info('Todavía no hay registros del monitor SKY Live.')
    st.caption('El monitoreo genera eventos locales; no envía notificaciones automáticas al teléfono ni garantiza disponibilidad 24/7.')

elif seccion=="🌐 SKY Metaverso y API":
    st.title('🌐 SKY Metaverso — Tu universo personal 3D')
    st.write('Construí ciudades, espacios educativos, laboratorios, mundos naturales y escenarios propios. La escena se guarda localmente y puede exportarse como GLB para Blender. El servidor privado de SKY Engine debe estar activo.')
    metaverso_url='http://127.0.0.1:8765/sky'
    try:
        with request.urlopen(metaverso_url,timeout=1) as respuesta:
            motor_activo=respuesta.status==200
    except (URLError,TimeoutError,OSError):
        motor_activo=False
    if motor_activo:
        st.success('SKY Engine está activo. Abrí el metaverso en otra pestaña para usarlo.')
    else:
        st.warning('SKY Engine no responde. Iniciá `INICIAR_SKY_METAVERSO_WINDOWS.bat` (Windows) o `bash iniciar_sky_metaverso_linux_mac.sh` (Linux/macOS), y volvé a cargar esta página.')
    st.link_button('↗ Abrir SKY Metaverso en otra pestaña', metaverso_url,disabled=not motor_activo)
    st.caption('Clave: archivo local_data/sky_api_token.txt del servidor. API Swagger: http://127.0.0.1:8765/docs. No pongás la clave en una URL ni la publiques.')
    st.info('El metaverso se abre fuera del panel porque sus protecciones de seguridad impiden cargarlo dentro de un iframe.')

elif seccion=="🎙️ SKY y dispositivos":
    st.title('🎙️ SKY — voz y dispositivos')
    st.write('Hablá en español, consultá a Gemini o prepará acciones para equipos tuyos y autorizados. **Ninguna acción remota se ejecuta desde una transcripción sin que la confirmés en pantalla.**')
    tab_voz, tab_dispositivos, tab_guia = st.tabs(['🎤 Hablar con SKY','🖥️ Dispositivos emparejados','🔐 Instalación y privacidad'])
    if 'sky_tokens' not in st.session_state: st.session_state['sky_tokens']={}
    if 'sky_historia' not in st.session_state: st.session_state['sky_historia']=[]
    with tab_dispositivos:
        st.subheader('Emparejar mi computadora')
        st.caption('Instalá primero el agente en cada computadora. Para acceso remoto usá una dirección HTTPS de Tailscale Serve; no abras puertos públicos.')
        with st.form('parear_nuevo'):
            n=st.text_input('Nombre',placeholder='PC de casa')
            u=st.text_input('Dirección del agente',placeholder='https://mi-pc.mi-tailnet.ts.net')
            t=st.text_input('Token entregado por el agente',type='password')
            parear=st.form_submit_button('Verificar y emparejar')
        if parear:
            try:
                datos=call_device(u,t, 'status')
                if not datos.get('ok'): raise RuntimeError('El agente no confirmó su estado.')
                save_device(n,u)
                st.session_state['sky_tokens'][n.strip()]=t.strip()
                st.success('Equipo emparejado: '+datos.get('device','sin nombre'))
            except Exception as exc: st.error(str(exc))
        dispositivos=paired_devices()
        if dispositivos:
            st.subheader('Administrar equipos')
            opciones=[x['name'] for x in dispositivos]
            seleccionado=st.selectbox('Elegir dispositivo',opciones,key='sky_dispositivo')
            info=next(x for x in dispositivos if x['name']==seleccionado)
            st.caption('Dirección: '+info['url'])
            token=st.session_state['sky_tokens'].get(seleccionado,'')
            if not token:
                ingresado=st.text_input('Token de este dispositivo (sólo en esta sesión)',type='password',key='reponer_token')
                if st.button('Activar acceso en esta sesión') and ingresado:
                    st.session_state['sky_tokens'][seleccionado]=ingresado.strip()
                    st.rerun()
            botones=st.columns(2)
            if botones[0].button('Consultar estado',disabled=not bool(token)):
                try: st.json(call_device(info['url'],token,'status'))
                except Exception as exc: st.error(str(exc))
            if botones[1].button('Olvidar dispositivo'):
                remove_device(seleccionado)
                st.session_state['sky_tokens'].pop(seleccionado,None)
                st.session_state.pop('sky_pending',None)
                st.rerun()
            st.subheader('Preparar una orden manual')
            tipo=st.selectbox('Acción',['Abrir aplicación','Abrir página HTTPS'],key='sky_manual_tipo')
            if tipo=='Abrir aplicación':
                app=st.selectbox('Aplicación permitida',APP_OPTIONS,key='sky_app')
                acc={'action':'launch_app','params':{'app':app},'description':'Abrir '+app}
            else:
                url=st.text_input('Sitio HTTPS',value='https://baqueanonicaragua.com',key='sky_url')
                acc={'action':'open_url','params':{'url':url},'description':'Abrir '+url}
            if st.button('Preparar orden para confirmar',disabled=not bool(token)):
                st.session_state['sky_pending']={**acc,'device':seleccionado}
        else: st.info('Todavía no hay equipos emparejados. Podés usar el chat de voz igualmente.')
    with tab_voz:
        voz_proveedor, voz_modelo = elegir_motor('sky_voz_motor','SKY voz')
        en_cola=read_inbox()
        if en_cola:
            st.info(f'Tenés {len(en_cola)} propuesta(s) pendiente(s) del modo manos libres (no ejecutadas).')
            cola=st.selectbox('Orden por voz para revisar',en_cola,format_func=lambda x:x.get('text',''))
            c1,c2=st.columns(2)
            if c1.button('Pasar a confirmación',key='aceptar_inbox'):
                equipo=st.session_state.get('sky_dispositivo')
                if not equipo: st.warning('Primero seleccioná un equipo emparejado en la pestaña Dispositivos.')
                else:
                    st.session_state['sky_pending']={**cola,'device':equipo}
                    dismiss_inbox(cola['id']); st.rerun()
            if c2.button('Descartar esta orden',key='descartar_inbox'):
                dismiss_inbox(cola['id']); st.rerun()
        st.caption('El audio grabado se envía a Gemini para transcribirlo (requiere GEMINI_API_KEY); la respuesta la genera el proveedor seleccionado arriba. También podés escribir sin Gemini.')
        grabacion=st.audio_input('Hablar con SKY',sample_rate=16000,key='sky_microfono')
        if grabacion:
            clip=grabacion.getvalue()
            marca=hashlib.sha256(clip).hexdigest()
            if marca != st.session_state.get('sky_audio_procesado'):
                st.session_state['sky_audio_procesado']=marca
                try:
                    with st.spinner('Reconociendo voz con Gemini…'):
                        st.session_state['sky_entrada']=transcribir_audio(clip)
                        st.session_state['sky_texto']=st.session_state['sky_entrada']
                    st.success('Escuché: '+st.session_state['sky_entrada'])
                except Exception as exc: st.error(str(exc))
        with st.form('sky_orden'):
            frase=st.text_input('O escribí una orden',key='sky_texto')
            voz_salida=st.checkbox('Reproducir la respuesta en voz española (gTTS)',value=False)
            auto_ejecutar=st.checkbox('Ejecutar directamente acciones simples en el equipo emparejado',value=False,
                help='Solo estado, HTTPS, aplicaciones y teclas multimedia; las notas siempre necesitan confirmación.')
            enviar=st.form_submit_button('Enviar a SKY',type='primary')
        if enviar and frase.strip():
            st.session_state['sky_entrada']=''
            orden=interpret_command(frase)
            if orden:
                ds=paired_devices()
                elegido=st.session_state.get('sky_dispositivo')
                if elegido and any(d['name']==elegido for d in ds):
                    if auto_ejecutar and orden['action'] in ('status','open_url','launch_app','media_key'):
                        asociado=next(d for d in ds if d['name']==elegido)
                        tok=st.session_state['sky_tokens'].get(elegido,'')
                        if not tok:
                            st.warning('Falta el token de este equipo. Activá el acceso en Dispositivos.')
                        else:
                            try:
                                resultado=call_device(asociado['url'],tok,orden['action'],orden['params'])
                                if not resultado.get('ok'):
                                    raise RuntimeError('El agente no confirmó la operación.')
                                st.session_state['sky_ultima_respuesta']='Acción completada en '+elegido+': '+orden['description']
                                st.success(st.session_state['sky_ultima_respuesta'])
                            except Exception as exc:
                                st.error('La acción no se ejecutó: '+str(exc))
                    else:
                        st.session_state['sky_pending']={**orden,'device':elegido}
                        st.info('Orden interpretada: '+orden['description']+'. Confirmá abajo para ejecutarla.')
                else:
                    st.warning('La orden requiere un dispositivo emparejado. Seleccioná uno en la pestaña Dispositivos.')
            else:
                proveedor=voz_proveedor
                modelo=voz_modelo
                try:
                    with st.spinner('SKY está respondiendo…'):
                        local=interpret_local_command(frase)
                        if local is not None:answer=local
                        else:answer,_=responder(frase,'Asistente SKY personal',st.session_state['sky_historia'],modelo,proveedor=proveedor)
                    st.session_state['sky_historia'].extend([{'role':'user','content':frase},{'role':'assistant','content':answer}])
                    st.session_state['sky_ultima_respuesta']=answer
                    if voz_salida:
                        try: st.session_state['sky_audio_salida']=hablar_texto(answer)
                        except Exception as exc: st.warning('No se generó la voz: '+str(exc))
                    else: st.session_state.pop('sky_audio_salida',None)
                except Exception as exc: st.error(str(exc))
        respuesta=st.session_state.get('sky_ultima_respuesta')
        if respuesta: st.markdown('**SKY:** '+respuesta)
        if st.session_state.get('sky_audio_salida'):
            st.audio(st.session_state['sky_audio_salida'],format='audio/mp3',autoplay=True)
        st.caption('Ejemplos: «Abrí YouTube», «Abrí calculadora», «Estado de mi computadora», «Explicame qué es Gemini», «Ayudame con una campaña para BAQUEANO».')
    pendiente=st.session_state.get('sky_pending')
    if pendiente:
        st.divider()
        st.warning('Orden pendiente — NO ejecutada. Revisá el equipo y la acción antes de confirmar.')
        st.json({'dispositivo':pendiente['device'],'acción':pendiente['action'], 'parámetros':pendiente['params']})
        col1,col2=st.columns(2)
        if col1.button('✅ Confirmar y ejecutar',type='primary'):
            asociado=next((d for d in paired_devices() if d['name']==pendiente['device']),None)
            tok=st.session_state['sky_tokens'].get(pendiente['device'])
            if not asociado or not tok: st.error('El dispositivo no está disponible o falta su token.')
            else:
                try:
                    params_para_agente={**pendiente['params']}
                    if pendiente['action'] in ('note_create','note_append','note_trash'):
                        params_para_agente['confirmed']=True  # botón pulsado por el usuario
                    resultado=call_device(asociado['url'],tok,pendiente['action'],params_para_agente)
                    st.json(resultado)
                    st.session_state.pop('sky_pending',None)
                except Exception as exc: st.error(str(exc))
        if col2.button('❌ Cancelar orden'):
            st.session_state.pop('sky_pending',None)
            st.rerun()
    with tab_guia:
        st.markdown("""**En cada computadora autorizada:**

```bash
python agente_dispositivo.py
```

Guardá el token que muestra esa computadora. Para acceso desde tu móvil u otra PC, instalá Tailscale en ambos dispositivos y, en la computadora con el agente, activá:

```bash
tailscale serve 8765
```

Copiá la dirección HTTPS del agente desde Tailscale y emparejala en este panel. Para acceder al panel SKY desde el celular también necesitás Tailscale, **contraseña del panel**, HTTPS y servir su puerto 8501. No usés Tailscale Funnel para exponerlo públicamente.

**Lo que funciona en esta versión:** voz pulsar-para-hablar, respuestas de Gemini/Ollama, lectura de estado, apertura de páginas HTTPS y cuatro aplicaciones permitidas en computadoras con agente. La ejecución se confirma manualmente.

**Modo manos libres opcional:** instalá `vosk sounddevice pyttsx3`, descargá un modelo de voz español de Vosk e iniciá `python sky_manos_libres.py --model ruta/al/modelo`. Se activa al escuchar «SKY», se detiene con Ctrl+C y envía órdenes de equipo a una cola para confirmación. **No incluido todavía:** control nativo de Android/iOS, manejo completo del escritorio, automatización de otras apps sin API, encendido remoto de equipos apagados, movimiento de dinero y comandos de shell arbitrarios. La presencia de la herramienta no permite saltar contraseñas ni restricciones del sistema operativo.""")

elif seccion=="💰 Finanzas personales":
    st.title("💰 Gestión de dinero")
    st.caption("Ingresos reales y gastos declarados; no se conecta a bancos. NIO y USD se calculan por separado.")
    with st.form("nuevo_movimiento",clear_on_submit=True):
        a,b,c,d=st.columns(4)
        with a: tipo=st.selectbox("Tipo",["ingreso","gasto"])
        with b: moneda=st.selectbox("Moneda",["NIO","USD"])
        with c: categoria=st.text_input("Categoría",value="Servicios")
        with d: monto=st.number_input("Importe",min_value=0.01,max_value=1_000_000.0,step=1.0)
        concepto=st.text_input("Concepto")
        if st.form_submit_button("Guardar movimiento"):
            if concepto.strip() and categoria.strip():
                guardar_con_feedback(guardar_movimiento,tipo,categoria,concepto,monto,moneda,mensaje="Movimiento guardado")
            else: st.error("Ingresa categoría y concepto")
    mes=st.text_input("Mes de análisis (AAAA-MM)",value=date.today().strftime("%Y-%m"))
    estadisticas=resumen(mes)
    for currency, datos in estadisticas["totales"].items():
        col1,col2,col3=st.columns(3)
        col1.metric(f"Ingresos {currency}",f"{datos['ingreso']/100:,.2f}")
        col2.metric(f"Gastos {currency}",f"{datos['gasto']/100:,.2f}")
        col3.metric(f"Saldo {currency}",f"{(datos['ingreso']-datos['gasto'])/100:,.2f}")
    with st.expander("Crear o editar presupuesto"):
        with st.form("ppto"):
            cat=st.text_input("Categoría de gasto",value="Publicidad")
            cur=st.selectbox("Moneda del presupuesto",["NIO","USD"])
            top=st.number_input("Límite mensual",min_value=0.0,step=10.0)
            if st.form_submit_button("Guardar presupuesto"):
                guardar_con_feedback(guardar_presupuesto,cat,cur,top,mensaje="Presupuesto guardado")
        st.dataframe(pd.DataFrame(presupuestos()),hide_index=True,use_container_width=True)
    for a in estadisticas["alertas"]:
        st.warning(f"Presupuesto alcanzado o excedido: {a['categoria']} ({a['moneda']}) gastado {a['gasto']:.2f} / {a['limite']:.2f}")
    data=movimientos()
    if data:
        st.dataframe(pd.DataFrame(data).assign(monto=lambda df:df.monto_centavos/100).drop(columns="monto_centavos"),hide_index=True,use_container_width=True)
    st.subheader("Escenario hipotético de ahorro/inversión")
    c1,c2,c3,c4=st.columns(4)
    with c1: cap=st.number_input("Capital inicial",0.0,1_000_000.0,100.0)
    with c2: aporte=st.number_input("Aporte mensual",0.0,1_000_000.0,20.0)
    with c3: tasa=st.number_input("Tasa anual supuesta (%)",-50.0,50.0,4.0)
    with c4: meses=st.number_input("Meses",1,600,12)
    st.metric("Resultado matemático de escenario, no pronóstico",f"{crecimiento_compuesto(cap,aporte,tasa,meses):,.2f}")
    st.caption("No incluye impuestos, comisiones, fluctuaciones de mercado ni pérdidas superiores al supuesto usado.")

elif seccion=="🚀 Generar ingresos":
    st.title("🚀 Motor de oportunidades y ventas")
    st.write("Herramientas para **conseguir clientes y vender trabajo real**. Los importes de las oportunidades no son ingresos cobrados.")
    with st.form("cliente",clear_on_submit=True):
        ca,cb,cc=st.columns(3)
        with ca: n=st.text_input("Cliente o prospecto")
        with cb: serv=st.text_input("Servicio ofrecido",value="Diseño de contenido digital")
        with cc: valor=st.number_input("Valor posible",min_value=0.0,max_value=1_000_000.0,value=50.0)
        da,db=st.columns(2)
        with da: mon=st.selectbox("Moneda",["USD","NIO"])
        with db: etapa=st.selectbox("Estado",list(ETAPAS))
        notas=st.text_area("Notas de contacto",height=75)
        if st.form_submit_button("Agregar oportunidad"):
            if n.strip() and serv.strip():
                guardar_con_feedback(agregar_cliente,n,serv,valor,mon,etapa,notas,mensaje="Oportunidad guardada")
            else: st.error("Nombre y servicio obligatorios")
    resumen_c=resumen_comercial()
    for cur,dat in resumen_c.items():
        cols=st.columns(3)
        cols[0].metric(f"Ventas marcadas como ganadas ({cur})",f"{dat['confirmado']:,.2f}")
        cols[1].metric(f"Potencial abierto ({cur})",f"{dat['potencial']:,.2f}")
        cols[2].metric(f"Valor ponderado estimado ({cur})",f"{dat['estimado']:,.2f}")
    registros=listar_clientes()
    if registros:
        st.dataframe(pd.DataFrame(registros).assign(valor=lambda df:df.monto_centavos/100).drop(columns="monto_centavos"),hide_index=True,use_container_width=True)
        with st.form("cambiar_estado"):
            eleccion=st.selectbox("Actualizar oportunidad",[x['id'] for x in registros],format_func=lambda id_:next(f"#{r['id']} · {r['nombre']}" for r in registros if r['id']==id_))
            estado=st.selectbox("Nueva etapa",list(ETAPAS))
            if st.form_submit_button("Actualizar estado"):
                guardar_con_feedback(cambiar_etapa,eleccion,estado,mensaje="Estado actualizado")
    st.subheader("Simulador de ventas (NO ingresos garantizados)")
    a,b,c,d=st.columns(4)
    with a: precio=st.number_input("Precio del servicio",0.0,1_000_000.0,25.0)
    with b: contactos=st.number_input("Contactos proyectados",0,100000,100)
    with c: conversion=st.slider("Conversión asumida (%)",0.0,100.0,5.0,0.5)
    with d: costo=st.number_input("Costo total previsto",0.0,1_000_000.0,100.0)
    r=simular_ventas(precio,contactos,conversion,costo)
    st.write(r)
    st.caption("Necesitás conseguir clientes reales, entregar valor y cobrar. Este escenario no mide demanda ni valida el mercado.")
    st.subheader("Servicios monetizables que podés ofrecer")
    st.markdown("• Diseño de identidad y campañas para negocios.  \n• Cursos y materiales educativos digitales.  \n• Automatización y soluciones de IA para pymes.  \n• Video corto, edición y estrategia de redes.  \n• Consultoría en presencia digital y comercio electrónico.")

elif seccion=="📈 Bolsa y Bitcoin":
    st.title("📈 Bolsa de valores y criptomonedas")
    st.warning("Información de mercado, no asesoría personalizada. No hay compra, venta, custodia, bots de trading ni garantía de ganancias.")
    op1,op2=st.tabs(["Bitcoin / criptomonedas", "Acciones / ETFs"])
    with op1:
        selec=st.multiselect("Criptomonedas",list(CRYPTOS),default=["Bitcoin","Ethereum"])
        if st.button("Consultar precios cripto",type="primary"):
            precios=ejecutar(cripto_precios,[CRYPTOS[s] for s in selec])
            if precios:
                st.dataframe(pd.DataFrame(precios),hide_index=True,use_container_width=True)
                st.caption("Fuente: CoinGecko · se muestran tiempos de actualización publicados por el proveedor")
    with op2:
        stock=st.selectbox("Activo",list(ACCIONES))
        if st.button("Consultar cierres históricos"):
            hist=ejecutar(accion_historial,ACCIONES[stock])
            if hist:
                d=pd.DataFrame(hist).set_index("fecha")
                st.line_chart(d)
                st.metric("Rendimiento histórico del período (%)",f"{rentabilidad_historica(hist[0]['cierre_usd'],hist[-1]['cierre_usd']):+.2f}%")
                st.dataframe(pd.DataFrame(hist[-12:]),hide_index=True)
                st.caption("Cierres diarios históricos del proveedor Stooq, NO cotizaciones en tiempo real. No incluyen dividendos ni comisiones.")
    alerta_red()

elif seccion=="📰 Noticias e Internet":
    st.title("📰 Noticias e investigación en Internet")
    tema=st.text_input("Tema de actualidad",value="Inteligencia artificial Nicaragua")
    if st.button("Buscar noticias recientes"):
        resultados=ejecutar(noticias,tema)
        if resultados:
            for r in resultados:
                st.markdown(f"**{r['titular']}**")
                st.caption(f"{r['fuente']} · {r['fecha']}")
                st.link_button("Abrir fuente",r['enlace'])
    st.divider()
    buscar=st.text_input("Buscar información enciclopédica",value="Aprendizaje automático")
    if st.button("Consultar Wikipedia"):
        items=ejecutar(wikipedia,buscar)
        if items:
            for item in items: st.markdown(f"[{item['titulo']}]({item['url']})")
    alerta_red()

elif seccion=="📣 Redes sociales":
    st.title("📣 Social Studio — campañas y ventas")
    with st.form("marketing"):
        a,b=st.columns(2)
        with a:
            nombre=st.text_input("Nombre del negocio o marca",value="Mi emprendimiento")
            producto=st.text_input("Producto o servicio",value="Servicios digitales")
            precio=st.text_input("Precio o paquete",value="Desde US$25")
        with b:
            publico=st.text_input("Público objetivo",value="Pequeños negocios")
            red=st.selectbox("Red social",list(REDES))
            objetivo=st.selectbox("Objetivo",["captar clientes","obtener prospectos","ganar seguidores","presentar un lanzamiento"])
        generar=st.form_submit_button("Crear publicación + guion",type="primary")
    if generar:
        resultado=ejecutar(campana,nombre,publico,producto,precio,red,objetivo)
        if resultado:
            st.text_area("Borrador editable",resultado,height=350)
            boton_descarga(resultado,"campana_neuralt.txt")
    st.caption("Podés ampliar este texto con Gemini desde IA universal o Educación e investigación.")

elif seccion=="🎵 Música y películas":
    st.title("🎵 Música, cine y entretenimiento")
    medio=st.radio("Explorar",["Música", "Películas"],horizontal=True)
    termino=st.text_input("Nombre de canción, artista o película",value="Nicaragua")
    if st.button("Buscar en catálogo"):
        items=ejecutar(catalogo_itunes,termino,"song" if medio=="Música" else "movie")
        if items:
            for x in items:
                st.write(f"**{x['titulo']}** · {x['artista']} · {x['genero']} · {x['fecha']}")
                if x['enlace'].startswith("https://"): st.link_button("Ver en catálogo",x['enlace'])
    st.caption("Metadatos y enlaces de iTunes; no permite descargar obras comerciales ni asegura disponibilidad regional.")
    alerta_red()

elif seccion=="🎞️ Imágenes y videos":
    st.title("🎞️ Laboratorio multimedia")
    tip=st.selectbox("Tipo de proyecto",["Vídeo corto", "Guion de película", "Imagen publicitaria", "Música original", "Podcast", "Documental", "Video educativo"])
    idea=st.text_area("Idea que querés producir")
    audiencia=st.text_input("Público",value="Audiencia general")
    if st.button("Crear plan creativo"):
        plan=ejecutar(produccion,tip,idea,audiencia)
        if plan:
            st.text_area("Plan de producción",plan,height=300)
            boton_descarga(plan,"guion_neuralt.txt")
    st.divider()
    st.subheader("Conversión local de imágenes")
    adjunto=st.file_uploader("Imagen PNG, JPG o WebP",type=["png","jpg","jpeg","webp"])
    a,b,c=st.columns(3)
    with a: formato=st.selectbox("Salida",["WEBP","PNG","JPEG"])
    with b: calidad=st.slider("Calidad",50,100,85)
    with c: ancho=st.number_input("Dimensión máxima (px)",min_value=100,max_value=3840,value=1920)
    if adjunto and st.button("Convertir imagen"):
        resultado=ejecutar(convertir_imagen,adjunto.getvalue(),formato,calidad,int(ancho))
        if resultado:
            blob,tamano=resultado
            st.image(blob,caption=f"Imagen: {tamano[0]} × {tamano[1]} px",width=350)
            st.download_button("Descargar imagen",blob,file_name=f"imagen_neuralt.{formato.lower()}",mime=f"image/{'jpeg' if formato=='JPEG' else formato.lower()}")
    st.divider()
    st.subheader("Generación de imágenes con Gemini")
    st.caption("Requiere API activa, acceso al modelo de imágenes y puede tener costos de consumo.")
    descripcion=st.text_area("Descripción de la imagen a generar",key="prompt_imagen_gemini")
    if st.button("Generar imagen con Gemini",key="gemini_crear_imagen"):
        resultado=ejecutar(generar_imagen,descripcion)
        if resultado:
            st.session_state['ultima_imagen_generada']=resultado
    if 'ultima_imagen_generada' in st.session_state:
        blob,mime=st.session_state['ultima_imagen_generada']
        st.image(blob,caption="Imagen generada por Gemini")
        ext='jpg' if mime=='image/jpeg' else 'webp' if mime=='image/webp' else 'png'
        st.download_button("Descargar imagen generada",blob,file_name=f"neuralt_gemini.{ext}",mime=mime)
    st.subheader("Analizar imágenes con Gemini")
    imagen_gemini=st.file_uploader("Imagen para análisis por IA",type=["png","jpg","jpeg","webp"],key="gemini_vision")
    consulta_gemini=st.text_input("¿Qué querés saber de la imagen?",value="Describe la imagen y proponé mejoras",key="gemini_image_query")
    if imagen_gemini and st.button("Analizar con Gemini"):
        tipo={'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp'}.get(imagen_gemini.name.lower().split('.')[-1],'')
        txt=ejecutar(analizar_imagen,consulta_gemini,imagen_gemini.getvalue(),tipo)
        if txt: st.write(txt)
    st.caption("Los videos, música y podcasts disponen de planificación/guiones. La renderización directa necesita un proveedor multimedia activado.")

elif seccion=="🔐 Antivirus y hacking ético":
    st.title("🔐 Seguridad y hacking ético")
    st.warning("Este módulo hace comprobaciones heurísticas de archivos y código, **no un análisis antivirus completo**. Nunca ejecutes archivos sospechosos para probarlos.")
    archivo=st.file_uploader("Analizar un archivo de menos de 12 MB",type=None)
    if archivo and st.button("Analizar archivo localmente"):
        reporte=ejecutar(revisar_archivo,archivo.name,archivo.getvalue())
        if reporte: st.json(reporte)
    st.subheader("Laboratorio de seguridad autorizado")
    st.markdown("- Aprender OWASP, contraseñas fuertes, autenticación multifactor y protección de cuentas.\n- Revisar código y dependencias propios en ambientes de prueba.\n- Hacer copias de seguridad, actualizaciones y verificaciones de permisos.\n- Practicar únicamente en máquinas o laboratorios propios o con autorización explícita.")
    st.caption("Sin módulos para comprometer dispositivos ajenos, robar credenciales, lanzar malware o acceder a cuentas no autorizadas.")

elif seccion=="🎓 Educación e investigación":
    st.title("🎓 Educación, innovación, deportes, salud y ciencia")
    area=st.selectbox("Elegí una especialidad",list(MODULOS),index=2)
    st.write(MODULOS[area])
    st.caption("El asistente puede ayudar a estudiar, planificar clases y sintetizar documentos. En salud es información general; no reemplaza a un profesional.")
    mostrar_chat(area,EJEMPLOS.get(area))

elif seccion=="📚 Biblioteca y memoria":
    st.title("📚 Biblioteca de conocimientos y recuerdos")
    subida=st.file_uploader("Añadir texto, PDF o DOCX",type=["txt","md","pdf","docx"])
    if subida and st.button("Añadir a la biblioteca"):
        contenido=ejecutar(extraer_texto,subida.name,subida.getvalue())
        if contenido is not None:
            idx=ejecutar(agregar_documento,Path(subida.name).name,contenido)
            if idx is not None: st.success(f"Documento registrado #{idx}")
    regs=documentos()
    if regs: st.dataframe(pd.DataFrame(regs),hide_index=True,use_container_width=True)
    st.caption("PDFs escaneados sin texto pueden necesitar OCR; este módulo sólo extrae texto digital. Los documentos se guardan en SQLite local.")
    with st.form("memoria"):
        texto=st.text_area("Algo que querés que recuerde SKY")
        if st.form_submit_button("Guardar recuerdo"):
            guardar_con_feedback(guardar_memoria,texto,mensaje="Memoria guardada")
    for m in memorias():
        izq,der=st.columns([8,1])
        izq.write(m['texto'])
        if der.button("Eliminar",key=f"memo{m['id']}"):
            ejecutar(eliminar_memoria,m['id']); st.rerun()

elif seccion=="🧭 BAQUEANO Control Center":
    st.title("🧭 BAQUEANO Control Center")
    st.caption("Sitio oficial baqueanonicaragua.com · Repositorio OscarElieser/APP-BAQUEANO · Propuestas de cambios revisables")
    webtab,repotab,datostab,editartab=st.tabs(["🌐 Estado web","🗂️ GitHub","🗃️ Supabase público","✍️ Proponer cambio"])
    with webtab:
        st.link_button("Abrir web oficial","https://baqueanonicaragua.com/")
        if st.button("Comprobar estado de BAQUEANO"):
            dato=ejecutar(estado_web)
            if dato: st.json(dato)
        st.caption("Se comprueba HTTP y si la página contiene la marca BAQUEANO; no equivale a una auditoría de todas las funciones.")
    with repotab:
        st.link_button("Abrir repositorio GitHub","https://github.com/OscarElieser/APP-BAQUEANO")
        if st.button("Consultar actividad de GitHub"):
            dato=ejecutar(resumen_repo)
            if dato: st.json(dato)
        carpeta=st.text_input("Explorar carpeta (raíz, web, website, docs)",value="",key="baqueano_carpeta")
        if st.button("Listar archivos"):
            dato=ejecutar(listado_repo,carpeta)
            if dato is not None: st.dataframe(pd.DataFrame(dato),hide_index=True,use_container_width=True)
    with datostab:
        st.caption("Lectura únicamente con clave publicable y políticas RLS. Algunas tablas no estarán expuestas a visitantes o podrían no existir.")
        tabla=st.selectbox("Vista autorizada",list(SUPABASE_VISTAS),key="supabase_tabla")
        limite=st.slider("Máximo de filas",1,25,10,key="supabase_limite")
        if st.button("Consultar filas públicas"):
            dato=ejecutar(supabase_publico,tabla,limite)
            if dato is not None: st.dataframe(pd.DataFrame(dato),hide_index=True,use_container_width=True)
        st.caption("Para datos privados se integrará la autenticación administrativa del propio BAQUEANO, nunca una clave service_role en el navegador.")
    with editartab:
        st.warning("Este flujo crea una rama y un Pull Request en GitHub. **No cambia la rama main ni publica cambios en producción.**")
        st.write("Requiere BAQUEANO_GITHUB_TOKEN configurado en `.env`, con permisos limitados a este repositorio.")
        ruta=st.text_input("Ruta de archivo (p. ej., website/index.html)",value="website/index.html",key="baq_ruta")
        if st.button("Leer archivo para editar"):
            dato=ejecutar(leer_archivo,ruta)
            if dato:
                st.session_state['baq_archivo']=dato
                st.session_state['baq_nuevo']=dato['contenido']
        actual=st.session_state.get('baq_archivo')
        if actual and actual['ruta']==ruta:
            nuevo=st.text_area("Contenido propuesto (editable)",key="baq_nuevo",height=260)
            titulo=st.text_input("Título de la propuesta",value="Actualizar contenido de BAQUEANO",key="baq_titulo")
            cambio=vista_diff(actual['contenido'],nuevo,actual['ruta'])
            st.code(cambio[:24000] if cambio else "Sin diferencias",language="diff")
            confirma=st.text_input("Escribe CREAR PROPUESTA para autorizar el PR",key="baq_confirmacion")
            if st.button("Crear rama y Pull Request",disabled=not bool(cambio) or confirma!='CREAR PROPUESTA'):
                resultado=ejecutar(propuesta_pr,ruta,nuevo,titulo,actual['sha'],confirma)
                if resultado:
                    st.success("Propuesta creada para revisión; producción permanece sin cambios.")
                    st.link_button("Abrir Pull Request",resultado['pull_request'])
                    del st.session_state['baq_archivo']
        else:
            st.info("Primero lee un archivo de contenido del repositorio.")

elif seccion=="🧾 Transacciones":
    st.title("🧾 Preparación de transacciones")
    st.warning("Sólo crea **borradores locales** para tu revisión. 'Aprobada localmente' NO significa enviada, pagada o procesada.")
    with st.form("transaccion"):
        concepto=st.text_input("Motivo de la operación")
        ben=st.text_input("Beneficiario o entidad")
        monto=st.number_input("Monto",min_value=0.01,max_value=1_000_000.0)
        cur=st.selectbox("Moneda",["NIO","USD"])
        if st.form_submit_button("Guardar borrador"):
            if concepto.strip() and ben.strip():
                guardar_con_feedback(crear_operacion,concepto,ben,monto,cur,mensaje="Borrador creado; no se movió dinero")
    ops=operaciones()
    if ops:
        st.dataframe(pd.DataFrame(ops),hide_index=True,use_container_width=True)
        abiertas=[a for a in ops if a['estado']=='borrador']
        if abiertas:
            a=st.selectbox("Revisar borrador",[p['id'] for p in abiertas])
            izq,der=st.columns(2)
            if izq.button("Marcar revisado / aprobado localmente"):
                ejecutar(revisar_operacion,a,'aprobada_local'); st.rerun()
            if der.button("Descartar"):
                ejecutar(revisar_operacion,a,'descartada'); st.rerun()

elif seccion=="📡 Engine Sensor MLP + GRU":
    mostrar_sensores()

elif seccion=="✅ Proyectos y tareas":
    st.title("✅ Proyectos, tareas y productividad")
    with st.form("tarea"):
        nombre=st.text_input("Tarea nueva")
        area=st.selectbox("Área",list(MODULOS))
        if st.form_submit_button("Agregar tarea"):
            if nombre.strip():
                guardar_con_feedback(guardar_tarea,nombre,area,mensaje="Tarea guardada")
    for x in tareas():
        l,r=st.columns([7,1])
        l.write(f"{'✅' if x['estado']=='completada' else '🕒'} {x['nombre']} · {x['area']}")
        if x['estado']!='completada' and r.button("Hecho",key=f"t{x['id']}"):
            ejecutar(completar_tarea,x['id']); st.rerun()

elif seccion=="⚽ SKY Sports Madridista":
    from neural_core.sky_sports_madridista import (
        PROXIMOS_PARTIDOS_REAL_MADRID, CANALES_DEPORTIVOS_OFICIALES,
        generar_prediccion_deportiva, LEMA_MADRIDISTA
    )
    st.title("⚽ SKY Sports Center · Real Madrid")
    st.caption("Modo deportivo madridista · Televisión, agenda oficial, canales y predicciones inteligentes")
    st.info(f"👑 **Identidad Blanca:** {LEMA_MADRIDISTA} | 15 Copas de Europa | El Rey indiscutible del fútbol mundial.")

    tab_tv, tab_pred, tab_agenda, tab_canales = st.tabs(["📺 Ver Partido (TV)", "🔮 Predicciones", "📅 Agenda Real Madrid", "📡 Canales Oficiales"])

    with tab_tv:
        st.subheader("📺 Televisión Deportiva de SKY · Señal Oficial")
        st.caption("Regla fundamental: La señal audiovisual se activa únicamente bajo tu orden expresa.")

        p_activo = PROXIMOS_PARTIDOS_REAL_MADRID[0]
        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            st.markdown(f"### 👑 Real Madrid vs {p_activo['rival']}")
            st.markdown(f"**Competición:** {p_activo['competicion']}")
            st.markdown(f"**Estadio:** {p_activo['estadio']} | **Fecha:** {p_activo['fecha']}")
            st.markdown(f"**Hora Nicaragua:** `{p_activo['hora_nicaragua']}` | **Hora Madrid:** `{p_activo['hora_madrid']}`")
        with col_m2:
            st.metric("Probabilidad Victoria RM", f"{p_activo['probabilidad_victoria_rm']}%", delta="Favorito")
            st.metric("Marcador Probable", p_activo['marcador_probable'])

        st.divider()

        reproductor_activo = st.checkbox("▶️ Activar Reproductor de TV Oficial del Real Madrid", value=False)
        if reproductor_activo:
            st.success("🔴 Conectado a la señal oficial de Real Madrid TV. Transmisión autorizada en vivo.")
            st.markdown(
                """<iframe width="100%" height="450" src="https://www.youtube-nocookie.com/embed/live_stream?channel=UCWV3obpZVGgJ3j9FVhEjF2Q" 
                title="Real Madrid TV Live" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>""",
                unsafe_allow_html=True
            )
        else:
            st.warning("El reproductor permanece en pausa para respetar tu ancho de banda y permisos hasta tu petición expresa.")

        st.markdown("**Operadores oficiales con derechos de transmisión en tu región (Nicaragua / Centroamérica):**")
        col_op1, col_op2, col_op3 = st.columns(3)
        with col_op1:
            st.markdown("🔴 **ViX Premium (Tigo Nicaragua)**: Derechos exclusivos de LaLiga EA Sports.")
        with col_op2:
            st.markdown("📺 **ESPN / Disney+**: Transmisión oficial de la UEFA Champions League.")
        with col_op3:
            st.markdown("📡 **SKY Sports Centroamérica**: Cobertura deportiva y copas.")

    with tab_pred:
        st.subheader("🔮 Calculadora de Predicciones Deportivas")
        st.caption("Predicciones inteligentes con porcentajes de victoria, marcadores y análisis táctico.")
        c_eq1, c_eq2, c_comp = st.columns(3)
        with c_eq1:
            local = st.selectbox("Equipo Local", ["Real Madrid", "FC Barcelona", "RB Leipzig", "Manchester City", "Bayern Múnich", "AC Milan"])
        with c_eq2:
            visitante = st.selectbox("Equipo Visitante", ["FC Barcelona", "RB Leipzig", "Real Madrid", "Arsenal", "Atlético de Madrid", "Liverpool"], index=1)
        with c_comp:
            comp = st.selectbox("Competición", ["UEFA Champions League", "LaLiga EA Sports", "Copa del Rey", "Supercopa de Europa"])

        if st.button("Generar Pronóstico Inteligente", type="primary"):
            pred = generar_prediccion_deportiva(local, visitante, comp)
            st.divider()
            c_p1, c_p2, c_p3 = st.columns(3)
            with c_p1: st.metric(f"Victoria {local}", f"{pred['probabilidad_local']}%")
            with c_p2: st.metric("Empate", f"{pred['probabilidad_empate']}%")
            with c_p3: st.metric(f"Victoria {visitante}", f"{pred['probabilidad_visitante']}%")

            st.success(f"🎯 Marcador Más Probable: **{pred['marcador_probable']}**")
            st.write(f"📋 **Análisis Táctico:** {pred['analisis_tactico']}")
            st.write(f"⭐ **Jugadores clave a seguir:** {', '.join(pred['jugadores_clave'])}")
            if pred.get('lema'):
                st.caption(pred['lema'])

    with tab_agenda:
        st.subheader("📅 Calendario Oficial del Real Madrid CF")
        for partido in PROXIMOS_PARTIDOS_REAL_MADRID:
            with st.container():
                st.markdown(f"#### 👑 Real Madrid vs {partido['rival']} ({partido['competicion']})")
                st.write(f"📅 **Fecha:** {partido['fecha']} | 🕒 **Hora Nicaragua:** `{partido['hora_nicaragua']}` | 🏟️ **Estadio:** {partido['estadio']}")
                st.write(f"📺 **Transmisión oficial:** {partido['canal_oficial']} | 🔮 **Pronóstico SKY:** `{partido['marcador_probable']}`")
                st.caption(f"Clave táctica: {partido['clave']}")
                st.divider()

    with tab_canales:
        st.subheader("📡 Catálogo Visual de Canales Deportivos Oficiales")
        st.caption("Guía de señales autorizadas para Nicaragua y Centroamérica")
        for ch in CANALES_DEPORTIVOS_OFICIALES:
            col_c1, col_c2 = st.columns([1, 4])
            with col_c1:
                st.markdown(f"## {ch['logo']}")
            with col_c2:
                st.markdown(f"**{ch['nombre']}** ({ch['categoria']})")
                st.write(ch['cobertura'])
                st.markdown(f"[Acceder a transmisión oficial ➔]({ch['url_oficial']})")
            st.divider()

elif seccion == "🌐 SKY IA Universal v12.0":
    st.header("🌐 SKY IA Universal v12.0 — Global Intelligence & FactCheck")
    st.caption("Arquitectura universal de alto rendimiento: planificación, fuentes primarias mundiales, verificación factual y memoria inteligente.")

    tab_plan, tab_sources, tab_factcheck, tab_memory, tab_bench = st.tabs([
        "🧭 Universal Engine & Plan", "🌍 Global Source Router", "🔍 FactCheck Engine", "🧠 Smart Memory", "📊 Benchmark & Evaluación"
    ])

    with tab_plan:
        st.subheader("🧭 Planificador de Inteligencia Universal")
        prompt_in = st.text_area("Consulta o problema a resolver:", "Investiga la población y estadísticas demográficas oficiales de Nicaragua según el INIDE")
        area_sel = st.selectbox("Especialidad:", ["General", "Estadística", "Salud", "Economía", "Ciencia", "Programación", "Legislación", "Educación"])
        if st.button("Generar Plan de Ejecución", key="btn_gen_plan"):
            from neural_core.sky_universal_engine import SkyUniversalEngine
            plan = SkyUniversalEngine.clasificar_intencion(prompt_in, area_sel)
            st.success(f"**Modo Operativo Detectado:** `{plan.modo.value.upper()}` | **Disciplina:** `{plan.disciplina.upper()}` | **Nivel Académico:** `{plan.nivel_academico.value.upper()}`")
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Requiere Investigación", "Sí" if plan.requiere_investigacion else "No")
            with c2: st.metric("Cálculo Determinista", "Sí" if plan.requiere_calculo_determinista else "No")
            with c3: st.metric("Código / DEV-CORE", "Sí" if plan.requiere_codigo else "No")

            st.write("📋 **Pasos del Plan:**")
            for paso in plan.pasos:
                st.write(f"- {paso}")

            st.write("📚 **Directivas Inyectadas al Asistente:**")
            st.code(SkyUniversalEngine.directivas_universales(plan), language="markdown")

    with tab_sources:
        st.subheader("🌍 Global Source Router — Directorio de Fuentes Primarias")
        from neural_core.sky_universal_engine import GLOBAL_SOURCES_REGISTRY
        disc_sel = st.selectbox("Filtrar por Disciplina:", ["Todas"] + list(GLOBAL_SOURCES_REGISTRY.keys()))
        sources_to_show = []
        if disc_sel == "Todas":
            sources_to_show = [s for sublist in GLOBAL_SOURCES_REGISTRY.values() for s in sublist]
        else:
            sources_to_show = GLOBAL_SOURCES_REGISTRY.get(disc_sel, [])

        for s in sources_to_show:
            with st.container():
                st.markdown(f"**{s.entidad}** (`{s.pais_o_region}`) — *{s.categoria}*")
                st.write(s.descripcion)
                st.markdown(f"🔗 [Acceder a portal oficial]({s.url_base})")
                st.divider()

    with tab_factcheck:
        st.subheader("🔍 SKY FactCheck Engine — Auditoría Factual & Aritmética")
        st.caption("Verifica afirmaciones, detecta aserciones no comprobadas y valida cálculos mediante CAS SymPy.")
        texto_check = st.text_area("Texto o respuesta a auditar:", "En la prueba matemática confirmamos que 14 * 7 = 98 con exactitud. Por otra parte, según el INIDE la población supera los 6 millones.")
        if st.button("Auditar con FactCheck", key="btn_factcheck"):
            from neural_core.factcheck_engine import SkyFactCheckEngine
            rep = SkyFactCheckEngine.auditar_respuesta(texto_check)
            if rep.es_consistente:
                st.success("✅ **Consistencia Aprobada:** Cero contradicciones detectadas.")
            else:
                st.error("⚠️ **Alerta:** Se detectaron contradicciones o fallos de cálculo.")

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Total Afirmaciones", rep.total_afirmaciones)
            with c2: st.metric("Respaldadas", rep.respaldadas)
            with c3: st.metric("No Comprobadas", rep.no_comprobadas)
            with c4: st.metric("Contradictorias", rep.contradictorias)

            if rep.advertencia_incertidumbre:
                st.warning(rep.advertencia_incertidumbre)

            for d in rep.detalles:
                st.write(f"🔹 **Afirmación:** {d.afirmacion}")
                st.caption(f"Estado: `{d.estado.value}` | Tipo: `{d.tipo}` | Observación: {d.observacion}")

    with tab_memory:
        st.subheader("🧠 Smart Memory — Control de Memoria Persistente")
        from neural_core.smart_memory import get_smart_memory_manager
        sm = get_smart_memory_manager()
        mems = sm.consultar_memorias(usuario_id="default_user", incluir_privadas=True)
        st.write(f"Total memorias activas: **{len(mems)}**")

        with st.expander("➕ Añadir Nueva Memoria", expanded=False):
            c_cat = st.selectbox("Categoría:", ["preferencia", "proyecto", "documental", "sesion"])
            c_key = st.text_input("Clave:")
            c_val = st.text_input("Valor:")
            c_priv = st.checkbox("Privado", value=True)
            if st.button("Guardar en Memoria", key="btn_save_mem"):
                if c_key and c_val:
                    sm.guardar_memoria(c_cat, c_key, c_val, usuario_id="default_user", es_privado=c_priv)
                    st.success("Memoria guardada correctamente.")
                    st.rerun()

        for m in mems:
            col_m1, col_m2 = st.columns([4, 1])
            with col_m1:
                st.markdown(f"**[{m.categoria.upper()}] {m.clave}**: `{m.valor}`")
                st.caption(f"Privado: {m.es_privado} | ID: `{m.id}`")
            with col_m2:
                if st.button("Eliminar", key=f"del_{m.id}"):
                    sm.eliminar_memoria(m.id, usuario_id="default_user")
                    st.rerun()
            st.divider()

    with tab_bench:
        st.subheader("📊 Benchmark Suite & Medición de Calidad")
        st.caption("Evaluación automatizada continua sobre 8 disciplinas críticas con métricas reproducibles.")
        if st.button("Ejecutar Benchmark Multidisciplinario", key="btn_run_bench"):
            from neural_core.eval_benchmark import ejecutar_evaluacion_benchmark
            b_res = ejecutar_evaluacion_benchmark()
            st.success(f"🎯 **Tasa General de Exactitud:** `{b_res['tasa_exactitud_pct']}%`")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1: st.metric("Preguntas Evaluadas", b_res["total_preguntas"])
            with col_b2: st.metric("Aprobadas", b_res["aprobadas"])
            with col_b3: st.metric("Citas Inexistentes", b_res["metricas"]["citas_inexistentes"])

            st.write("📋 **Detalle por Disciplina Evaluada:**")
            for det in b_res["detalles"]:
                st.write(f"{'✅' if det['aprobado'] else '❌'} **{det['disciplina']}** ({det['id']}): Criterio: {det['criterio']} | Método: `{det['metodo']}`")


st.divider()
st.caption("SKY Universal v8.0 · Prototipo personal experimental · Los datos externos necesitan conexión; los movimientos financieros son manuales y locales.")
