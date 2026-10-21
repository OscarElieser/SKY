"""
SKY-IA — Interfaz Holográfica 3D (Holographic Core Interface)
Diseño Cinematográfico con Núcleo Central Tridimensional y Ventanas Holográficas Inteligentes.
Inspirado en interfaces holográficas futuristas, con autoría conceptual de Oscar Elieser Chamorro Guzmán.
"""

from typing import Dict, Any, List, Optional
import json
import datetime


def generate_holographic_scene_html(
    voice_state: str = "ESPERANDO_ACTIVACION",
    active_player_track: Optional[str] = None,
    active_player_artist: Optional[str] = None,
    is_playing_music: bool = False,
    interaction_mode: str = "MODO_A",
    height: int = 580
) -> str:
    """Genera el documento HTML/Three.js del Núcleo Holográfico 3D interactivo."""

    # Mapeo de estados del coordinador de voz y eventos del backend a visuales
    state_display_map = {
        # Formatos en español internos
        "ESPERANDO_ACTIVACION": ("En espera", "#00f2ff", "slow"),
        "ESCUCHANDO": ("Escuchando...", "#00ffaa", "pulse"),
        "PROCESANDO": ("Procesando...", "#00c8ff", "fast"),
        "RESPONDIENDO": ("Respondiendo...", "#ffffff", "waves"),
        "EJECUTANDO_HERRAMIENTA": ("Ejecutando...", "#ffaa00", "fast"),
        "ESPERANDO_SIGUIENTE_INTERVENCION": ("Te escucho...", "#00ffaa", "pulse"),
        "PAUSADO": ("Pausado", "#888888", "idle"),
        # Formatos estándar backend (IDLE, LISTENING, THINKING, SPEAKING, EXECUTING, SUCCESS, ERROR)
        "IDLE": ("En espera", "#00f2ff", "slow"),
        "LISTENING": ("Escuchando...", "#00ffaa", "pulse"),
        "THINKING": ("Pensando...", "#00c8ff", "fast"),
        "SPEAKING": ("Hablando...", "#ffffff", "waves"),
        "EXECUTING": ("Ejecutando...", "#ffaa00", "fast"),
        "SUCCESS": ("Acción verificada", "#00ff88", "pulse"),
        "ERROR": ("Atención requerida", "#ff3366", "shake"),
    }

    norm_state = str(voice_state or "").strip().upper()
    state_text, state_color, state_anim = state_display_map.get(
        norm_state, ("Listo", "#00f2ff", "slow")
    )
    now_str = datetime.datetime.now().strftime("%H:%M")
    track_title = active_player_track or "SKY-IA Audio Engine"
    track_artist = active_player_artist or "SKY-IA Universal"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: transparent;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      user-select: none;
      color: #e0f2fe;
    }}
    #hologram-viewport {{
      position: relative;
      width: 100%;
      height: {height}px;
      border-radius: 20px;
      overflow: hidden;
      background: radial-gradient(circle at 50% 40%, #031528 0%, #020b16 48%, #010408 92%);
      border: 1px solid rgba(0, 242, 255, 0.35);
      box-shadow: 0 0 50px rgba(0, 242, 255, 0.25), inset 0 0 60px rgba(0, 242, 255, 0.1);
    }}

    /* Marco de cabina espacial / Observatory frame */
    .cockpit-frame-top {{
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 36px;
      background: linear-gradient(180deg, rgba(8, 24, 48, 0.85) 0%, rgba(4, 12, 24, 0.2) 80%, transparent 100%);
      border-bottom: 1px solid rgba(0, 242, 255, 0.2);
      pointer-events: none;
      z-index: 10;
    }}
    .cockpit-frame-bottom {{
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 48px;
      background: linear-gradient(0deg, rgba(6, 18, 36, 0.95) 0%, rgba(3, 9, 20, 0.4) 75%, transparent 100%);
      border-top: 1px solid rgba(0, 242, 255, 0.25);
      pointer-events: none;
      z-index: 10;
    }}

    /* Header superior: Logo a la izquierda */
    .holo-header-left {{
      position: absolute;
      top: 18px;
      left: 28px;
      display: flex;
      align-items: center;
      gap: 14px;
      z-index: 20;
    }}
    .logo-ring {{
      width: 44px;
      height: 44px;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .logo-ring svg {{
      width: 100%;
      height: 100%;
      filter: drop-shadow(0 0 8px #00f2ff);
    }}
    .logo-brand {{
      display: flex;
      flex-direction: column;
    }}
    .brand-name {{
      font-family: 'Orbitron', -apple-system, sans-serif;
      font-size: 21px;
      font-weight: 900;
      letter-spacing: 3px;
      color: #ffffff;
      text-shadow: 0 0 16px rgba(0, 242, 255, 0.9), 0 0 30px rgba(0, 168, 255, 0.5);
    }}
    .brand-subtitle {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 4px;
      color: #7dd3fc;
      text-transform: uppercase;
      opacity: 0.9;
    }}

    /* Header superior: Estado de voz a la derecha */
    .holo-header-right {{
      position: absolute;
      top: 18px;
      right: 28px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 12px;
      z-index: 20;
    }}
    .status-capsule {{
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(6, 20, 38, 0.82);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      border: 1px solid rgba(0, 242, 255, 0.4);
      border-radius: 30px;
      padding: 7px 18px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6), 0 0 18px rgba(0, 242, 255, 0.25);
    }}
    .wave-icon {{
      display: flex;
      align-items: center;
      gap: 2.5px;
      height: 16px;
    }}
    .wave-bar {{
      width: 2.5px;
      background: #00f2ff;
      border-radius: 2px;
      box-shadow: 0 0 6px #00f2ff;
      animation: soundWave 1.2s infinite ease-in-out;
    }}
    .wave-bar:nth-child(1) {{ height: 6px; animation-delay: 0.1s; }}
    .wave-bar:nth-child(2) {{ height: 14px; animation-delay: 0.3s; }}
    .wave-bar:nth-child(3) {{ height: 9px; animation-delay: 0.15s; }}
    .wave-bar:nth-child(4) {{ height: 16px; animation-delay: 0.4s; }}
    .wave-bar:nth-child(5) {{ height: 8px; animation-delay: 0.2s; }}

    @keyframes soundWave {{
      0%, 100% {{ transform: scaleY(0.4); }}
      50% {{ transform: scaleY(1.3); }}
    }}

    .status-label {{
      font-family: 'Courier New', monospace;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 1.5px;
      color: {state_color};
      text-shadow: 0 0 10px {state_color};
    }}
    .status-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: {state_color};
      box-shadow: 0 0 12px {state_color};
      animation: blinkDot 1.6s infinite;
    }}
    .clock-tag {{
      font-family: 'Courier New', monospace;
      font-size: 13px;
      font-weight: 700;
      color: #94a3b8;
      letter-spacing: 1px;
      border-left: 1px solid rgba(255, 255, 255, 0.15);
      padding-left: 10px;
    }}

    @keyframes blinkDot {{
      0%, 100% {{ opacity: 0.4; transform: scale(0.9); }}
      50% {{ opacity: 1.0; transform: scale(1.3); box-shadow: 0 0 16px {state_color}; }}
    }}

    /* Widget flotante de música (Esquina superior derecha) */
    .music-widget-card {{
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(5, 18, 36, 0.78);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(0, 242, 255, 0.32);
      border-radius: 16px;
      padding: 9px 16px;
      box-shadow: 0 6px 25px rgba(0,0,0,0.7), 0 0 18px rgba(0, 242, 255, 0.18);
      transition: all 0.3s ease;
    }}
    .music-widget-card:hover {{
      border-color: #00f2ff;
      box-shadow: 0 0 25px rgba(0, 242, 255, 0.35);
    }}
    .music-art {{
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: radial-gradient(circle, #00d4ff 0%, #032147 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 10px rgba(0, 242, 255, 0.4);
      font-size: 16px;
    }}
    .music-meta {{
      display: flex;
      flex-direction: column;
    }}
    .music-title {{
      font-size: 12px;
      font-weight: 700;
      color: #e0f2fe;
      letter-spacing: 0.5px;
      max-width: 140px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .music-artist {{
      font-size: 10px;
      color: #7dd3fc;
      letter-spacing: 1px;
    }}
    .music-controls {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-left: 6px;
    }}
    .music-btn {{
      background: transparent;
      border: none;
      color: #38bdf8;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
    }}
    .music-btn:hover {{
      color: #00f2ff;
      transform: scale(1.15);
      filter: drop-shadow(0 0 6px #00f2ff);
    }}

    canvas {{
      display: block;
      width: 100%;
      height: 100%;
    }}
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
  <div id="hologram-viewport">
    <div class="cockpit-frame-top"></div>

    <!-- Header Izquierdo: Logotipo SKY-IA -->
    <div class="holo-header-left">
      <div class="logo-ring">
        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="50" cy="50" r="38" stroke="#00f2ff" stroke-width="4" stroke-dasharray="14 6" opacity="0.85"/>
          <ellipse cx="50" cy="50" rx="46" ry="18" transform="rotate(-30 50 50)" stroke="#38bdf8" stroke-width="3" opacity="0.9"/>
          <path d="M50 26 L68 64 L50 55 L32 64 Z" fill="none" stroke="#00f2ff" stroke-width="3.5" stroke-linejoin="round"/>
          <circle cx="50" cy="50" r="4" fill="#ffffff" filter="drop-shadow(0 0 6px #00f2ff)"/>
        </svg>
      </div>
      <div class="logo-brand">
        <span class="brand-name">SKY-IA</span>
        <span class="brand-subtitle">IA UNIVERSAL</span>
      </div>
    </div>

    <!-- Header Derecho: Estado de Voz y Conexión -->
    <div class="holo-header-right">
      <div class="status-capsule">
        <div class="wave-icon">
          <span class="wave-bar"></span>
          <span class="wave-bar"></span>
          <span class="wave-bar"></span>
          <span class="wave-bar"></span>
          <span class="wave-bar"></span>
        </div>
        <span class="status-label">{state_text}</span>
        <span class="status-dot"></span>
        <span class="clock-tag">{now_str}</span>
      </div>

      <!-- Mini-tarjeta musical holográfica -->
      <div class="music-widget-card">
        <div class="music-art">🎵</div>
        <div class="music-meta">
          <span class="music-title">{track_title}</span>
          <span class="music-artist">{track_artist}</span>
        </div>
        <div class="music-controls">
          <button class="music-btn" title="Anterior">⏮</button>
          <button class="music-btn" title="Reproducir/Pausar" style="font-size: 15px; color: #00f2ff;">⏸</button>
          <button class="music-btn" title="Siguiente">⏭</button>
        </div>
      </div>
    </div>

    <canvas id="core-canvas"></canvas>
    <div class="cockpit-frame-bottom"></div>
  </div>

  <script>
    const container = document.getElementById('hologram-viewport');
    const canvas = document.getElementById('core-canvas');
    const width = container.clientWidth || 900;
    const height = container.clientHeight || {height};

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x010712, 0.028);

    const camera = new THREE.PerspectiveCamera(46, width / height, 0.1, 1000);
    camera.position.set(0, 0.2, 11.2);

    const renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true, alpha: true }});
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    // Luces
    const ambientLight = new THREE.AmbientLight(0x08223d, 1.4);
    scene.add(ambientLight);

    const coreLight = new THREE.PointLight(0x00f2ff, 5.0, 28);
    coreLight.position.set(0, 0.2, 0);
    scene.add(coreLight);

    const topLight = new THREE.DirectionalLight(0x38bdf8, 2.2);
    topLight.position.set(0, 10, 5);
    scene.add(topLight);

    const bottomFloorLight = new THREE.PointLight(0x00d4ff, 3.5, 15);
    bottomFloorLight.position.set(0, -3.2, 0);
    scene.add(bottomFloorLight);

    // GRUPO RAÍZ DEL NÚCLEO 3D
    const coreGroup = new THREE.Group();
    scene.add(coreGroup);

    // 1. ESFERA ENERGÉTICA CENTRAL
    const coreSphereGeo = new THREE.SphereGeometry(1.65, 48, 48);
    const coreSphereMat = new THREE.MeshStandardMaterial({{
      color: 0x00c8ff,
      emissive: 0x00a8ff,
      emissiveIntensity: 2.2,
      roughness: 0.18,
      metalness: 0.82,
      transparent: true,
      opacity: 0.88
    }});
    const centralSphere = new THREE.Mesh(coreSphereGeo, coreSphereMat);
    coreGroup.add(centralSphere);

    // Capa wireframe de cuadrícula neuronal en la esfera
    const neuralGridGeo = new THREE.SphereGeometry(1.72, 24, 24);
    const neuralGridMat = new THREE.MeshBasicMaterial({{
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.35
    }});
    const neuralGrid = new THREE.Mesh(neuralGridGeo, neuralGridMat);
    coreGroup.add(neuralGrid);

    // 2. GLIFO DELTA HOLOGRÁFICO EN EL CENTRO EXACTO (Símbolo de SKY-IA)
    const deltaGroup = new THREE.Group();
    const deltaPoints = [
      new THREE.Vector3(0, 0.95, 0.2),
      new THREE.Vector3(0.8, -0.65, 0.2),
      new THREE.Vector3(0.25, -0.4, 0.2),
      new THREE.Vector3(0, 0.15, 0.2),
      new THREE.Vector3(-0.25, -0.4, 0.2),
      new THREE.Vector3(-0.8, -0.65, 0.2),
      new THREE.Vector3(0, 0.95, 0.2)
    ];
    const deltaGeo = new THREE.BufferGeometry().setFromPoints(deltaPoints);
    const deltaMat = new THREE.LineBasicMaterial({{
      color: 0xffffff,
      linewidth: 3,
      transparent: true,
      opacity: 0.95
    }});
    const deltaLine = new THREE.Line(deltaGeo, deltaMat);
    deltaGroup.add(deltaLine);

    // Segundo delta posterior para efecto holográfico 3D
    const deltaBackPoints = deltaPoints.map(p => new THREE.Vector3(p.x * 0.9, p.y * 0.9, -0.2));
    const deltaBackGeo = new THREE.BufferGeometry().setFromPoints(deltaBackPoints);
    const deltaBackMat = new THREE.LineBasicMaterial({{ color: 0x00f2ff, linewidth: 2, transparent: true, opacity: 0.6 }});
    const deltaBackLine = new THREE.Line(deltaBackGeo, deltaBackMat);
    deltaGroup.add(deltaBackLine);

    coreGroup.add(deltaGroup);

    // 3. ANILLOS ORBITALES INCLINADOS CON NODOS DE ENERGÍA
    const ringsGroup = new THREE.Group();
    coreGroup.add(ringsGroup);

    function createOrbitalRing(radius, tube, rotX, rotY, rotZ, color, emissive) {{
      const geo = new THREE.TorusGeometry(radius, tube, 16, 128);
      const mat = new THREE.MeshStandardMaterial({{
        color: color,
        emissive: emissive,
        emissiveIntensity: 2.8,
        transparent: true,
        opacity: 0.85
      }});
      const ring = new THREE.Mesh(geo, mat);
      ring.rotation.set(rotX, rotY, rotZ);
      return ring;
    }}

    const ringA = createOrbitalRing(3.1, 0.022, Math.PI / 3.2, Math.PI / 5, 0, 0x00f2ff, 0x00f2ff);
    const ringB = createOrbitalRing(3.55, 0.018, -Math.PI / 3.8, Math.PI / 4, 0.4, 0x38bdf8, 0x00d4ff);
    const ringC = createOrbitalRing(2.7, 0.024, Math.PI / 2.1, 0, 0, 0x67e8f9, 0x00f2ff);
    ringsGroup.add(ringA);
    ringsGroup.add(ringB);
    ringsGroup.add(ringC);

    // Nodos brillantes en las órbitas
    const nodesGroup = new THREE.Group();
    ringsGroup.add(nodesGroup);
    const nodeGeo = new THREE.SphereGeometry(0.09, 16, 16);
    const nodeMat = new THREE.MeshBasicMaterial({{ color: 0xffffff }});
    const nodeA = new THREE.Mesh(nodeGeo, nodeMat);
    const nodeB = new THREE.Mesh(nodeGeo, nodeMat);
    const nodeC = new THREE.Mesh(nodeGeo, nodeMat);
    nodesGroup.add(nodeA);
    nodesGroup.add(nodeB);
    nodesGroup.add(nodeC);

    // 4. PEDESTAL CIRCULAR DE CONTENCIÓN EN EL SUELO (Reflejos y Anillos LED)
    const pedestalGroup = new THREE.Group();
    pedestalGroup.position.y = -3.2;
    scene.add(pedestalGroup);

    const floorRadii = [1.6, 2.4, 3.3, 4.4, 5.6];
    floorRadii.forEach((r, idx) => {{
      const floorRingGeo = new THREE.RingGeometry(r - 0.035, r + 0.035, 72);
      const floorRingMat = new THREE.MeshBasicMaterial({{
        color: idx === 1 ? 0x00f2ff : 0x0284c7,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: idx === 1 ? 0.8 : 0.35
      }});
      const floorRing = new THREE.Mesh(floorRingGeo, floorRingMat);
      floorRing.rotation.x = Math.PI / 2;
      pedestalGroup.add(floorRing);
    }});

    // Líneas radiales del pedestal
    for (let i = 0; i < 16; i++) {{
      const angle = (i / 16) * Math.PI * 2;
      const pts = [
        new THREE.Vector3(Math.cos(angle) * 1.6, 0, Math.sin(angle) * 1.6),
        new THREE.Vector3(Math.cos(angle) * 5.6, 0, Math.sin(angle) * 5.6)
      ];
      const rGeo = new THREE.BufferGeometry().setFromPoints(pts);
      const rMat = new THREE.LineBasicMaterial({{ color: 0x00f2ff, transparent: true, opacity: 0.22 }});
      const radialLine = new THREE.Line(rGeo, rMat);
      pedestalGroup.add(radialLine);
    }}

    // 5. CAMPO DE PARTÍCULAS / ENERGÍA ORBITAL
    const particleCount = 280;
    const pGeo = new THREE.BufferGeometry();
    const pPos = new Float32Array(particleCount * 3);
    const pCols = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {{
      const rad = 2.4 + Math.random() * 4.2;
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      pPos[i * 3] = rad * Math.sin(ph) * Math.cos(th);
      pPos[i * 3 + 1] = rad * Math.sin(ph) * Math.sin(th) * 0.75;
      pPos[i * 3 + 2] = rad * Math.cos(ph);

      pCols[i * 3] = 0.0;
      pCols[i * 3 + 1] = 0.95;
      pCols[i * 3 + 2] = 1.0;
    }}
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    pGeo.setAttribute('color', new THREE.BufferAttribute(pCols, 3));
    const pMat = new THREE.PointsMaterial({{
      size: 0.065,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending
    }});
    const particles = new THREE.Points(pGeo, pMat);
    coreGroup.add(particles);

    // Fondo estelar cósmico
    const starCount = 400;
    const starGeo = new THREE.BufferGeometry();
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {{
      starPos[i * 3] = (Math.random() - 0.5) * 45;
      starPos[i * 3 + 1] = (Math.random() - 0.5) * 30;
      starPos[i * 3 + 2] = (Math.random() - 0.5) * 20 - 8;
    }}
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({{ size: 0.045, color: 0x93c5fd, transparent: true, opacity: 0.65 }});
    const stars = new THREE.Points(starGeo, starMat);
    scene.add(stars);

    // Interacción suave con mouse
    let mouseX = 0, mouseY = 0;
    container.addEventListener('mousemove', (e) => {{
      const rect = container.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / width - 0.5) * 1.2;
      mouseY = ((e.clientY - rect.top) / height - 0.5) * 1.2;
    }});
    container.addEventListener('mouseleave', () => {{
      mouseX = 0;
      mouseY = 0;
    }});

    // Animación
    const clock = new THREE.Clock();
    const animState = "{state_anim}";

    function animate() {{
      requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      // Velocidad reactiva al estado
      let speedMult = 1.0;
      if (animState === 'fast') speedMult = 2.4;
      else if (animState === 'pulse') speedMult = 1.8;
      else if (animState === 'idle') speedMult = 0.4;

      // Rotaciones
      centralSphere.rotation.y = t * 0.28 * speedMult;
      neuralGrid.rotation.y = -t * 0.35 * speedMult;
      neuralGrid.rotation.x = Math.sin(t * 0.4) * 0.15;

      ringA.rotation.z = t * 0.45 * speedMult;
      ringB.rotation.z = -t * 0.38 * speedMult;
      ringC.rotation.z = t * 0.52 * speedMult;

      // Nodos orbitando
      nodeA.position.set(Math.cos(t * 1.2) * 3.1, Math.sin(t * 1.2) * 3.1 * 0.5, Math.sin(t * 1.2) * 1.5);
      nodeB.position.set(Math.sin(t * 1.0) * 3.55 * 0.7, Math.cos(t * 1.0) * 3.55, -Math.cos(t * 1.0) * 1.8);
      nodeC.position.set(Math.cos(t * 1.4) * 2.7, -Math.sin(t * 1.4) * 1.2, Math.sin(t * 1.4) * 2.7);

      particles.rotation.y = t * 0.12 * speedMult;

      // Pulsación de energía en el glifo y esfera
      if (animState === 'shake') {{
        const shake = Math.sin(t * 30.0) * 0.04;
        centralSphere.position.x = shake;
        coreLight.color.setHex(0xff3366);
        coreSphereMat.emissive.setHex(0xff2244);
        coreLight.intensity = 6.0 + Math.sin(t * 12.0) * 3.0;
      }} else if (animState === 'pulse' || animState === 'waves') {{
        centralSphere.position.x = 0;
        const pulse = 1.0 + Math.sin(t * 6.0) * 0.08;
        centralSphere.scale.set(pulse, pulse, pulse);
        deltaGroup.scale.set(pulse * 1.05, pulse * 1.05, pulse * 1.05);
        coreLight.intensity = 5.0 + Math.sin(t * 6.0) * 2.5;
        if (animState === 'pulse') {{
          coreLight.color.setHex(0x00ffaa);
        }}
      }} else {{
        centralSphere.position.x = 0;
        const gentle = 1.0 + Math.sin(t * 1.5) * 0.02;
        centralSphere.scale.set(gentle, gentle, gentle);
        deltaGroup.scale.set(1, 1, 1);
        coreLight.intensity = 5.0;
        coreLight.color.setHex(0x00f2ff);
        coreSphereMat.emissive.setHex(0x00a8ff);
      }}

      // Seguimiento de mouse
      coreGroup.rotation.y += (mouseX * 0.4 - coreGroup.rotation.y) * 0.05;
      coreGroup.rotation.x += (-mouseY * 0.3 - coreGroup.rotation.x) * 0.05;

      renderer.render(scene, camera);
    }}

    animate();

    window.addEventListener('resize', () => {{
      const nw = container.clientWidth || 900;
      const nh = container.clientHeight || {height};
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    }});
  </script>
