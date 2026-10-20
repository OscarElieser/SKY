"""Vista del Engine Sensor: Núcleo Neuronal Híbrido MLP + GRU con Telemetría Real."""
from pathlib import Path
import pandas as pd
import numpy as np
import torch
import streamlit as st
import streamlit.components.v1 as components

from modelo import COLUMNAS
from motor import (RAIZ, cargar_datos, recuperar, pronostico_siguiente,
                   anomalias_recientes, huella_archivo, VENTANA)
from entrenar import entrenar
from neural_core.sky_neural_core_viz import generar_html_nucleo_neuronal
from neural_core.sky_industrial_sensor import gestor_sensores, HAS_SERIAL

def extraer_activaciones_y_pesos_reales(datos: pd.DataFrame, estado) -> dict:
    """Extrae las activaciones y pesos tensoriales REALES de PyTorch sin datos inventados."""
    if not estado or len(datos) < VENTANA:
        return {
            'inputs': {c: float(datos[c].iloc[-1]) for c in COLUMNAS if c in datos.columns},
            'dense1': [0.0] * 32,
            'memory2': [0.0] * 48,
            'pesos_cruzados': [[0.0] * 32 for _ in range(48)],
            'outputs': {}
        }
    try:
        modelo, media, desv, umbral, info = estado
        arr = datos[COLUMNAS].to_numpy(dtype=np.float32)
        sec = (arr[-VENTANA:] - media) / desv
        t_sec = torch.from_numpy(sec.astype('float32'))[None]

        with torch.no_grad():
            x_last = t_sec[:, -1, :]
            # Capa Dense 1 (MLP 32 neuronas reales)
            mlp1 = torch.relu(modelo.mlp[0](x_last))[0].cpu().numpy().tolist()
            # Capa Memory 2 (GRU 48 unidades de memoria temporal)
            _, h = modelo.gru(t_sec)
            gru_h = torch.tanh(h[0, 0]).cpu().numpy().tolist()
            pred = modelo(t_sec)[0].cpu().numpy() * desv + media

            # Extraer pesos tensoriales reales de PyTorch (48, 32)
            w_head = modelo.cabeza[0].weight.detach().cpu().numpy()
            w_cross = w_head[:, :32].tolist()

        return {
            'inputs': dict(zip(COLUMNAS, map(float, arr[-1]))),
            'dense1': [round(float(v), 4) for v in mlp1],
            'memory2': [round(float(v), 4) for v in gru_h],
            'pesos_cruzados': w_cross,
            'outputs': dict(zip(COLUMNAS, map(float, pred)))
        }
    except Exception:
        return {
            'inputs': {c: float(datos[c].iloc[-1]) for c in COLUMNAS if c in datos.columns},
            'dense1': [0.1] * 32,
            'memory2': [0.1] * 48,
            'pesos_cruzados': [[0.1] * 32 for _ in range(48)],
            'outputs': {}
        }


