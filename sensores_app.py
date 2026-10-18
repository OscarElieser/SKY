"""Vista del Engine Sensor original, preservada como módulo."""
"""Panel web local de NeuralT Personal. Iniciar: streamlit run app.py"""
from pathlib import Path
import pandas as pd
import streamlit as st
from modelo import COLUMNAS
from motor import (RAIZ, cargar_datos, recuperar, pronostico_siguiente,
                   anomalias_recientes, huella_archivo)
from entrenar import entrenar

def mostrar_sensores():
    st.markdown("""<style>
    .block-container {padding-top: 2rem; max-width: 1400px;}
    h1 {letter-spacing: -.03em;}
    [data-testid='stMetric'] {background-color: rgba(127,127,127,.06); border-radius:12px; padding:13px;}
    </style>""", unsafe_allow_html=True)
    st.title("📡 Engine Sensor MLP + GRU")
    st.caption("Motor predictivo híbrido MLP + GRU · Engine Sensor · 100 % ejecución local")
    st.warning("PROTOTIPO EXPERIMENTAL. Los datos de demostración son sintéticos. No usar para control crítico, fallas reales o mantenimiento sin validación independiente.")

    with st.sidebar:
        st.header("Origen de datos")
        subida = st.file_uploader("Cargar sensores CSV", type=["csv"])
        if subida:
            ruta = RAIZ / "local_data" / "sensores_usuario.csv"
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(subida.getvalue())
            st.success("Archivo recibido localmente")
        else:
            ruta = RAIZ / "data" / "demo_sensores.csv"
            st.info("Usando lecturas sintéticas de demostración")
        st.divider()
        epocas = st.slider("Épocas de entrenamiento", 5, 50, 15, 5)
        reentrenar = st.button("Entrenar / actualizar IA", type="primary", use_container_width=True)
        st.caption("El entrenamiento y las predicciones se realizan en tu equipo.")

    try:
        datos = cargar_datos(ruta)
    except Exception as exc:
        st.error(f"No se puede leer el CSV: {exc}")
        st.stop()

    if reentrenar:
        with st.spinner("Entrenando MLP + GRU con tus lecturas..."):
            try:
                entrenar(ruta, epocas)
                st.success("Nuevo modelo entrenado y guardado correctamente.")
            except Exception as exc:
                st.error(f"Error al entrenar: {exc}")

    estado = recuperar()
    compatibilidad = bool(estado and estado[4]["huella_datos"] == huella_archivo(ruta))

    st.subheader("Lecturas del Engine Sensor")
    metricas = st.columns(len(COLUMNAS))
    for i, campo in enumerate(COLUMNAS):
        with metricas[i]:
            st.metric(campo.replace("_", " ").title(), f"{datos[campo].iloc[-1]:.2f}")

    sensor_elegido = st.selectbox("Visualizar sensor", COLUMNAS, format_func=lambda x: x.replace("_", " ").title())
    st.line_chart(datos[[sensor_elegido]].tail(220), height=285)
    st.caption(f"{len(datos):,} registros cargados; gráfico de las últimas 220 lecturas.")

    if not estado:
        st.info("Todavía no existe un modelo. Selecciona 'Entrenar / actualizar IA'.")
    elif not compatibilidad:
        st.warning("El modelo guardado corresponde a otro archivo. Entrena nuevamente con los datos actuales para evitar predicciones incompatibles.")
    else:
        st.divider()
        st.subheader("Predicción del próximo registro")
        estimacion = pronostico_siguiente(datos, estado)
        columnas_pred = st.columns(len(COLUMNAS))
        for i, sensor in enumerate(COLUMNAS):
            with columnas_pred[i]:
                st.metric(sensor.replace("_", " ").title(), f"{estimacion[sensor]:.2f}")
        st.caption("Pronóstico de un paso, no una garantía. El paso temporal coincide con el intervalo entre filas si el CSV tiene cadencia regular.")
        st.subheader("Detección exploratoria de anomalías")
        alertas = anomalias_recientes(datos, estado, cantidad=60)
        if len(alertas) and alertas["alerta"].any():
            st.error(f"{int(alertas['alerta'].sum())} registros con desviación superior al umbral estadístico de validación.")
            st.dataframe(alertas.loc[alertas["alerta"]].tail(20), use_container_width=True, hide_index=True)
        else:
            st.success("Ninguna desviación significativa detectada en las últimas 60 lecturas bajo los umbrales del modelo.")
        st.caption("Los umbrales se calculan a partir de los errores de validación; son experimentales, no límites físicos certificados.")
        with st.expander("Métricas de validación y entrenamiento"):
            st.write(estado[4]["mae_validacion_por_sensor"])
            st.line_chart(pd.DataFrame(estado[4]["historial"]).set_index("epoca")[["entrenamiento", "validacion"]])

    st.divider()
    st.subheader("Exportar los datos")
    st.download_button("Descargar CSV actual", data=datos.to_csv(index=False).encode("utf-8"),
                       file_name="sensores_neuralt.csv", mime="text/csv")
    st.caption("Privacidad: esta versión no incluye cuentas, llamadas externas, telemetría ni despliegue en la nube. La propia instalación de dependencias puede requerir Internet.")
