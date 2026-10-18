"""Arquitectura híbrida MLP + GRU para datos temporales multivariantes."""
import torch
from torch import nn

COLUMNAS = ["temperatura_c", "vibracion_mm_s", "rpm", "corriente_a", "presion_bar"]
VENTANA = 24


class NeuralT(nn.Module):
    def __init__(self, entradas=len(COLUMNAS), ocultas=48):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(entradas, 32), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(32, 24), nn.ReLU(),
        )
        self.gru = nn.GRU(input_size=entradas, hidden_size=ocultas,
                          num_layers=1, batch_first=True)
        self.cabeza = nn.Sequential(
            nn.Linear(24 + ocultas, 48), nn.ReLU(),
            nn.Linear(48, entradas),
        )

    def forward(self, secuencia):
        ultimo = self.mlp(secuencia[:, -1, :])
        _, h = self.gru(secuencia)
        return self.cabeza(torch.cat((ultimo, h[-1]), dim=-1))