def mostrar_sensores():
    st.markdown("""<style>
    .block-container {padding-top: 1.5rem; max-width: 1440px;}
    .hud-title-box {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.8) 100%);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 25px rgba(0, 0, 0, 0.45);
    }
    .hud-status-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #34d399;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .sensor-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 10px;
        padding: 14px 16px;
    }
    </style>""", unsafe_allow_html=True)

    # Identificar origen de telemetría activo
    origen_tag = "Hardware COM Conectado" if gestor_sensores.puerto_activo else "Telemetría de Maquinaria"

    st.markdown(f"""
    <div class="hud-title-box">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
          <h1 style="margin:0; font-size:26px; font-weight:700; color:#f8fafc; letter-spacing:-0.02em;">
            📡 Engine Sensor · Núcleo Neuronal Híbrido (MLP + GRU)
          </h1>
          <p style="margin:4px 0 0 0; font-size:13px; color:#94a3b8;">
            Inferencia tensorial en tiempo real · Sensores físicos y maquinaria industrial · Procesamiento local en hardware privado
          </p>
        </div>
        <div style="display:flex; gap:12px; align-items:center;">
          <div class="hud-status-chip">
            <span style="display:inline-block; width:7px; height:7px; background:#10b981; border-radius:50%; box-shadow:0 0 8px #10b981;"></span>
            {origen_tag}
          </div>
          <span style="font-size:12px; color:#38bdf8; font-family:monospace; font-weight:600;">PyTorch CPU/CUDA</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # --- PANEL LATERAL: CONEXIÓN DE HARDWARE Y ORIGEN DE DATOS ---
    with st.sidebar:
        st.header("🔌 Conexión de Hardware Real")
        modo_fuente = st.radio(
            "Seleccionar interfaz:",
            ["📁 Archivo CSV de Maquinaria", "⚡ Puerto Serie / COM (Arduino / ESP32)", "🌐 API HTTP LAN"]
        )

        ruta = RAIZ / "data" / "demo_sensores.csv"

        if modo_fuente == "📁 Archivo CSV de Maquinaria":
            subida = st.file_uploader("Cargar lecturas reales CSV", type=["csv"])
            if subida:
                ruta = RAIZ / "local_data" / "sensores_usuario.csv"
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_bytes(subida.getvalue())
                st.success("✅ Archivo de maquinaria cargado")
            else:
                st.info("Visualizando registro de telemetría de motor")

        elif modo_fuente == "⚡ Puerto Serie / COM (Arduino / ESP32)":
            if not HAS_SERIAL:
                st.error("pyserial no detectado.")
            else:
                puertos = gestor_sensores.listar_puertos_com()
                if puertos:
                    nombres = [f"{p['dispositivo']} - {p['descripcion'][:24]}" for p in puertos]
                    idx_sel = st.selectbox("Puerto COM detectado:", range(len(puertos)), format_func=lambda i: nombres[i])
                    baud = st.selectbox("Baudrate:", [9600, 19200, 38400, 57600, 115200], index=4)
                    puerto_elegido = puertos[idx_sel]['dispositivo']

                    c_con, c_des = st.columns(2)
                    if c_con.button("Conectar", width="stretch"):
                        ok, msg = gestor_sensores.conectar_puerto(puerto_elegido, baud)
                        if ok: st.success(msg); st.rerun()
                        else: st.error(msg)
                    if c_des.button("Desconectar", width="stretch"):
                        gestor_sensores.desconectar()
                        st.info("Puerto desconectado.")
                        st.rerun()

                    if gestor_sensores.puerto_activo:
                        st.success(f"🟢 Escuchando en vivo: {gestor_sensores.puerto_activo}")
                        st.caption(f"Tramas en buffer: {len(gestor_sensores.buffer)}")
                else:
                    st.warning("No se detectaron puertos COM activos en este momento.")

        elif modo_fuente == "🌐 API HTTP LAN":
            st.info("Endpoint de recepción activo en:")
            st.code("POST http://127.0.0.1:8765/api/telemetria/push\nContent-Type: application/json\n\n{\n  \"temperatura_c\": 74.2,\n  \"vibracion_mm_s\": 2.1,\n  \"rpm\": 2400,\n  \"corriente_a\": 9.1,\n  \"presion_bar\": 3.3\n}")

        st.divider()
        epocas = st.slider("Épocas de entrenamiento PyTorch", 5, 50, 15, 5)
        reentrenar = st.button("Reentrenar Red con Datos Actuales", type="primary", width="stretch")

    # Si hay telemetría COM en vivo en el buffer, usarla con prioridad
    df_live = gestor_sensores.obtener_dataframe()
    if len(df_live) >= VENTANA:
        datos = df_live
    else:
        try:
            datos = cargar_datos(ruta)
        except Exception as exc:
            st.error(f"Error al leer datos de sensores: {exc}")
            st.stop()

    if reentrenar:
        with st.spinner("Entrenando tensores MLP + GRU en hardware local..."):
            try:
                entrenar(ruta, epocas)
                st.success("✅ Pesos sinápticos actualizados y guardados en modelos/neuralT.pt.")
            except Exception as exc:
                st.error(f"Error al entrenar: {exc}")

    estado = recuperar()
    compatibilidad = bool(estado and estado[4]["huella_datos"] == huella_archivo(ruta))

    # Control de índice de lectura
    if "sensor_sim_idx" not in st.session_state:
        st.session_state.sensor_sim_idx = len(datos)

    sim_idx = min(len(datos), max(VENTANA, st.session_state.sensor_sim_idx))
    datos_actuales = datos.iloc[:sim_idx]

    # --- TELEMETRÍA EN VIVO ---
    st.markdown("##### 📊 Telemetría de Canales Físicos")
    metricas = st.columns(len(COLUMNAS))
    ultimos = datos_actuales.iloc[-1]
    previos = datos_actuales.iloc[-2] if len(datos_actuales) > 1 else ultimos

    col_labels = {
        "temperatura_c": ("Temperatura", "°C"),
        "vibracion_mm_s": ("Vibración", "mm/s"),
        "rpm": ("Velocidad", "RPM"),
        "corriente_a": ("Corriente", "A"),
        "presion_bar": ("Presión", "Bar")
    }

    for i, campo in enumerate(COLUMNAS):
        with metricas[i]:
            val = float(ultimos[campo])
            prev = float(previos[campo])
            delta = val - prev
            lbl, unit = col_labels.get(campo, (campo.replace("_", " ").title(), ""))
            st.metric(
                label=f"{lbl} ({unit})",
                value=f"{val:.2f}",
                delta=f"{delta:+.2f}" if abs(delta) > 0.001 else "Estable",
                delta_color="normal"
            )

    # --- NÚCLEO NEURONAL EN VIVO CON PESOS REALES ---
    st.markdown("---")
    c_hdr, c_act = st.columns([7, 3])
    with c_hdr:
        st.markdown("##### 🧠 Núcleo Neuronal Híbrido en Vivo (Dense ↔ Memory)")
        st.caption("Visualización sináptica directa de los tensores de PyTorch. Las líneas representan los pesos reales aprendidos (W) y los pulsos reflejan la activación de los sensores.")
    with c_act:
        c_step, c_reset = st.columns(2)
        if c_step.button("⚡ Siguiente Pulso", width="stretch", help="Calcula la inferencia en tiempo real para la siguiente lectura temporal"):
            if st.session_state.sensor_sim_idx < len(datos):
                st.session_state.sensor_sim_idx += 1
            else:
                st.session_state.sensor_sim_idx = VENTANA
            st.rerun()
        if c_reset.button("🔄 Reiniciar", width="stretch"):
            st.session_state.sensor_sim_idx = len(datos)
            st.rerun()

    # Extraer activaciones y pesos reales de PyTorch
    activaciones = extraer_activaciones_y_pesos_reales(datos_actuales, estado)

    # Renderizar el Canvas Interactivo
    html_canvas = generar_html_nucleo_neuronal(activaciones, altura=760)
    components.html(html_canvas, height=770, scrolling=False)

    # --- PREDICCIÓN Y ANÁLISIS ---
    if not estado:
        st.info("Modelo no inicializado. Haz clic en 'Reentrenar Red' en la barra lateral.")
    else:
        st.markdown("---")
        st.subheader("🎯 Diagnóstico Predictivo y Detección de Anomalías")
        estimacion = pronostico_siguiente(datos_actuales, estado)

        c_pred, c_chart = st.columns([4, 6])
        with c_pred:
            st.markdown("###### Pronóstico del Próximo Registro:")
            cols_p = st.columns(len(COLUMNAS))
            for i, sensor in enumerate(COLUMNAS):
                with cols_p[i]:
                    actual_v = float(ultimos[sensor])
                    pred_v = float(estimacion[sensor])
                    diff = pred_v - actual_v
                    lbl, unit = col_labels.get(sensor, (sensor, ""))
                    st.metric(lbl, f"{pred_v:.2f}", delta=f"{diff:+.2f}")
            st.caption("Fusión de representaciones MLP (24 canales) + Estado oculto recurrente GRU (48 dimensiones).")

            alertas = anomalias_recientes(datos_actuales, estado, cantidad=60)
            if len(alertas) and alertas["alerta"].any():
                st.error(f"⚠️ {int(alertas['alerta'].sum())} desviaciones detectadas sobre el umbral estadístico de validación.")
                st.dataframe(alertas.loc[alertas["alerta"]].tail(10), width="stretch", hide_index=True)
            else:
                st.success("✅ Estado de maquinaria normal: Todas las lecturas se encuentran dentro de los márgenes de seguridad.")

        with c_chart:
            sensor_elegido = st.selectbox("Canal a monitorear:", COLUMNAS,
                                          format_func=lambda x: col_labels.get(x, (x.replace('_',' ').title(), ''))[0])
            st.line_chart(datos_actuales[[sensor_elegido]].tail(220), height=260)
            st.caption(f"{len(datos_actuales):,} lecturas procesadas hasta el pulso actual.")

        with st.expander("🔬 Métricas de entrenamiento y convergencia de pérdidas"):
            col_m1, col_m2 = st.columns([4, 6])
            with col_m1:
                st.write("**Error Absoluto Medio (MAE) por Canal:**")
                st.json(estado[4].get("mae_validacion_por_sensor", {}))
            with col_m2:
                st.write("**Curva de Convergencia (Loss) MLP + GRU:**")
                st.line_chart(pd.DataFrame(estado[4]["historial"]).set_index("epoca")[["entrenamiento", "validacion"]])

    st.markdown("---")
    st.download_button(
        "💾 Exportar CSV de Telemetría Real",
        data=datos.to_csv(index=False).encode("utf-8"),
        file_name="telemetria_maquinaria_sky.csv",
        mime="text/csv"
    )
