"""API de telemetría y sensores físicos reales para SKY."""
from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/telemetria", tags=["Telemetria"])

class TelemetriaPayload(BaseModel):
    temperatura_c: float = Field(..., description="Temperatura en grados Celsius")
    vibracion_mm_s: float = Field(..., description="Vibración en mm/s")
    rpm: float = Field(..., description="Velocidad angular en RPM")
    corriente_a: float = Field(..., description="Consumo de corriente en Amperios")
    presion_bar: float = Field(..., description="Presión hidráulica/neumática en Bar")

@router.post("/push")
def recibir_telemetria(datos: TelemetriaPayload):
    """Recibe telemetría real transmitida por Arduino, ESP32, PLC o agentes IoT."""
    from neural_core.sky_industrial_sensor import gestor_sensores, LecturaSensor
    lectura = LecturaSensor(
        timestamp=datetime.now().isoformat(),
        temperatura_c=datos.temperatura_c,
        vibracion_mm_s=datos.vibracion_mm_s,
        rpm=datos.rpm,
        corriente_a=datos.corriente_a,
        presion_bar=datos.presion_bar
    )
    gestor_sensores.registrar_lectura(lectura)
    return {"status": "ok", "buffer_size": len(gestor_sensores.buffer), "registro": lectura.a_dict()}

@router.get("/latest")
def obtener_ultima_telemetria():
    """Devuelve la última lectura real recibida del hardware."""
    from neural_core.sky_industrial_sensor import gestor_sensores
    if not gestor_sensores.buffer:
        gestor_sensores._cargar_buffer_disco()
    if not gestor_sensores.buffer:
        return {"status": "empty", "lectura": None}
    return {"status": "ok", "lectura": gestor_sensores.buffer[-1].a_dict()}
