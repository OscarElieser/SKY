"""Gestor de telemetría y sensores industriales reales para SKY.

Soporta:
1. Lectura de puertos serie / COM (Arduino, ESP32, PLC RS-485, Modbus).
2. Detección automática de puertos COM físicos en Windows.
3. Ingestión de tramas JSON, CSV o pares clave-valor industriales.
4. Buffer en memoria y persistencia de telemetría de maquinaria real.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import threading
import time
from typing import List, Dict, Optional, Tuple

import pandas as pd
from modelo import COLUMNAS

try:
    import serial
    import serial.tools.list_ports as list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

BUFFER_FILE = Path(__file__).resolve().parent.parent / "local_data" / "telemetria_maquinaria_real.csv"

@dataclass
class LecturaSensor:
    timestamp: str
    temperatura_c: float
    vibracion_mm_s: float
    rpm: float
    corriente_a: float
    presion_bar: float

    def a_dict(self) -> Dict[str, float]:
        return {
            "temperatura_c": self.temperatura_c,
            "vibracion_mm_s": self.vibracion_mm_s,
            "rpm": self.rpm,
            "corriente_a": self.corriente_a,
            "presion_bar": self.presion_bar
        }

class GestorSensoresIndustriales:
    _instancia = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._inicializar()
            return cls._instancia

    def _inicializar(self):
        self.buffer: List[LecturaSensor] = []
        self.puerto_activo: Optional[str] = None
        self.baudrate: int = 115200
        self.hilo_lectura: Optional[threading.Thread] = None
        self.ejecutando: bool = False
        self.ultimo_error: str = ""
        self._cargar_buffer_disco()

    def _cargar_buffer_disco(self):
        BUFFER_FILE.parent.mkdir(parents=True, exist_ok=True)
        if BUFFER_FILE.exists():
            try:
                df = pd.read_csv(BUFFER_FILE)
                for _, row in df.tail(500).iterrows():
                    self.buffer.append(LecturaSensor(
                        timestamp=str(row.get("timestamp", datetime.now().isoformat())),
                        temperatura_c=float(row.get("temperatura_c", 0.0)),
                        vibracion_mm_s=float(row.get("vibracion_mm_s", 0.0)),
                        rpm=float(row.get("rpm", 0.0)),
                        corriente_a=float(row.get("corriente_a", 0.0)),
                        presion_bar=float(row.get("presion_bar", 0.0))
                    ))
            except Exception:
                pass

    def listar_puertos_com(self) -> List[Dict[str, str]]:
        """Lista todos los puertos COM disponibles en Windows."""
        if not HAS_SERIAL:
            return []
        try:
            puertos = []
            for p in list_ports.comports():
                puertos.append({
                    "dispositivo": p.device,
                    "descripcion": p.description or p.device,
                    "hwid": p.hwid or ""
                })
            return puertos
        except Exception:
            return []

    def registrar_lectura(self, lectura: LecturaSensor):
        """Registra una lectura real en el buffer y en el archivo CSV."""
        with self._lock:
            self.buffer.append(lectura)
            if len(self.buffer) > 2000:
                self.buffer.pop(0)

            # Persistir en CSV
            es_nuevo = not BUFFER_FILE.exists()
            with open(BUFFER_FILE, "a", encoding="utf-8") as f:
                if es_nuevo:
                    f.write("timestamp," + ",".join(COLUMNAS) + "\n")
                f.write(f"{lectura.timestamp},{lectura.temperatura_c:.3f},{lectura.vibracion_mm_s:.3f},{lectura.rpm:.2f},{lectura.corriente_a:.3f},{lectura.presion_bar:.3f}\n")

    def parsear_linea_trama(self, linea: str) -> Optional[LecturaSensor]:
        """Parsea una trama de sensor industrial (JSON, CSV o pares)."""
        linea = linea.strip()
        if not linea:
            return None

        ahora = datetime.now().isoformat()

        # Intentar JSON
        if linea.startswith("{") and linea.endswith("}"):
            try:
                obj = json.loads(linea)
                return LecturaSensor(
                    timestamp=ahora,
                    temperatura_c=float(obj.get("temperatura_c", obj.get("temp", obj.get("t", 0.0)))),
                    vibracion_mm_s=float(obj.get("vibracion_mm_s", obj.get("vib", obj.get("v", 0.0)))),
                    rpm=float(obj.get("rpm", obj.get("vel", 0.0))),
                    corriente_a=float(obj.get("corriente_a", obj.get("amp", obj.get("i", 0.0)))),
                    presion_bar=float(obj.get("presion_bar", obj.get("pres", obj.get("p", 0.0))))
                )
            except Exception:
                pass

        # Intentar CSV directo: 72.5, 2.1, 2300, 9.2, 3.4
        partes = [p.strip() for p in linea.split(",") if p.strip()]
        if len(partes) >= 5:
            try:
                nums = [float(p) for p in partes[:5]]
                return LecturaSensor(
                    timestamp=ahora,
                    temperatura_c=nums[0],
                    vibracion_mm_s=nums[1],
                    rpm=nums[2],
                    corriente_a=nums[3],
                    presion_bar=nums[4]
                )
            except ValueError:
                pass

        # Intentar pares clave=valor: T=72.5 V=2.1 RPM=2300 I=9.2 P=3.4
        valores = {}
        for token in linea.replace(";", " ").replace(",", " ").split():
            if "=" in token or ":" in token:
                k, v = token.replace(":", "=").split("=", 1)
                try:
                    valores[k.strip().lower()] = float(v.strip())
                except ValueError:
                    pass

        if valores:
            return LecturaSensor(
                timestamp=ahora,
                temperatura_c=valores.get("t", valores.get("temperatura", valores.get("temp", 70.0))),
                vibracion_mm_s=valores.get("v", valores.get("vibracion", valores.get("vib", 2.0))),
                rpm=valores.get("rpm", valores.get("velocidad", 2200.0)),
                corriente_a=valores.get("i", valores.get("a", valores.get("corriente", 9.0))),
                presion_bar=valores.get("p", valores.get("bar", valores.get("presion", 3.2)))
            )

        return None

    def conectar_puerto(self, nombre_puerto: str, baudrate: int = 115200) -> Tuple[bool, str]:
        """Conecta un puerto COM y arranca el hilo de escucha continua."""
        if not HAS_SERIAL:
            return False, "pyserial no está disponible."

        self.desconectar()
        try:
            ser = serial.Serial(nombre_puerto, baudrate=baudrate, timeout=1.0)
            self.puerto_activo = nombre_puerto
            self.baudrate = baudrate
            self.ejecutando = True

            def bucle_lectura():
                while self.ejecutando and ser.is_open:
                    try:
                        linea = ser.readline().decode("utf-8", errors="ignore")
                        lectura = self.parsear_linea_trama(linea)
                        if lectura:
                            self.registrar_lectura(lectura)
                    except Exception as exc:
                        self.ultimo_error = str(exc)
                        time.sleep(0.1)
                ser.close()

            self.hilo_lectura = threading.Thread(target=bucle_lectura, daemon=True)
            self.hilo_lectura.start()
            return True, f"Conectado a {nombre_puerto} a {baudrate} baudios."
        except Exception as exc:
            self.ultimo_error = str(exc)
            return False, f"Error al abrir {nombre_puerto}: {exc}"

    def desconectar(self):
        """Detiene la conexión serie activa."""
        self.ejecutando = False
        self.puerto_activo = None

    def obtener_dataframe(self) -> pd.DataFrame:
        """Devuelve las lecturas en formato DataFrame de Pandas."""
        with self._lock:
            if not self.buffer:
                return pd.DataFrame(columns=COLUMNAS)
            filas = [l.a_dict() for l in self.buffer]
            return pd.DataFrame(filas)

gestor_sensores = GestorSensoresIndustriales()
