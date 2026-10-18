"""Entrena el modelo desde CSV, siempre localmente. Uso: python entrenar.py --csv ruta.csv"""
import argparse
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from modelo import COLUMNAS, VENTANA, NeuralT
from motor import cargar_datos, crear_ventanas, huella_archivo, guardar


def entrenar(ruta, epocas=15):
    torch.manual_seed(14)
    np.random.seed(14)
    torch.set_num_threads(min(torch.get_num_threads(), 4))
    df = cargar_datos(ruta)
    datos = df[COLUMNAS].to_numpy(dtype=np.float32)
    corte = int(len(datos) * 0.8)
    media = datos[:corte].mean(axis=0)
    desv = datos[:corte].std(axis=0)
    desv[desv < 1e-6] = 1.0
    normales = (datos - media) / desv
    ix_entrena = np.arange(VENTANA, corte)
    ix_valida = np.arange(corte, len(datos))
    x_train, y_train = crear_ventanas(normales, ix_entrena)
    x_val, y_val = crear_ventanas(normales, ix_valida)
    loader = DataLoader(TensorDataset(x_train, y_train), batch_size=64, shuffle=True)
    net = NeuralT()
    optim = torch.optim.Adam(net.parameters(), lr=0.002)
    criterio = nn.SmoothL1Loss()
    mejor = float("inf")
    pesos_mejores = None
    historial = []
    for epoca in range(epocas):
        net.train()
        perdida = 0.0
        for x, y in loader:
            optim.zero_grad()
            pred = net(x)
            loss = criterio(pred, y)
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            optim.step()
            perdida += float(loss.detach()) * len(x)
        net.eval()
        with torch.no_grad():
            val = float(criterio(net(x_val), y_val))
        historial.append({"epoca": epoca + 1, "entrenamiento": round(perdida / len(x_train), 5),
                          "validacion": round(val, 5)})
        if val < mejor:
            mejor = val
            pesos_mejores = {k: v.detach().clone() for k, v in net.state_dict().items()}
    net.load_state_dict(pesos_mejores)
    net.eval()
    with torch.no_grad():
        pred = net(x_val).numpy() * desv + media
    observado = datos[ix_valida]
    residual = abs(pred - observado)
    mae = residual.mean(axis=0)
    umbrales = np.maximum(np.quantile(residual, 0.95, axis=0), 1e-5)
    info = {
        "nombre": "NeuralT Personal v1.0 — MLP + GRU Engine Sensor",
        "procedencia": str(Path(ruta).name),
        "huella_datos": huella_archivo(ruta),
        "registros": int(len(df)), "entrenamiento": int(len(ix_entrena)),
        "validacion": int(len(ix_valida)), "epocas": epocas,
        "mae_validacion_por_sensor": {c: round(float(v), 4) for c, v in zip(COLUMNAS, mae)},
        "historial": historial,
        "advertencia": "Uso experimental. No sustituye sensores certificados ni sistemas de seguridad.",
    }
    guardar(net, media, desv, umbrales, info)
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/demo_sensores.csv")
    parser.add_argument("--epocas", type=int, default=15)
    args = parser.parse_args()
    info = entrenar(args.csv, args.epocas)
    print("Modelo entrenado. Error absoluto medio de validación por sensor:")
    for sensor, error in info["mae_validacion_por_sensor"].items():
        print(f"  {sensor}: {error}")
