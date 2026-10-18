"""Carga, preparación y predicción local de sensores."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import torch
from modelo import COLUMNAS, VENTANA, NeuralT

RAIZ = Path(__file__).resolve().parent
DIR_MODELOS = RAIZ / "modelos"


def huella_archivo(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def cargar_datos(ruta):
    df = pd.read_csv(ruta)
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        raise ValueError("Faltan columnas: " + ", ".join(faltan))
    if len(df) < 100:
        raise ValueError("Se necesitan al menos 100 registros para entrenar.")
    for col in COLUMNAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if not np.isfinite(df[COLUMNAS].to_numpy(dtype=float)).all():
        raise ValueError("Los sensores deben contener números válidos, sin vacíos o infinitos.")
    return df


def crear_ventanas(valores, indices, longitud=VENTANA):
    x = np.stack([valores[i-longitud:i] for i in indices]).astype(np.float32)
    y = valores[indices].astype(np.float32)
    return torch.from_numpy(x), torch.from_numpy(y)


def guardar(modelo, media, desv, errores, info):
    DIR_MODELOS.mkdir(exist_ok=True, parents=True)
    torch.save({"pesos": modelo.state_dict(),
                "media": media.tolist(), "desv": desv.tolist(),
                "umbral_error": errores.tolist(), "info": info},
               DIR_MODELOS / "neuralT.pt")
    (DIR_MODELOS / "metricas.json").write_text(json.dumps(info, indent=2), encoding="utf-8")


def recuperar():
    archivo = DIR_MODELOS / "neuralT.pt"
    if not archivo.exists():
        return None
    datos = torch.load(archivo, map_location="cpu", weights_only=True)
    modelo = NeuralT()
    modelo.load_state_dict(datos["pesos"])
    modelo.eval()
    return modelo, np.array(datos["media"]), np.array(datos["desv"]), np.array(datos["umbral_error"]), datos["info"]


def pronostico_siguiente(df, estado):
    modelo, media, desv, umbral, info = estado
    datos = df[COLUMNAS].to_numpy(dtype=np.float32)
    sec = (datos[-VENTANA:] - media) / desv
    with torch.no_grad():
        pred = modelo(torch.from_numpy(sec.astype(np.float32))[None]).numpy()[0]
    retorno = pred * desv + media
    return dict(zip(COLUMNAS, map(float, retorno)))


def anomalias_recientes(df, estado, cantidad=30):
    """Marca desviaciones entre valor observado y predicción del paso anterior."""
    modelo, media, desv, umbral, info = estado
    datos = df[COLUMNAS].to_numpy(dtype=np.float32)
    base = max(VENTANA, len(datos) - cantidad)
    if base >= len(datos):
        return pd.DataFrame()
    indices = np.arange(base, len(datos))
    normalizado = (datos - media) / desv
    x, _ = crear_ventanas(normalizado, indices)
    with torch.no_grad():
        pred = modelo(x).numpy() * desv + media
    errores = abs(pred - datos[indices])
    resultado = pd.DataFrame({"registro": indices,
                              "alerta": np.any(errores > umbral, axis=1),
                              "sensores_fuera": [", ".join(np.array(COLUMNAS)[fila > umbral])
                                                for fila in errores]})
    return resultado
