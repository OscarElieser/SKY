"""Genera lecturas sintéticas: NO representan ningún motor real."""
from pathlib import Path
import numpy as np
import pandas as pd


def generar(ruta="data/demo_sensores.csv", n=1200):
    rng = np.random.default_rng(2026)
    t = np.arange(n)
    rpm = 2000 + 230 * np.sin(t / 31) + 60 * np.sin(t / 9) + rng.normal(0, 22, n)
    temperatura = 70 + (rpm - 2000) * 0.019 + 1.5 * np.sin(t / 71) + rng.normal(0, 0.65, n)
    vibracion = 2.1 + (rpm - 2000) * 0.001 + 0.25 * np.sin(t / 22) + rng.normal(0, 0.11, n)
    corriente = 8 + (rpm - 2000) * 0.004 + rng.normal(0, 0.18, n)
    presion = 3.2 + (rpm - 2000) * 0.0005 + rng.normal(0, 0.06, n)
    # Pocos eventos ficticios anómalos para demostrar alertas
    temperatura[1120:1125] += 12
    vibracion[1164:1168] += 2.2
    df = pd.DataFrame({
        "fecha_hora": pd.date_range("2026-09-01", periods=n, freq="min").astype(str),
        "temperatura_c": temperatura.round(3),
        "vibracion_mm_s": vibracion.round(3),
        "rpm": rpm.round(3),
        "corriente_a": corriente.round(3),
        "presion_bar": presion.round(3),
    })
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)
    return df

if __name__ == "__main__":
    generar()
    print("CSV de ejemplo generado.")
