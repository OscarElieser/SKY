"""SKY FactCheck Engine (v12.0).

Motor de verificación factual rigurosa, contraste de evidencia,
auditoría de citas y validación determinista de cálculos.

Estados de Verificación Factual:
- RESPALDADA: afirmación corroborada por fuentes primarias u oficiales.
- CONTRADICTORIA: la evidencia desmiente la afirmación.
- NO_COMPROBADA: no hay suficiente evidencia empírica u oficial; requiere advertencia explícita.
- DESACTUALIZADA: el dato fue válido pero ha sido superado por publicaciones o censos más recientes.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from neural_core.math_engine import math_cas_evaluate


class VerificationStatus(str, Enum):
    RESPALDADA = "respaldada"
    CONTRADICTORIA = "contradictoria"
    NO_COMPROBADA = "no_comprobada"
    DESACTUALIZADA = "desactualizada"


@dataclass
class FactualClaim:
    afirmacion: str
    tipo: str # "numerica", "fecha", "cita", "conceptual"
    estado: VerificationStatus
    fuente_corroborante: Optional[str] = None
    observacion: str = ""


@dataclass
class FactCheckReport:
    total_afirmaciones: int
    respaldadas: int
    contradictorias: int
    no_comprobadas: int
    desactualizadas: int
    es_consistente: bool
    calculos_verificados: List[Dict[str, Any]]
    detalles: List[FactualClaim]
    advertencia_incertidumbre: Optional[str] = None


class SkyFactCheckEngine:
    """Motor de verificación factual y detección de afirmaciones no corroboradas."""

    # Detección de patrones de afirmaciones factuales (cifras, años, porcentajes, citas)
    PATRON_ANIO = re.compile(r'\b(19\d{2}|20\d{2})\b')
    PATRON_PORCENTAJE = re.compile(r'\b\d+(?:\.\d+)?\s*%')
    PATRON_CITA = re.compile(r'«([^»]+)»|"([^"]+)"')
    PATRON_CALCULO = re.compile(r'(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)\s*=\s*(\d+(?:\.\d+)?)')

    @classmethod
    def extraer_afirmaciones(cls, texto: str) -> List[FactualClaim]:
        """Extrae aserciones verificables de un texto."""
        claims: List[FactualClaim] = []
        oraciones = [s.strip() for s in re.split(r'[\.\n]+', texto) if len(s.strip()) > 15]

        for s in oraciones:
            # 1. Comprobación de cálculos explícitos
            m_calc = cls.PATRON_CALCULO.search(s)
            if m_calc:
                n1, op, n2, res_esperado = m_calc.groups()
                expr = f"{n1}{op}{n2}"
                cas_res = math_cas_evaluate(expr)
                if cas_res.get("ok"):
                    val_exacto = cas_res.get("resultado_exacto")
                    try:
                        es_correcto = (abs(float(val_exacto) - float(res_esperado)) < 1e-4)
                    except (ValueError, TypeError):
                        es_correcto = (str(val_exacto).strip() == str(res_esperado).strip())
                    
                    estado = VerificationStatus.RESPALDADA if es_correcto else VerificationStatus.CONTRADICTORIA
                    obs = f"Cálculo validado vía CAS SymPy: {expr} = {val_exacto} (afirmado: {res_esperado})"
                    claims.append(FactualClaim(s, "calculo", estado, "SymPy CAS Kernel", obs))
                    continue

            # 2. Aserciones numéricas o porcentuales.
            # IMPORTANTE: mencionar OMS, UNESCO, INIDE, NASA, etc. no demuestra
            # que ese organismo publicó el dato. Un enlace o lista de fuentes
            # tampoco prueba por sí solo la afirmación: hace falta cotejar
            # evidencia concreta, fechada y atribuible al documento original.
            if cls.PATRON_PORCENTAJE.search(s) or any(c.isdigit() for c in s):
                claims.append(FactualClaim(
                    s, "numerica", VerificationStatus.NO_COMPROBADA, None,
                    "Dato numérico sin cotejo de evidencia primaria; nombrar una institución no lo verifica."
                ))
                continue

            # 3. Citas textuales
            if cls.PATRON_CITA.search(s):
                claims.append(FactualClaim(s, "cita", VerificationStatus.NO_COMPROBADA, None, "Cita textual pendiente de cotejo contra documento original"))

        return claims

    @classmethod
    def auditar_respuesta(cls, texto: str, fuentes_disponibles: Optional[List[str]] = None) -> FactCheckReport:
        """Audita una respuesta completa generando un informe de exactitud factual."""
        claims = cls.extraer_afirmaciones(texto)
        
        respaldadas = sum(1 for c in claims if c.estado == VerificationStatus.RESPALDADA)
        contradictorias = sum(1 for c in claims if c.estado == VerificationStatus.CONTRADICTORIA)
        no_comprobadas = sum(1 for c in claims if c.estado == VerificationStatus.NO_COMPROBADA)
        desactualizadas = sum(1 for c in claims if c.estado == VerificationStatus.DESACTUALIZADA)

        es_consistente = (contradictorias == 0)

        advertencia = None
        if no_comprobadas > 0:
            advertencia = (
                f"Se detectaron {no_comprobadas} afirmación(es) o cifras sin fuente primaria directa cotejada. "
                "Se recomienda verificar en repositorios oficiales antes de su uso decisional."
            )
        if contradictorias > 0:
            advertencia = (
                f"¡ALERTA CRÍTICA!: Se detectaron {contradictorias} contradicción(es) o errores de cálculo aritmético."
            )

        # Extraer cálculos verificados
        calculos = [
            {"afirmacion": c.afirmacion, "observacion": c.observacion, "valido": (c.estado == VerificationStatus.RESPALDADA)}
            for c in claims if c.tipo == "calculo"
        ]

        return FactCheckReport(
            total_afirmaciones=len(claims),
            respaldadas=respaldadas,
            contradictorias=contradictorias,
            no_comprobadas=no_comprobadas,
            desactualizadas=desactualizadas,
            es_consistente=es_consistente,
            calculos_verificados=calculos,
            detalles=claims,
            advertencia_incertidumbre=advertencia
        )
