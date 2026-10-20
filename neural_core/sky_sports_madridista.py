"""SKY Sports Center · Modo Deportivo Madridista (v1.0).

Módulo de inteligencia deportiva especializado en fútbol y seguidora del Real Madrid.
Funciones clave:
1. Predicciones inteligentes con porcentajes de victoria, marcadores probables y estadísticas.
2. Personalidad madridista apasionada («¡Hala Madrid y nada más! 🤍⚽») con análisis objetivo multideporte.
3. Agenda deportiva estilo Centro de TV y catálogo visual de canales oficiales (ViX, ESPN, SKY Sports, Real Madrid TV).
4. Activación del reproductor deportivo EXCLUSIVAMENTE por orden expresa del usuario.
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

LEMA_MADRIDISTA = "¡Hala Madrid y nada más! 🤍⚽"

# ==============================================================================
# 1. CALENDARIO OFICIAL Y METADATOS DEL REAL MADRID
# ==============================================================================
PROXIMOS_PARTIDOS_REAL_MADRID = [
    {
        "id": "rm-rbl-20261021",
        "competicion": "UEFA Champions League · Fase de Liga",
        "rival": "RB Leipzig",
        "local": False,
        "estadio": "Red Bull Arena (Leipzig)",
        "fecha": "2026-10-21",
        "hora_nicaragua": "13:00",
        "hora_madrid": "21:00",
        "canal_oficial": "ESPN / Disney+ / Star+",
        "estado": "programado",
        "en_vivo": False,
        "probabilidad_victoria_rm": 62.5,
        "probabilidad_empate": 21.0,
        "probabilidad_victoria_rival": 16.5,
        "marcador_probable": "1-3",
        "clave": "Contragolpe letal de Vinícius y desmarque de Mbappé ante bloque medio alemán."
    },
    {
        "id": "rm-fcb-20261025",
        "competicion": "LaLiga EA Sports · Jornada 11 (El Clásico)",
        "rival": "FC Barcelona",
        "local": True,
        "estadio": "Estadio Santiago Bernabéu (Madrid)",
        "fecha": "2026-10-25",
        "hora_nicaragua": "14:00",
        "hora_madrid": "22:00",
        "canal_oficial": "ViX Premium / Tigo Nicaragua / SKY Sports",
        "estado": "programado",
        "en_vivo": False,
        "probabilidad_victoria_rm": 56.0,
        "probabilidad_empate": 23.5,
        "probabilidad_victoria_rival": 20.5,
        "marcador_probable": "3-1",
        "clave": "Presión alta en el Bernabéu, control del mediocampo con Valverde y Bellingham, y solidez de Courtois."
    },
    {
        "id": "rm-val-20261102",
        "competicion": "LaLiga EA Sports · Jornada 12",
        "rival": "Valencia CF",
        "local": False,
        "estadio": "Mestalla (Valencia)",
        "fecha": "2026-11-02",
        "hora_nicaragua": "14:00",
        "hora_madrid": "21:00",
        "canal_oficial": "ViX Premium / SKY Sports",
        "estado": "programado",
        "en_vivo": False,
        "probabilidad_victoria_rm": 64.0,
        "probabilidad_empate": 22.0,
        "probabilidad_victoria_rival": 14.0,
        "marcador_probable": "0-2",
        "clave": "Control del ritmo de juego y evitar transiciones rápidas de Mestalla."
    },
    {
        "id": "rm-acm-20261105",
        "competicion": "UEFA Champions League · Clásico Europeo",
        "rival": "AC Milan",
        "local": True,
        "estadio": "Estadio Santiago Bernabéu (Madrid)",
        "fecha": "2026-11-05",
        "hora_nicaragua": "14:00",
        "hora_madrid": "21:00",
        "canal_oficial": "ESPN / Disney+",
        "estado": "programado",
        "en_vivo": False,
        "probabilidad_victoria_rm": 68.0,
        "probabilidad_empate": 19.0,
        "probabilidad_victoria_rival": 13.0,
        "marcador_probable": "3-1",
        "clave": "Duelo histórico de los dos máximos ganadores de Europa (15 vs 7 orejonas)."
    }
]

# ==============================================================================
# 2. GUÍA DE CANALES Y SEÑALES OFICIALES (CENTROAMÉRICA / NICARAGUA)
# ==============================================================================
CANALES_DEPORTIVOS_OFICIALES = [
    {
        "id": "rmtv",
        "nombre": "Real Madrid TV Oficial",
        "categoria": "Canal Oficial de Club",
        "logo": "⚪",
        "cobertura": "Señal en directo 24/7, previas, ruedas de prensa, cantera y análisis exclusivo",
        "tipo_acceso": "embed_oficial",
        "url_oficial": "https://www.realmadrid.com/es-ES/madridistas/real-madrid-tv",
        "embed_url": "https://www.youtube-nocookie.com/embed/live_stream?channel=UCWV3obpZVGgJ3j9FVhEjF2Q"
    },
    {
        "id": "vix",
        "nombre": "ViX Premium (Tigo Nicaragua)",
        "categoria": "Operador Oficial LaLiga",
        "logo": "🔴",
        "cobertura": "Transmisión exclusiva de todos los partidos de LaLiga EA Sports en Nicaragua",
        "tipo_acceso": "operador_oficial",
        "url_oficial": "https://vix.com/es-es/deportes"
    },
    {
        "id": "espn",
        "nombre": "ESPN / Disney+ / Star+",
        "categoria": "Operador Oficial UEFA Champions League",
        "logo": "📺",
        "cobertura": "Transmisión oficial de la UEFA Champions League para Centroamérica",
        "tipo_acceso": "operador_oficial",
        "url_oficial": "https://www.disneyplus.com"
    },
    {
        "id": "sky_sports",
        "nombre": "SKY Sports Centroamérica",
        "categoria": "Operador Televisivo Oficial",
        "logo": "📡",
        "cobertura": "Señales oficiales de fútbol europeo y torneos internacionales en Centroamérica",
        "tipo_acceso": "operador_oficial",
        "url_oficial": "https://www.sky.com.mx"
    },
    {
        "id": "dsports",
        "nombre": "DSports / DGO",
        "categoria": "Fútbol Continental",
        "logo": "⚡",
        "cobertura": "Señales deportivas continentales e internacionales",
        "tipo_acceso": "operador_oficial",
        "url_oficial": "https://www.directvgo.com"
    },
    {
        "id": "futbol_libre_hd",
        "nombre": "Fútbol Libre Full HD (Referencia Partidos Real Madrid)",
        "categoria": "Transmisiones y Señales En Vivo",
        "logo": "⚽",
        "cobertura": "Portal de referencia para ver partidos en directo del Real Madrid, Champions League y LaLiga EA Sports",
        "tipo_acceso": "referencia_directa",
        "url_oficial": "https://futbollibrefullhd.org/",
        "embed_url": "https://futbollibrefullhd.org/"
    }
]

# Aliases de conveniencia
CANALES_OFICIALES = CANALES_DEPORTIVOS_OFICIALES
AGENDA_REAL_MADRID = PROXIMOS_PARTIDOS_REAL_MADRID


# ==============================================================================
# 3. RECONOCIMIENTO DE ÓRDENES EXPRESAS PARA VER AL REAL MADRID
# ==============================================================================
PATRONES_VER_PARTIDO_MADRID = [
    r'mu[eé]strame\s+(?:el\s+)?partido\s+(?:en\s+vivo\s+)?(?:del\s+)?(?:real\s+)?madrid',
    r'ver\s+(?:el\s+)?partido\s+(?:en\s+vivo\s+)?(?:del\s+)?(?:real\s+)?madrid',
    r'partido\s+en\s+vivo\s+(?:del\s+)?(?:real\s+)?madrid',
    r'pon(?:er)?\s+(?:el\s+)?partido\s+(?:del\s+)?(?:real\s+)?madrid',
    r'ver\s+al\s+(?:real\s+)?madrid\s*(?:en\s+vivo)?',
    r'ver\s+(?:el\s+)?cl[aá]sico.*?(?:en\s+vivo)?',
    r'televisi[oó]n\s+(?:deportiva|madridista)',
    r'sky\s+sports\s+center'
]

def es_orden_ver_partido_madrid(texto: str) -> bool:
    """Detecta si el usuario solicita expresamente ver el partido del Real Madrid."""
    t = texto.strip().lower()
    for pat in PATRONES_VER_PARTIDO_MADRID:
        if re.search(pat, t, re.IGNORECASE):
            return True
    return False

def consultar_partido_actual_madrid() -> Dict[str, Any]:
    """Devuelve los datos del partido actual o más próximo del Real Madrid."""
    proximo = PROXIMOS_PARTIDOS_REAL_MADRID[0]
    return {
        "encontrado": True,
        "partido": proximo,
        "esta_en_vivo": proximo.get("en_vivo", False),
        "lema": LEMA_MADRIDISTA,
        "canales_disponibles": CANALES_DEPORTIVOS_OFICIALES,
        "canales_autorizados": CANALES_DEPORTIVOS_OFICIALES
    }

# ==============================================================================
# 4. MOTOR DE PREDICCIONES DEPORTIVAS INTELIGENTES
# ==============================================================================
def generar_prediccion_deportiva(
    equipo_local: str,
    equipo_visitante: str,
    competicion: str = "Fútbol Internacional"
) -> Dict[str, Any]:
    """Calcula probabilidades de victoria, resultado más probable y análisis táctico."""
    loc = equipo_local.strip()
    vis = equipo_visitante.strip()
    
    es_madrid_local = "madrid" in loc.lower()
    es_madrid_visitante = "madrid" in vis.lower()
    es_barca = any("barcelona" in e.lower() or "barça" in e.lower() for e in [loc, vis])
    es_champions = "champions" in competicion.lower()

    # Cálculo probabilístico ponderado
    if es_madrid_local:
        prob_local = 62.0 if not es_barca else 56.0
        if es_champions: prob_local += 6.0 # Mística de Champions en el Bernabéu
        prob_empate = 21.0
        prob_vis = round(100.0 - prob_local - prob_empate, 1)
        marcador = "3-1" if prob_local > 60 else "2-1"
        analisis_madrid = "El Santiago Bernabéu es un fortín histórico. Con la verticalidad de Mbappé, el desequilibrio de Vinícius Jr. y el liderazgo de Bellingham, el Madrid domina las transiciones ofensivas."
    elif es_madrid_visitante:
        prob_vis = 58.0 if not es_barca else 51.0
        if es_champions: prob_vis += 4.0
        prob_empate = 23.0
        prob_local = round(100.0 - prob_vis - prob_empate, 1)
        marcador = "1-2"
        analisis_madrid = "Como visitante, el Real Madrid aplica transiciones rápidas y solidez en repliegue con Valverde y Tchouaméni, aprovechando la velocidad punta en los últimos 30 metros."
    else:
        # Partido neutro / otros equipos
        prob_local = 46.0
        prob_empate = 28.0
        prob_vis = 26.0
        marcador = "1-1"
        analisis_madrid = "Análisis táctico neutral: Se prevé un duelo equilibrado en mediocampo, donde la efectividad en balones parados y el control de pérdidas definirán el desenlace."

    return {
        "partido": f"{loc} vs {vis}",
        "equipo_local": loc,
        "equipo_visitante": vis,
        "competicion": competicion,
        "probabilidad_local": prob_local,
        "probabilidad_empate": prob_empate,
        "probabilidad_visitante": prob_vis,
        "probabilidades": {
            "victoria_local_pct": prob_local,
            "victoria_visitante_pct": prob_vis,
            "empate_pct": prob_empate
        },
        "marcador_probable": marcador,
        "analisis_tactico": analisis_madrid,
        "jugadores_clave": ["Kylian Mbappé", "Vinícius Júnior", "Jude Bellingham", "Federico Valverde", "Thibaut Courtois"] if (es_madrid_local or es_madrid_visitante) else ["Goleador local", "Centrocampista creativo"],
        "lema": LEMA_MADRIDISTA if (es_madrid_local or es_madrid_visitante) else ""
    }


# ==============================================================================
# 5. PERSONALIDAD MADRIDISTA & DIRECTIVAS CONVERSACIONALES
# ==============================================================================
def es_tema_deportivo(area: str, prompt: str) -> bool:
    """Identifica si la solicitud involucra fútbol, Real Madrid o deportes."""
    combined = f"{area} {prompt}".lower()
    keywords = [
        "futbol", "fútbol", "real madrid", "madridista", "champions", "laliga",
        "bernabeu", "bernabéu", "clasico", "clásico", "barcelona", "mbappé", "mbappe",
        "vinicius", "vinícius", "bellingham", "partido", "gol", "prediccion deportiva",
        "pronostico", "pronóstico", "copa de europa", "leipzig", "deporte", "deportes"
    ]
    return any(k in combined for k in keywords)

def instrucciones_madridista(area: str, prompt: str) -> str:
    """Genera las instrucciones de personalidad deportiva y madridista para SKY."""
    if not es_tema_deportivo(area, prompt):
        return ""

    combined = f"{area} {prompt}".lower()
    es_madrid = any(w in combined for w in ["madrid", "blanco", "merengue", "bernabeu", "bernabéu", "champions", "clasico", "clásico", "hala madrid"])

    instrucciones = [
        "=== MODO DEPORTIVO SKY SPORTS CENTER ===",
        "Eres una analista deportiva de élite con pasión madridista inquebrantable.",
    ]

    if es_madrid:
        instrucciones.append(
            "✦ PERSONALIDAD MADRIDISTA ACTIVA:\n"
            "- Tu corazón es blanco: eres aficionada apasionada y orgullosa del Real Madrid (El Rey de Europa con 15 Orejonas, 15 Copas de Europa, 36 Ligas).\n"
            "- Conoces la historia dorada: Di Stéfano, Gento, Puskás, la Quinta del Buitre, las 3 Champions de Zidane, la 14ª de las remontadas y la Decimoquinta.\n"
            "- Celebras las victorias y goles con entusiasmo y energía, pero tus análisis tácticos son siempre rigurosos, analíticos y basados en datos reales.\n"
            f"- Cierra o saluda tus intervenciones madridistas con la frase lema: «{LEMA_MADRIDISTA}»."
        )
    else:
        instrucciones.append(
            "✦ OBJETIVIDAD MULTIDEPORTE CON IDENTIDAD MADRIDISTA:\n"
            f"- Tu identidad distintiva es ser aficionada del Real Madrid («{LEMA_MADRIDISTA}»), pero para otros clubes, selecciones u otros deportes (baloncesto, tenis, béisbol, F1), mantén imparcialidad absoluta, rigor estadístico y respeto profesional."
        )

    # Si solicita ver partido o pantalla deportiva
    if es_orden_ver_partido_madrid(prompt):
        instrucciones.append(
            "✦ ORDEN DE VER PARTIDO DETECTADA:\n"
            "- El usuario ha pedido expresamente ver el partido del Real Madrid.\n"
            "- Confirma con alegría madridista, enuncia el próximo partido oficial (RB Leipzig 21-Oct / Clásico 25-Oct) e informa que la pantalla oficial de SKY Sports Center ha sido desplegada con los operadores autorizados (ViX Premium, ESPN, SKY Sports y Real Madrid TV)."
        )

    return "\n".join(instrucciones)
