"""Generadores locales de borradores. IA avanzada opcional vía Ollama."""
from textwrap import dedent

REDES={"TikTok": "vídeo vertical de 20-40 s", "Instagram": "Reel o carrusel",
       "Facebook": "publicación para comunidad", "YouTube": "Short o video largo",
       "X": "mensaje breve", "Threads": "conversación breve", "LinkedIn": "publicación profesional"}


def campana(nombre, publico, producto, precio, red, objetivo="captar clientes"):
    if red not in REDES:
        raise ValueError("Red no permitida")
    nombre = nombre.strip()[:100]
    producto = producto.strip()[:160]
    publico = publico.strip()[:140]
    objetivo = objetivo.strip()[:120]
    precio = precio.strip()[:70]
    if not nombre or not producto or not publico:
        raise ValueError("Faltan datos de la campaña")
    return dedent(f"""\
    CAMPAÑA · {nombre}
    Plataforma: {red} · Formato sugerido: {REDES[red]}
    Público: {publico}
    Producto/servicio: {producto}
    Precio: {precio or 'A cotizar'}
    Objetivo: {objetivo}

    GANCHO: ¿Buscás una solución para {producto.lower()}?
    PROPUESTA: Te ayudamos con {producto.lower()} mediante un servicio claro y personalizado.
    PRUEBA: Mostrar una demostración, un caso real verificable o un resultado medible.
    LLAMADO A LA ACCIÓN: Escribinos para recibir información y una cotización.

    GUIÓN: 0-3 s: problema visual; 3-12 s: solución en pantalla; 12-22 s: beneficio demostrable; 22-30 s: CTA.
    MÉTRICAS: visualizaciones, contactos reales, conversiones y ventas confirmadas.
    NOTA: borrador editable. No afirmar testimonios, premios ni garantías sin evidencia.
    """)


def produccion(tipo, idea, publico):
    tipo=tipo.strip()
    idea=idea.strip()[:500]
    publico=publico.strip()[:200]
    if not idea:
        raise ValueError("Describe la idea")
    return dedent(f"""\
    PLAN CREATIVO · {tipo.upper()}
    Tema: {idea}
    Público: {publico or 'General'}
    Estructura: apertura potente → desarrollo con evidencia y emoción → cierre con acción.
    Escenas: 1) presentación con plano general; 2) detalle/contexto; 3) conflicto o pregunta;
    4) demostración o giro; 5) resolución y mensaje final.
    Producción: audio autorizado y originales; usar imágenes, voz, música y videos con derechos de uso.
    Para generación directa de imágenes o videos hay que conectar un proveedor compatible; aquí se preparan los guiones.
    """)