</body>
</html>"""
    return html


def get_holographic_css() -> str:
    """Retorna los estilos CSS para la interfaz cinematográfica del Núcleo 3D y Ventanas Holográficas."""
    return """
    <style>
    /* Ocultar barra lateral en Modo Holográfico para máxima inmersión cinematográfica */
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    .main .block-container {
        max-width: 1360px !important;
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        background: transparent !important;
    }

    /* Fondo espacial general */
    body, .stApp {
        background-color: #020712 !important;
        background-image:
            radial-gradient(ellipse at 50% 25%, rgba(0, 168, 255, 0.08) 0%, transparent 60%),
            radial-gradient(circle at 85% 15%, rgba(0, 242, 255, 0.05) 0%, transparent 40%),
            linear-gradient(180deg, #01040a 0%, #030d1c 50%, #010408 100%) !important;
        background-attachment: fixed !important;
        color: #e0f2fe !important;
    }

    /* Barra Superior de Control Holográfico */
    .holo-top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(4, 14, 28, 0.85);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(0, 242, 255, 0.35);
        border-radius: 18px;
        padding: 8px 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 25px rgba(0,0,0,0.6), 0 0 20px rgba(0, 242, 255, 0.15);
    }
    .holo-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .holo-brand-title {
        font-family: 'Orbitron', -apple-system, sans-serif;
        font-size: 1.15rem;
        font-weight: 900;
        letter-spacing: 3px;
        color: #00f2ff;
        text-shadow: 0 0 12px rgba(0, 242, 255, 0.8);
    }
    .holo-brand-sub {
        font-size: 0.72rem;
        letter-spacing: 3px;
        color: #7dd3fc;
        text-transform: uppercase;
        font-weight: 700;
    }

    /* Cápsula de Entrada Inferior (Matching Image Reference) */
    .holo-input-capsule {
        position: relative;
        background: rgba(5, 18, 36, 0.92);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1.5px solid rgba(0, 242, 255, 0.45);
        border-radius: 40px;
        padding: 6px 14px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.8), 0 0 35px rgba(0, 242, 255, 0.28), inset 0 0 20px rgba(0, 242, 255, 0.1);
        margin-top: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    /* Ventanas Holográficas Inteligentes */
    .holo-window-card {
        background: rgba(5, 16, 34, 0.92) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(0, 242, 255, 0.38) !important;
        border-radius: 18px !important;
        padding: 16px 20px !important;
        margin: 12px 0 !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.75), 0 0 30px rgba(0, 242, 255, 0.2) !important;
        transition: all 0.3s ease !important;
    }
    .holo-window-card:hover {
        border-color: #00f2ff !important;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.85), 0 0 38px rgba(0, 242, 255, 0.3) !important;
    }
    .holo-window-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(0, 242, 255, 0.25);
        padding-bottom: 10px;
        margin-bottom: 14px;
    }
    .holo-window-title {
        font-family: 'Orbitron', monospace;
        font-size: 0.96rem;
        font-weight: 800;
        letter-spacing: 2px;
        color: #00f2ff;
        text-shadow: 0 0 10px rgba(0, 242, 255, 0.6);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .holo-window-controls {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Dock Flotante de Ventanas Minimizadas */
    .holo-dock {
        display: flex;
        align-items: center;
        gap: 10px;
        background: rgba(4, 12, 24, 0.88);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(0, 242, 255, 0.3);
        border-radius: 24px;
        padding: 8px 18px;
        margin: 10px 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.7), 0 0 16px rgba(0, 242, 255, 0.15);
    }
    .holo-dock-label {
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        color: #7dd3fc;
        text-transform: uppercase;
    }

    /* Botones de acción rápida futuristas */
    .stButton>button {
        background: rgba(8, 24, 48, 0.85) !important;
        border: 1px solid rgba(0, 242, 255, 0.4) !important;
        color: #e0f2fe !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        letter-spacing: 0.8px !important;
        transition: all 0.25s ease !important;
    }
    .stButton>button:hover {
        background: rgba(0, 242, 255, 0.22) !important;
        border-color: #00f2ff !important;
        box-shadow: 0 0 18px rgba(0, 242, 255, 0.5) !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, rgba(0, 242, 255, 0.35) 0%, rgba(0, 168, 255, 0.2) 100%) !important;
        border-color: #00f2ff !important;
        color: #00f2ff !important;
        text-shadow: 0 0 8px rgba(0, 242, 255, 0.6) !important;
    }
    </style>
    """

