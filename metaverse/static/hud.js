/* SKY v12 — Interfaz HUD. Sin dependencias externas; todo el texto dinámico va por textContent. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const S = {
    key: '', historial: [], voz: true, conv: false, rate: 1,
    listening: false, speaking: false, pending: null, lastSky: '',
    level: 0, pulse: 0, sttLocal: false, ytApi: false, analyser: null, freq: null,
    stream: null, recorder: null, recognition: null,
  };
  const store = {
    get(k) { try { return sessionStorage.getItem(k) || ''; } catch { return ''; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch { /* privado */ } },
    lget(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch { return d; } },
    lset(k, v) { try { localStorage.setItem(k, v); } catch { /* privado */ } },
  };
  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }
  function headers(extra = {}, json = true) {
    const h = { 'X-SKY-KEY': S.key, ...extra };
    if (json) h['Content-Type'] = 'application/json';
    if (window.SKYOwnerAuth) Object.assign(h, window.SKYOwnerAuth.headers());
    return h;
  }
  async function api(path, opts = {}) {
    const r = await fetch(path, { ...opts, headers: headers(opts.headers, !(opts.body instanceof FormData)) });
    let data = {};
    try { data = await r.json(); } catch { /* vacío */ }
    if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : ('Error HTTP ' + r.status));
    return data;
  }

  /* ------------------------------------------------------------------ estado */
  const TEXTO = { idle: 'EN ESPERA', listening: 'ESCUCHANDO', thinking: 'PROCESANDO', speaking: 'RESPONDIENDO',
    executing: 'EJECUTANDO', error: 'ATENCIÓN' };
  const COLOR = { idle: [0, 229, 255], listening: [0, 255, 170], thinking: [56, 214, 255], speaking: [235, 250, 255],
    executing: [255, 176, 32], error: [255, 51, 102] };
  let estado = 'idle', errorTimer = null;
  function setState(s, sub) {
    estado = s;
    document.body.dataset.state = s;
    $('state-label').textContent = TEXTO[s] || 'LISTO';
    if (sub !== undefined) $('state-sub').textContent = sub;
    clearTimeout(errorTimer);
    if (s === 'error') errorTimer = setTimeout(() => setState('idle', 'Listo.'), 3500);
  }

  /* ------------------------------------------------------------------ núcleo */
  const canvas = $('core');
  const ctx = canvas.getContext('2d');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let rgb = COLOR.idle.slice();
  function resize() {
    const r = canvas.getBoundingClientRect(), d = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(r.width * d)); canvas.height = Math.max(1, Math.round(r.height * d));
  }
  window.addEventListener('resize', resize);
  function col(a) { return `rgba(${rgb[0] | 0},${rgb[1] | 0},${rgb[2] | 0},${a})`; }
  function arc(r, a0, a1, w, alpha) {
    ctx.beginPath(); ctx.arc(0, 0, r, a0, a1); ctx.lineWidth = w; ctx.strokeStyle = col(alpha); ctx.stroke();
  }
  function frame(t) {
    const target = COLOR[estado] || COLOR.idle;
    for (let i = 0; i < 3; i++) rgb[i] += (target[i] - rgb[i]) * 0.08;
    let raw = 0;
    const an = (S.speaking && S.outAn) ? S.outAn : S.analyser;
    if (!S.freq) S.freq = new Uint8Array(128);
    if (an) {
      an.getByteFrequencyData(S.freq);
      let sum = 0; for (let i = 0; i < S.freq.length; i++) sum += S.freq[i];
      raw = Math.min(1, sum / S.freq.length / 90);
    }
    if (S.speaking && !(S.outAn && audioActual)) { S.pulse *= 0.9; raw = Math.max(raw, 0.25 + 0.2 * Math.abs(Math.sin(t / 110)) + S.pulse * 0.4); }
    S.level += (raw - S.level) * 0.2;
    const speed = { idle: 0.25, listening: 0.6, thinking: 1.6, speaking: 0.8, executing: 1.4, error: 0.3 }[estado] || 0.3;
    const k = reduce ? 0 : t / 1000 * speed;
    const W = canvas.width, H = canvas.height, R = Math.min(W, H) / 2 * 0.94;
    ctx.clearRect(0, 0, W, H);
    ctx.save(); ctx.translate(W / 2, H / 2);
    if (estado === 'error' && !reduce) ctx.translate(Math.sin(t / 30) * 2, 0);
    ctx.shadowColor = col(0.9); ctx.shadowBlur = 14 * (window.devicePixelRatio || 1);
    // anillo exterior con marcas de esquina
    arc(R * 0.97, 0, Math.PI * 2, 1, 0.25);
    for (let q = 0; q < 4; q++) { const a = q * Math.PI / 2 + Math.PI / 4; arc(R * 0.97, a - 0.12, a + 0.12, 3, 0.9); }
    // barras de audio radiales
    const bars = 72;
    for (let i = 0; i < bars; i++) {
      const a = i / bars * Math.PI * 2 + k * 0.15;
      let v = an ? S.freq[(i * 3) % S.freq.length] / 255 : 0;
      if (S.speaking) v = Math.max(v, S.level * (0.4 + 0.6 * Math.abs(Math.sin(i * 1.7 + t / 140))));
      const r0 = R * 0.8, r1 = r0 + R * (0.015 + v * 0.14);
      ctx.beginPath(); ctx.moveTo(Math.cos(a) * r0, Math.sin(a) * r0); ctx.lineTo(Math.cos(a) * r1, Math.sin(a) * r1);
      ctx.lineWidth = 2; ctx.strokeStyle = col(0.35 + v * 0.65); ctx.stroke();
    }
    // anillo de arcos gruesos
    ctx.save(); ctx.rotate(k * 0.6);
    for (let i = 0; i < 3; i++) arc(R * 0.66, i * 2.094, i * 2.094 + 1.5, 7, 0.8);
    ctx.restore();
    // escala graduada
    ctx.save(); ctx.rotate(-k * 0.3);
    for (let i = 0; i < 120; i++) {
      const a = i / 120 * Math.PI * 2, big = i % 10 === 0, r0 = R * 0.52, r1 = r0 + (big ? R * 0.05 : R * 0.022);
      ctx.beginPath(); ctx.moveTo(Math.cos(a) * r0, Math.sin(a) * r0); ctx.lineTo(Math.cos(a) * r1, Math.sin(a) * r1);
      ctx.lineWidth = big ? 2 : 1; ctx.strokeStyle = col(big ? 0.8 : 0.35); ctx.stroke();
    }
    ctx.restore();
    // segmentos interiores
    ctx.save(); ctx.rotate(k);
    for (let i = 0; i < 8; i++) arc(R * 0.4, i * 0.785, i * 0.785 + 0.55, 3, 0.7);
    ctx.restore();
    arc(R * 0.34, 0, Math.PI * 2, 1, 0.4);
    // núcleo
    const rc = R * (0.2 + S.level * 0.07);
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rc);
    g.addColorStop(0, 'rgba(255,255,255,0.95)'); g.addColorStop(0.35, col(0.85)); g.addColorStop(1, col(0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, rc, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = 'rgba(1,16,28,0.85)';
    ctx.font = `700 ${Math.round(R * 0.09)}px "Segoe UI", system-ui, sans-serif`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('SKY', 0, 1);
    ctx.restore();
    requestAnimationFrame(frame);
  }

  /* ------------------------------------------------------------------ feed */
  const feed = $('feed');
  function scroll() { feed.scrollTop = feed.scrollHeight; }
  function addMsg(role, text, extra) {
    const m = el('div', 'msg ' + role + (extra ? ' ' + extra : ''), text);
    feed.appendChild(m); scroll(); return m;
  }
  function addCard(title, sub) {
    const c = el('div', 'card');
    c.appendChild(el('div', 't', title));
    if (sub) c.appendChild(el('div', 's', sub));
    feed.appendChild(c); scroll(); return c;
  }
  function resultText(res) {
    if (!res) return 'Sin resultado disponible.';
    if (res.ok === false || res.status === 'FAILED') return res.error || res.message || 'No se pudo completar.';
    const msg = res.message || '';
    if (res.status === 'SENT') return (msg || 'Orden enviada') + ' (efecto aún no verificado).';
    if (res.status === 'PENDING') return (msg || 'Tarea registrada') + ' (pendiente de completar).';
    if (res.status === 'RUNNING') return (msg || 'Ejecución iniciada') + ' (sin comprobación final).';
    if (res.status === 'RECEIVED') return (msg || 'Orden recibida') + ' (aún no ejecutada).';
    if (res.status === 'NEEDS_CONFIRMATION') return msg || 'Esperando autorización.';
    if (res.status === 'VERIFIED') return msg || 'Acción verificada.';
    return msg || 'Solicitud procesada; estado final no verificado.';
  }
  function renderResult(card, res) {
    const ok = res && res.ok !== false && res.status !== 'FAILED';
    const verified = ok && res.status === 'VERIFIED';
    card.appendChild(el('div', 'res' + (!ok ? ' bad' : ''), (!ok ? '✗ ' : verified ? '✓ ' : '• ') + resultText(res)));
    let detalle = '';
    if (Array.isArray(res && res.windows)) detalle = res.windows.map(w => '▸ ' + w.title).join('\n') || '(sin ventanas)';
    else if (Array.isArray(res && res.elementos)) detalle = res.elementos.map(e => (e.carpeta ? '[dir] ' : '      ') + e.nombre).join('\n') || '(vacía)';
    else if (res && typeof res.text === 'string') detalle = res.text || '(portapapeles vacío)';
    else if (res && res.device) {
      const s = res.system || {};
      detalle = [res.device + ' · ' + res.platform + ' ' + (res.system_version || ''),
        'Perfil ' + res.profile + ' · Agente ' + (res.version || ''),
        s.bateria_percent !== undefined ? 'Batería ' + s.bateria_percent + '%' + (s.cargando ? ' (cargando)' : '') : '',
        s.cpu_percent !== undefined ? 'CPU ' + s.cpu_percent + '% · RAM ' + s.memoria_percent + '%' : ''].filter(Boolean).join('\n');
    } else if (res && res.archivo) detalle = res.archivo;
    else if (res && res.path) detalle = res.path;
    if (detalle) card.appendChild(el('pre', '', detalle));
    scroll();
  }

  /* ------------------------------------------------------------------ voz: hablar (cola por frases) */
  let voces = [];
  function cargarVoces() { voces = ('speechSynthesis' in window) ? speechSynthesis.getVoices() : []; }
  if ('speechSynthesis' in window) { cargarVoces(); speechSynthesis.onvoiceschanged = cargarVoces; }
  function vozLocal() {
    const es = voces.filter(v => /^es/i.test(v.lang));
    const pref = ['es-419', 'es-MX', 'es-US', 'es-NI', 'es-ES'];
    const ordenar = (lst) => lst.sort((a, b) => (pref.indexOf(a.lang) + 99) % 99 - (pref.indexOf(b.lang) + 99) % 99);
    return ordenar(es.filter(v => v.localService))[0] || ordenar(es)[0] || null;
  }
  function limpiarParaVoz(t) {
    return String(t || '').replace(/```[\s\S]*?```/g, ' (código en pantalla) ').replace(/\$\$?[^$]*\$\$?/g, ' ')
      .replace(/[#*_`>|~]/g, ' ').replace(/https?:\/\/\S+/g, ' enlace ')
      .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, ' ').replace(/\s+/g, ' ').trim();
  }
  function frases(t) {
    const limpio = limpiarParaVoz(t);
    const partes = limpio.match(/[^.!?…;:]+[.!?…;:]*/g) || [];
    const out = []; let buf = '';
    for (const p of partes) { buf += p; if (buf.length > 40 || /[.!?…]$/.test(buf.trim())) { out.push(buf.trim()); buf = ''; } }
    if (buf.trim()) out.push(buf.trim());
    return out.filter(Boolean);
  }
  const cola = []; let hablando = false, esperas = [], audioActual = null;
  function salidaAudio() {
    if (!S.acOut) {
      S.acOut = new (window.AudioContext || window.webkitAudioContext)();
      S.outAn = S.acOut.createAnalyser(); S.outAn.fftSize = 256; S.outAn.connect(S.acOut.destination);
    }
    if (S.acOut.state === 'suspended') S.acOut.resume().catch(() => {});
    return S.acOut;
  }
  function prepararPiper(texto) {
    return fetch('/api/hud/tts', { method: 'POST', headers: headers(), body: JSON.stringify({ texto: texto.slice(0, 680) }) })
      .then(r => r.ok ? r.blob() : Promise.reject(new Error('tts'))).catch(() => null);
  }
  function encolar(texto) {
    if (!S.voz || !texto) return;
    const item = { texto, audio: S.ttsLocal ? prepararPiper(texto) : null };
    cola.push(item);
    if (!hablando) procesarCola();
  }
  function reproducirBlob(blob) {
    return new Promise((resolve) => {
      const url = URL.createObjectURL(blob);
      const a = new Audio(url); audioActual = a;
      try { const ac = salidaAudio(); ac.createMediaElementSource(a).connect(S.outAn); } catch { /* sin visual */ }
      const fin = () => { URL.revokeObjectURL(url); audioActual = null; resolve(); };
      a.onended = fin; a.onerror = fin; a.play().catch(fin);
    });
  }
  function hablarSistema(texto) {
    return new Promise((resolve) => {
      if (!('speechSynthesis' in window)) { resolve(); return; }
      const u = new SpeechSynthesisUtterance(texto);
      const v = vozLocal(); if (v) { u.voice = v; u.lang = v.lang; } else u.lang = 'es-419';
      u.rate = S.rate; u.onboundary = () => { S.pulse = 1; };
      u.onend = resolve; u.onerror = resolve;
      speechSynthesis.speak(u);
    });
  }
  async function procesarCola() {
    hablando = true; S.speaking = true;
    setState('speaking', S.ttsLocal ? 'Voz local (Piper)' : (vozLocal() && vozLocal().localService ? 'Voz local' : 'Voz del sistema'));
    while (cola.length) {
      const item = cola.shift();
      const blob = item.audio ? await item.audio : null;
      if (!hablando) break;
      if (blob) await reproducirBlob(blob); else await hablarSistema(item.texto);
    }
    hablando = false; S.speaking = false;
    if (estado === 'speaking') setState('idle', 'Listo.');
    const w = esperas; esperas = []; w.forEach(f => f());
  }
  function speak(text) {
    frases(text).forEach(encolar);
    return new Promise((resolve) => { if (!hablando) resolve(); else esperas.push(resolve); });
  }
  function callar() {
    cola.length = 0; hablando = false; S.speaking = false;
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    if (audioActual) { audioActual.pause(); audioActual = null; }
    const w = esperas; esperas = []; w.forEach(f => f());
  }

  /* ------------------------------------------------------------------ voz: escuchar */
  async function micAnalyser() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    const src = ac.createMediaStreamSource(stream);
    const an = ac.createAnalyser(); an.fftSize = 256; src.connect(an);
    S.analyser = an; S.freq = new Uint8Array(an.frequencyBinCount); S.stream = stream; S.ac = ac;
    return stream;
  }
  function soltarMic() {
    if (S.stream) S.stream.getTracks().forEach(t => t.stop());
    if (S.ac) S.ac.close().catch(() => {});
    S.stream = null; S.ac = null; S.analyser = null;
  }
  function finEscucha() {
    S.listening = false; $('btn-mic').classList.remove('rec'); soltarMic();
    if (estado === 'listening') setState('idle', 'Listo.');
    if (W.on && W.sr) setTimeout(() => { try { W.sr.start(); } catch { /* ya activo */ } }, 500);
  }
  async function escuchar() {
    if (S.listening) { detenerEscucha(); return; }
    callar();
    if (W.sr) { try { W.sr.stop(); } catch { /* se reanuda en onend */ } }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      addMsg('sky', 'Este navegador no permite usar el micrófono aquí.', 'err'); return;
    }
    S.listening = true; $('btn-mic').classList.add('rec');
    $('transcript').textContent = '';
    try {
      if (S.sttLocal && window.MediaRecorder) await grabarLocal();
      else await dictadoNavegador();
    } catch (e) {
      finEscucha(); setState('error', 'Micrófono no disponible: ' + e.message);
    }
  }
  function detenerEscucha() {
    if (S.recorder && S.recorder.state === 'recording') S.recorder.stop();
    if (S.recognition) { try { S.recognition.stop(); } catch { /* ya parado */ } }
  }
  async function grabarLocal() {
    const stream = await micAnalyser();
    setState('listening', 'Reconocimiento 100 % local');
    const tipo = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(t => MediaRecorder.isTypeSupported(t)) || '';
    const rec = new MediaRecorder(stream, tipo ? { mimeType: tipo } : undefined);
    const partes = []; S.recorder = rec;
    rec.ondataavailable = (e) => { if (e.data.size) partes.push(e.data); };
    let hablo = false, silencio = 0; const inicio = performance.now();
    const vad = setInterval(() => {
      const ahora = performance.now();
      if (S.level > 0.12) { hablo = true; silencio = ahora; }
      if ((hablo && ahora - silencio > 1100) || ahora - inicio > 14000 || (!hablo && ahora - inicio > 6000)) {
        if (rec.state === 'recording') rec.stop();
      }
    }, 120);
    rec.onstop = async () => {
      clearInterval(vad); finEscucha();
      if (!hablo || !partes.length) { setState('idle', 'No escuché nada.'); return; }
      setState('thinking', 'Transcribiendo en tu equipo…');
      const ext = (rec.mimeType || '').includes('mp4') ? 'm4a' : 'webm';
      const fd = new FormData(); fd.append('file', new Blob(partes, { type: rec.mimeType }), 'voz.' + ext); fd.append('language', 'es');
      try {
        const r = await api('/api/global-media/stt/transcribe', { method: 'POST', body: fd });
        const texto = String(r.text || '').trim();
        if (!texto) { setState('idle', 'No entendí. Probá de nuevo.'); return; }
        $('transcript').textContent = '“' + texto + '”';
        recibir(texto, 'voz');
      } catch (e) { setState('error', 'Transcripción local: ' + e.message); }
    };
    rec.start(250);
  }
  async function dictadoNavegador() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) throw new Error('sin reconocimiento de voz (usá Chrome/Edge o instalá faster-whisper)');
    try { await micAnalyser(); } catch { /* sólo visual */ }
    const rec = new SR(); S.recognition = rec;
    rec.lang = 'es-419'; rec.interimResults = true; rec.maxAlternatives = 1;
    setState('listening', 'Dictado del navegador (puede usar la nube)');
    let final = '';
    rec.onresult = (ev) => {
      let txt = '';
      for (const r of ev.results) { txt += r[0].transcript; if (r.isFinal) final = txt; }
      $('transcript').textContent = '“' + txt + '”';
    };
    rec.onend = () => { S.recognition = null; finEscucha(); if (final.trim()) recibir(final.trim(), 'voz'); };
    rec.onerror = (e) => { S.recognition = null; finEscucha(); if (e.error !== 'no-speech' && e.error !== 'aborted') setState('error', 'Voz: ' + e.error); };
    rec.start();
  }

  /* ------------------------------------------------------------------ escucha continua "SKY…" */
  const WAKE = /^\s*(?:oye\s+|hey\s+|ok\s+|okay\s+)?(?:sky|skye|skai|esky|eskai|esquai|es\s?kai|escai|scai)\b[\s,.:;!¡¿?]*(.*)$/i;
  const W = { on: false, stream: null, ac: null, an: null, buf: null, rec: null, timer: null, sr: null, ocupado: false };
  function ordenDespertador(texto) { const m = String(texto || '').match(WAKE); return m ? m[1].trim() : null; }
  async function activarEscucha(on) {
    W.on = on; const b = $('btn-wake'); b.setAttribute('aria-pressed', String(on)); store.lset('sky-wake', on ? '1' : '0');
    if (!on) { apagarEscucha(); setState('idle', 'Escucha continua apagada.'); return; }
    try {
      if (S.sttLocal && window.MediaRecorder) await vigilarLocal(); else vigilarNavegador();
      setState('idle', 'Decí “SKY…” cuando quieras' + (S.sttLocal ? ' (100 % local)' : ' (dictado del navegador)'));
    } catch (e) { W.on = false; b.setAttribute('aria-pressed', 'false'); setState('error', 'Micrófono: ' + e.message); }
  }
  function apagarEscucha() {
    clearInterval(W.timer); W.timer = null;
    if (W.rec && W.rec.state === 'recording') { W.rec.onstop = null; W.rec.stop(); }
    if (W.stream) W.stream.getTracks().forEach(t => t.stop());
    if (W.ac) W.ac.close().catch(() => {});
    if (W.sr) { W.sr.onend = null; try { W.sr.stop(); } catch { /* */ } }
    Object.assign(W, { stream: null, ac: null, an: null, rec: null, sr: null, ocupado: false });
  }
  async function vigilarLocal() {
    W.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    W.ac = new (window.AudioContext || window.webkitAudioContext)();
    W.an = W.ac.createAnalyser(); W.an.fftSize = 512; W.ac.createMediaStreamSource(W.stream).connect(W.an);
    W.buf = new Uint8Array(W.an.fftSize);
    const tipo = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(t => MediaRecorder.isTypeSupported(t)) || '';
    let partes = [], voz = 0, silencio = 0, inicio = 0;
    W.timer = setInterval(() => {
      if (!W.on || W.ocupado || S.listening || S.speaking || hablando) return;
      W.an.getByteTimeDomainData(W.buf);
      let sum = 0; for (const v of W.buf) sum += (v - 128) * (v - 128);
      const rms = Math.sqrt(sum / W.buf.length) / 128, ahora = performance.now();
      if (!W.rec || W.rec.state !== 'recording') {
        voz = rms > 0.045 ? voz + 1 : 0;
        if (voz >= 2) {
          partes = []; inicio = ahora; silencio = ahora;
          W.rec = new MediaRecorder(W.stream, tipo ? { mimeType: tipo } : undefined);
          W.rec.ondataavailable = (e) => { if (e.data.size) partes.push(e.data); };
          W.rec.onstop = () => transcribirDespertador(partes, W.rec ? W.rec.mimeType : tipo);
          W.rec.start(200);
        }
        return;
      }
      if (rms > 0.035) silencio = ahora;
      if (ahora - silencio > 850 || ahora - inicio > 9000) W.rec.stop();
    }, 90);
  }
  async function transcribirDespertador(partes, mime) {
    if (!partes.length || !W.on) return;
    W.ocupado = true;
    try {
      const fd = new FormData(); fd.append('file', new Blob(partes, { type: mime }), (mime || '').includes('mp4') ? 'w.m4a' : 'w.webm');
      fd.append('language', 'es');
      const r = await api('/api/global-media/stt/transcribe', { method: 'POST', body: fd });
      const orden = ordenDespertador(r.text);
      if (orden !== null) {
        $('transcript').textContent = '“' + (r.text || '').trim() + '”';
        if (orden) recibir(orden, 'voz'); else { await speak('¿Sí?'); escuchar(); }
      }
    } catch { /* ruido o audio corto */ }
    W.ocupado = false;
  }
  function vigilarNavegador() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) throw new Error('el navegador no tiene reconocimiento de voz; instalá faster-whisper');
    const sr = new SR(); W.sr = sr; sr.lang = 'es-419'; sr.continuous = true; sr.interimResults = false;
    sr.onresult = (ev) => {
      if (S.speaking || hablando || S.listening) return;
      const txt = ev.results[ev.results.length - 1][0].transcript;
      const orden = ordenDespertador(txt);
      if (orden === null) return;
      $('transcript').textContent = '“' + txt.trim() + '”';
      if (orden) recibir(orden, 'voz'); else speak('¿Sí?').then(() => { try { sr.stop(); } catch { /* */ } escuchar(); });
    };
    sr.onend = () => { if (W.on && W.sr === sr && !S.listening) setTimeout(() => { try { sr.start(); } catch { /* */ } }, 400); };
    sr.onerror = () => { /* se reinicia en onend */ };
    sr.start();
  }

  /* ------------------------------------------------------------------ conversación */
  const SI = /^(si|sí|dale|hacelo|hazlo|confirmo|confirmar|adelante|ok|okay|de acuerdo|claro|ejecuta|ejecutalo)\b/i;
  const NO = /^(no|cancela|cancelar|dejalo|déjalo|olvidalo|olvídalo|mejor no)\b/i;
  function recibir(texto, origen) {
    if (S.pending && origen === 'voz') {
      const t = texto.trim().toLowerCase();
      if (SI.test(t)) { addMsg('user', texto); S.pending.run(); return; }
      if (NO.test(t)) { addMsg('user', texto); S.pending.cancel(); speak('Cancelado.'); return; }
    }
    enviar(texto, origen === 'voz' ? 'voz' : 'chat');
  }
  async function enviar(texto, modo) {
    texto = String(texto || '').trim();
    if (!texto) return;
    addMsg('user', texto); $('chat-input').value = '';
    setState('thinking', modo === 'voz' ? 'Pensando…' : 'Procesando…');
    if (modo === 'voz' && window.ReadableStream) { await enviarStream(texto); return; }
    try {
      const data = await api('/api/asistente/mensaje', { method: 'POST', body: JSON.stringify({
        texto, historial: S.historial.slice(-12), modo, dispositivo: 'local' }) });
      S.historial.push({ role: 'user', content: texto });
      await responder(data, modo);
    } catch (e) {
      addMsg('sky', 'No pude contactar a SKY: ' + e.message, 'err'); setState('error', 'Sin conexión con SKY');
    }
  }
  async function enviarStream(texto) {
    let r;
    try {
      r = await fetch('/api/asistente/stream', { method: 'POST', headers: headers(), body: JSON.stringify({
        texto, historial: S.historial.slice(-12), modo: 'voz', dispositivo: 'local' }) });
      if (!r.ok || !r.body) throw new Error('HTTP ' + r.status);
    } catch (e) { addMsg('sky', 'No pude contactar a SKY: ' + e.message, 'err'); setState('error', 'Sin conexión'); return; }
    S.historial.push({ role: 'user', content: texto });
    const lector = r.body.getReader(), dec = new TextDecoder();
    let resto = '', acumulado = '', pendiente = '', vivo = null;
    const soltarFrases = (forzar) => {
      const m = pendiente.match(/^[\s\S]*[.!?…:;](?=\s|$)/);
      if (m && m[0].trim().length > 2) { encolar(limpiarParaVoz(m[0])); pendiente = pendiente.slice(m[0].length); }
      if (forzar && pendiente.trim()) { encolar(limpiarParaVoz(pendiente)); pendiente = ''; }
    };
    for (;;) {
      const { value, done } = await lector.read();
      if (done) break;
      resto += dec.decode(value, { stream: true });
      let nl;
      while ((nl = resto.indexOf('\n')) >= 0) {
        const linea = resto.slice(0, nl).trim(); resto = resto.slice(nl + 1);
        if (!linea) continue;
        let ev; try { ev = JSON.parse(linea); } catch { continue; }
        if (ev.delta) {
          if (!vivo) { vivo = addMsg('sky', '', 'live'); }
          acumulado += ev.delta; pendiente += ev.delta; vivo.textContent = acumulado; scroll();
          soltarFrases(false);
        }
        if (ev.final) {
          if (vivo) vivo.classList.remove('live');
          if (ev.final.transmitido) {
            soltarFrases(true);
            const msg = ev.final.mensaje || acumulado;
            if (vivo) vivo.textContent = msg; else addMsg('sky', msg);
            S.lastSky = msg; S.historial.push({ role: 'assistant', content: msg.slice(0, 4000) });
            await speak(''); seguirConversacion();
          } else {
            if (vivo && !acumulado.trim()) vivo.remove();
            await responder(ev.final, 'voz');
          }
          return;
        }
      }
    }
    if (vivo) vivo.classList.remove('live');
  }
  async function decir(texto, extra) {
    addMsg('sky', texto, extra);
    S.lastSky = texto;
    S.historial.push({ role: 'assistant', content: String(texto).slice(0, 4000) });
    await speak(texto);
    seguirConversacion();
  }
  function seguirConversacion() {
    if (S.conv && !S.listening && !S.pending) setTimeout(() => { if (S.conv && !S.speaking && !S.listening) escuchar(); }, 350);
  }
  async function responder(data, modo) {
    if (data.tipo === 'respuesta' || data.tipo === 'local') {
      if (Array.isArray(data.correos) && data.correos.length) {
        const c = addCard('Correos nuevos (' + data.correos.length + ')', 'sin marcar como leídos');
        c.appendChild(el('pre', '', data.correos.map(m => '▸ ' + m.de + ' — ' + m.asunto + '\n   ' + (m.resumen || '').slice(0, 140)).join('\n')));
      }
      if (data.recordatorio || data.proveedor === 'sky-agenda') refrescarAgenda();
      await decir(data.mensaje || ''); return;
    }
    if (data.tipo === 'error') { setState('error', 'Revisá el motor de IA'); addMsg('sky', data.mensaje || 'Error.', 'err'); await speak('Tengo un problema: ' + (data.mensaje || '').split('.')[0]); return; }
    if (data.tipo === 'accion') { await accion(data, modo); return; }
    if (data.tipo === 'casa') { await casaOrden(data, modo); return; }
    if (data.tipo === 'correo') { await correoOrden(data, modo); return; }
    await decir(data.mensaje || 'Listo.');
  }
  async function accion(data, modo) {
    const p = data.propuesta;
    if (data.interfaz) { await interfaz(p); return; }
    if (p.action === 'play_media' && (p.params.service || 'youtube') === 'youtube' && S.ytApi && !p.params.path) {
      await reproductor(p.params.query); return;
    }
    const card = addCard('▸ ' + p.description, 'acción · ' + p.action);
    if (data.ejecucion) {
      renderResult(card, data.ejecucion); setState('idle', 'Listo.');
      await speak(resultText(data.ejecucion)); refrescarLog(); seguirConversacion(); return;
    }
    if (data.aviso) { card.appendChild(el('div', 'note', data.aviso)); setState('idle', 'Permiso desactivado');
      await speak('Esa función está desactivada en tu equipo. Te dejé cómo activarla.'); seguirConversacion(); return; }
    confirmar(card, p.description, () => ejecutar({ ...p, approval_token: data.approval_token }, card));
    setState('idle', 'Esperando tu confirmación');
    if (modo === 'voz') { await speak('¿Lo hago? ' + p.description + '.'); if (S.conv || modo === 'voz') escuchar(); }
  }
  function confirmar(card, desc, run) {
    const btns = el('div', 'btns');
    const si = el('button', 'btn primary', 'Ejecutar'); si.type = 'button';
    const no = el('button', 'btn', 'Cancelar'); no.type = 'button';
    btns.append(si, no); card.appendChild(btns); scroll();
    const pend = {
      run: () => { btns.remove(); S.pending = null; run(); },
      cancel: () => { btns.remove(); S.pending = null; card.appendChild(el('div', 's', 'Cancelado.')); setState('idle', 'Listo.'); },
    };
    si.addEventListener('click', pend.run); no.addEventListener('click', pend.cancel);
    S.pending = pend;
  }
  async function ejecutar(p, card) {
    setState('executing', p.description);
    try {
      const res = await api('/api/asistente/ejecutar', { method: 'POST', body: JSON.stringify({ action: p.action, params: p.params, dispositivo: 'local', approval_token: p.approval_token || '' }) });
      renderResult(card, res); setState('idle', 'Listo.'); await speak(resultText(res));
    } catch (e) { renderResult(card, { ok: false, error: e.message }); setState('error', 'No se completó'); await speak('No se pudo: ' + e.message); }
    refrescarLog(); refrescarTareas(); refrescarNotas(); seguirConversacion();
  }
  async function casaOrden(data, modo) {
    const p = data.propuesta;
    const card = addCard('▸ ' + p.description, 'casa · ' + p.service);
    const correr = async () => {
      setState('executing', p.description);
      try {
        const r = await api('/api/asistente/casa', { method: 'POST', body: JSON.stringify({ service: p.service, entity_ids: p.entity_ids, data: p.data || {}, approval_token: data.approval_token || '' }) });
        renderResult(card, r); setState('idle', 'Listo.'); await speak('Listo.');
      } catch (e) { renderResult(card, { ok: false, error: e.message }); setState('error', 'Casa'); }
      refrescarCasa(); seguirConversacion();
    };
    if (data.ejecucion) { renderResult(card, data.ejecucion); setState('idle', 'Listo.'); await speak(data.ejecucion.ok === false ? 'No pude.' : 'Listo.'); seguirConversacion(); return; }
    confirmar(card, p.description, correr);
    if (modo === 'voz') { await speak('¿Confirmás? ' + p.description + '.'); escuchar(); }
  }

  async function correoOrden(data, modo) {
    const b = data.borrador;
    const card = addCard('▸ ' + data.mensaje, 'correo · para ' + b.para);
    card.appendChild(el('pre', '', 'Asunto: ' + b.asunto + '\n\n' + b.cuerpo));
    confirmar(card, data.mensaje, async () => {
      setState('executing', 'Enviando correo');
      try {
        const r = await api('/api/asistente/correo', { method: 'POST', body: JSON.stringify({ ...b, approval_token: data.approval_token || '' }) });
        renderResult(card, r); setState('idle', 'Listo.'); await speak(r.message || 'Enviado.');
      } catch (e) { renderResult(card, { ok: false, error: e.message }); setState('error', 'Correo'); }
      seguirConversacion();
    });
    setState('idle', 'Revisá el correo antes de enviarlo');
    if (modo === 'voz') { await speak('Te dejé el borrador. ¿Lo envío?'); escuchar(); }
  }

  /* ------------------------------------------------------------------ acciones de interfaz */
  async function interfaz(p) {
    const sub = (p.params || {}).subaction || '';
    if (p.action === 'player_control') { controlReproductor(sub); await decir(p.description); return; }
    if (p.action === 'holographic_window') { ventanasHolograficas(sub); await decir(p.params.message || p.description); return; }
    if (p.action === 'voice_control') {
      if (sub === 'stop_speech') { callar(); return; }
      if (sub === 'slower') S.rate = 0.85;
      if (sub === 'normal_speed') S.rate = 1;
      if (sub === 'pause_session' || sub === 'end_session') setConv(false);
      if (sub === 'resume_session') setConv(true);
      if (sub === 'repeat_last') { await decir(S.lastSky ? 'Te repito: ' + S.lastSky : 'Todavía no te dije nada.'); return; }
      if (sub === 'text_mode') { setConv(false); $('chat-input').focus(); }
      await decir(p.params.message || p.description); return;
    }
    if (p.action === 'social_action') {
      const prm = p.params || {};
      const texto = prm.content || prm.comment || prm.message || '';
      const card = addCard('Borrador para ' + (prm.platform || 'redes'), 'SKY no publica ni envía por vos: copiá y pegá cuando quieras.');
      card.appendChild(el('pre', '', texto || '(decime el texto del mensaje)'));
      const b = el('button', 'btn', 'Copiar'); b.type = 'button';
      b.addEventListener('click', () => { navigator.clipboard && navigator.clipboard.writeText(texto).then(() => { b.textContent = 'Copiado'; }); });
      const bb = el('div', 'btns'); bb.appendChild(b); card.appendChild(bb);
      await speak('Te preparé el borrador.'); return;
    }
    await decir(p.description);
  }

  /* ------------------------------------------------------------------ ventanas holográficas */
  const ventanas = new Map(); let zTop = 10, cascada = 0;
  function abrirVentana(id, titulo, contenido, opts = {}) {
    if (ventanas.has(id)) { const w = ventanas.get(id); w.el.classList.remove('hidden'); enfocar(id); return w; }
    const w = el('div', 'win'); w.dataset.id = id;
    const anchoMax = window.innerWidth, altoMax = window.innerHeight - 56;
    const ancho = Math.min(opts.w || 920, anchoMax - 40), alto = Math.min(opts.h || 600, altoMax - 60);
    w.style.width = ancho + 'px'; w.style.height = alto + 'px';
    w.style.left = Math.max(10, (anchoMax - ancho) / 2 + cascada) + 'px';
    w.style.top = Math.max(10, (altoMax - alto) / 2 + cascada) + 'px';
    cascada = (cascada + 28) % 140;
    const hd = el('header'); hd.appendChild(el('span', 'ttl', titulo));
    const bMin = el('button', '', '–'), bMax = el('button', '', '□'), bX = el('button', '', '×');
    [bMin, bMax, bX].forEach((b, i) => { b.type = 'button'; b.title = ['Minimizar', 'Ampliar', 'Cerrar'][i]; hd.appendChild(b); });
    w.appendChild(hd);
    if (typeof contenido === 'string') {
      const f = document.createElement('iframe'); f.src = contenido; f.title = titulo;
      f.setAttribute('allow', opts.allow || 'microphone; camera; clipboard-write');
      if (opts.referrer) f.referrerPolicy = opts.referrer;
      w.appendChild(f);
    } else { const b = el('div', 'body'); b.appendChild(contenido); w.appendChild(b); }
    $('windows').appendChild(w);
    const reg = { el: w, titulo };
    ventanas.set(id, reg);
    bMin.addEventListener('click', () => { w.classList.add('hidden'); dock(); });
    bMax.addEventListener('click', () => { w.classList.toggle('max'); });
    bX.addEventListener('click', () => cerrarVentana(id));
    w.addEventListener('pointerdown', () => enfocar(id));
    arrastrable(w, hd);
    enfocar(id); dock();
    return reg;
  }
  function cerrarVentana(id) { const w = ventanas.get(id); if (w) { w.el.remove(); ventanas.delete(id); dock(); } }
  function enfocar(id) { const w = ventanas.get(id); if (w) { w.el.style.zIndex = ++zTop; dock(id); } }
  function arrastrable(w, asa) {
    let sx, sy, ox, oy, mov = false;
    asa.addEventListener('pointerdown', (e) => {
      if (e.target.tagName === 'BUTTON' || w.classList.contains('max')) return;
      mov = true; sx = e.clientX; sy = e.clientY; ox = w.offsetLeft; oy = w.offsetTop; asa.setPointerCapture(e.pointerId);
    });
    asa.addEventListener('pointermove', (e) => {
      if (!mov) return;
      w.style.left = Math.max(-w.offsetWidth + 80, Math.min(window.innerWidth - 80, ox + e.clientX - sx)) + 'px';
      w.style.top = Math.max(0, Math.min(window.innerHeight - 90, oy + e.clientY - sy)) + 'px';
    });
    asa.addEventListener('pointerup', () => { mov = false; });
  }
  function dock(activa) {
    const d = $('dock'); d.textContent = '';
    ventanas.forEach((w, id) => {
      const b = el('button', (activa === id && !w.el.classList.contains('hidden')) ? 'active' : '', w.titulo); b.type = 'button';
      b.addEventListener('click', () => { if (w.el.classList.contains('hidden')) w.el.classList.remove('hidden'); enfocar(id); });
      d.appendChild(b);
    });
  }
  function ventanasHolograficas(sub) {
    if (sub === 'minimize_all' || sub === 'leave_only_core') ventanas.forEach(w => w.el.classList.add('hidden'));
    else if (sub === 'restore_all') ventanas.forEach(w => w.el.classList.remove('hidden'));
    else if (sub === 'close_multimedia') cerrarVentana('player');
    else if (sub.startsWith('close_')) {
      const grupo = { close_docs: ['office'], close_modules: [...ventanas.keys()], close_projects: ['flows'], close_chat: ['clasico'] }[sub]
        || [sub.slice(6)];
      grupo.forEach(cerrarVentana);
    }
    dock();
  }

  /* ------------------------------------------------------------------ módulos */
  const MODULOS = [
    { id: 'clasico', t: 'Clásico', d: 'Chat multi-IA, adjuntos, imágenes y búsqueda', url: '/sky' },
    { id: 'creative', t: 'Creative', d: 'Video, animación y edición por capas', url: '/creative' },
    { id: 'office', t: 'Office', d: 'Word, Excel, PowerPoint y PDF', url: '/office' },
    { id: 'flows', t: 'Flujos', d: 'Automatizaciones con aprobación', url: '/flows' },
    { id: 'world', t: 'Metaverso', d: 'Mundos 3D y escenas', url: '/world' },
    { id: 'studio', t: 'Studio 3D', d: 'Foto a modelo GLB', url: '/studio' },
    { id: 'community', t: 'Comunidad', d: 'Espacios compartidos', url: '/community' },
    { id: 'negocio', t: 'BAQUEANO', d: 'Panel de negocio del dueño', url: '/owner/baqueano' },
    { id: 'player', t: 'Reproductor', d: 'YouTube dentro de SKY', accion: () => preguntarReproducir() },
    { id: 'streamlit', t: 'Panel completo', d: 'Deportes, finanzas, visión… (pestaña aparte)', externo: 'http://127.0.0.1:8501' },
  ];
  function pintarModulos() {
    const box = $('tiles'); box.textContent = '';
    MODULOS.forEach(m => {
      const b = el('button', 'tile'); b.type = 'button';
      b.appendChild(el('b', '', m.t)); b.appendChild(el('small', '', m.d));
      b.addEventListener('click', () => {
        if (m.externo) { window.open(m.externo, '_blank', 'noopener'); return; }
        if (m.accion) { m.accion(); return; }
        abrirVentana(m.id, m.t, m.url);
        if (window.matchMedia('(max-width:900px)').matches) mostrarPanel('core');
      });
      box.appendChild(b);
    });
  }

  /* ------------------------------------------------------------------ reproductor */
  const YT = 'https://www.youtube-nocookie.com';
  let lista = [], indice = 0;
  function preguntarReproducir() {
    const i = $('chat-input'); i.value = 'reproduce '; i.focus();
  }
  async function reproductor(consulta) {
    setState('thinking', 'Buscando “' + consulta + '”');
    let r;
    try { r = await api('/api/hud/youtube?q=' + encodeURIComponent(consulta)); } catch (e) { r = { embebible: false, motivo: e.message }; }
    if (!r.embebible) {
      setState('idle', 'Abriendo en el navegador');
      const card = addCard('▸ Reproducir “' + consulta + '”', 'YouTube');
      card.appendChild(el('div', 'note', r.motivo || ''));
      await ejecutar({ action: 'play_media', params: { query: consulta, service: 'youtube' }, description: 'Reproducir ' + consulta }, card);
      return;
    }
    lista = r.videos; indice = 0; mostrarVideo();
    await decir('Reproduciendo ' + lista[0].titulo + '.');
  }
  function mostrarVideo() {
    const v = lista[indice]; if (!v) return;
    cerrarVentana('player');
    const w = abrirVentana('player', '♪ ' + v.titulo, YT + '/embed/' + encodeURIComponent(v.id) + '?autoplay=1&playsinline=1&rel=0&enablejsapi=1',
      { w: 760, h: 470, allow: 'autoplay; encrypted-media; picture-in-picture; fullscreen', referrer: 'strict-origin-when-cross-origin' });
    w.el.querySelector('iframe').setAttribute('allowfullscreen', '');
  }
  function ytCmd(func, args = []) {
    const w = ventanas.get('player'); if (!w) return;
    const f = w.el.querySelector('iframe');
    if (f && f.contentWindow) f.contentWindow.postMessage(JSON.stringify({ event: 'command', func, args }), YT);
  }
  function controlReproductor(sub) {
    const w = ventanas.get('player');
    if (!w && !['close'].includes(sub)) { return; }
    if (sub === 'close') { cerrarVentana('player'); return; }
    w.el.classList.remove('hidden', 'mini', 'max');
    if (sub === 'mode_mini') w.el.classList.add('mini');
    if (sub === 'mode_expanded') w.el.classList.add('max');
    if (sub === 'mode_fullscreen') { const f = w.el.querySelector('iframe'); if (f && f.requestFullscreen) f.requestFullscreen().catch(() => w.el.classList.add('max')); }
    if (sub === 'pause') ytCmd('pauseVideo');
    if (sub === 'play') ytCmd('playVideo');
    if (sub === 'restart') { ytCmd('seekTo', [0, true]); ytCmd('playVideo'); }
    if (sub === 'next' && lista.length) { indice = (indice + 1) % lista.length; mostrarVideo(); }
    if (sub === 'previous' && lista.length) { indice = (indice - 1 + lista.length) % lista.length; mostrarVideo(); }
    enfocar('player');
  }

  /* ------------------------------------------------------------------ paneles */
  function pill(id, txt, cls) { const p = $(id); p.textContent = txt; p.className = 'pill ' + (cls || ''); }
  function meter(id, v) {
    const ok = typeof v === 'number' && isFinite(v);
    $('m-' + id).style.width = ok ? Math.max(0, Math.min(100, v)) + '%' : '0%';
    $('v-' + id).textContent = ok ? Math.round(v) + '%' : '—';
  }
  async function refrescarEstado() {
    let e;
    try { e = await api('/api/hud/estado'); } catch (err) { pill('pill-agent', 'SKY · SIN ACCESO', 'bad'); return; }
    $('ver').textContent = 'v' + e.version;
    S.sttLocal = !!(e.stt_local && e.stt_local.disponible); S.ytApi = !!e.youtube_api; S.ttsLocal = !!e.tts_local;
    $('ia-cerebro').textContent = (e.ia && e.ia.cerebro) ? 'herramientas (entiende frases libres)' : 'sólo reglas · iniciá Ollama';
    $('ia-cerebro').title = $('ia-cerebro').textContent; $('ia-ollama').title = $('ia-ollama').textContent;
    $('ia-voz').textContent = (S.ttsLocal ? 'Piper local' : 'voz del sistema') + ' · ' + (S.sttLocal ? 'escucha local' : 'dictado navegador');
    pill('pill-voz', S.sttLocal ? 'VOZ · LOCAL' : 'VOZ · NAVEGADOR', S.sttLocal ? 'ok' : 'warn');
    const ia = e.ia || {};
    const ollamaOff = ia.proveedor === 'ollama' && !(ia.ollama && ia.ollama.activo);
    if (ollamaOff) pill('pill-ia', 'IA · OLLAMA APAGADO', 'bad');
    else if (ia.proveedor) pill('pill-ia', 'IA · ' + (ia.local ? 'LOCAL ' : '') + ia.proveedor.toUpperCase(), ia.local ? 'ok' : 'warn');
    else pill('pill-ia', 'IA · SIN MOTOR', 'bad');
    $('ia-prov').textContent = ia.proveedor ? ia.proveedor + ' · ' + (ia.modelo || '') : 'sin configurar';
    $('ia-priv').textContent = ia.solo_local ? '100 % local (forzado)' : ia.local ? 'local' : 'nube';
    $('ia-ollama').textContent = ia.ollama && ia.ollama.activo ? (ia.ollama.modelos.slice(0, 2).join(', ') || 'activo') : 'apagado · ejecutá ollama serve';
    pill('pill-casa', e.casa && e.casa.configurado ? 'CASA · CONECTADA' : 'CASA · —', e.casa && e.casa.configurado ? 'ok' : '');
    const a = e.agente || {};
    if (!a.ok) {
      pill('pill-agent', 'AGENTE · APAGADO', 'bad');
      $('sys-device').textContent = '—'; $('sys-profile').textContent = '—';
      const c = $('caps-list'); c.textContent = ''; c.appendChild(el('span', 'muted', a.error || 'Iniciá SKY completo (opción 0 del menú).'));
      ['cpu', 'ram', 'bat'].forEach(k => meter(k, null)); return;
    }
    pill('pill-agent', 'AGENTE · ' + String(a.profile || '').toUpperCase(), 'ok');
    $('sys-device').textContent = a.device + ' · ' + a.platform;
    $('sys-profile').textContent = a.profile + ' · v' + (a.version || '');
    const s = a.system || {};
    meter('cpu', s.cpu_percent); meter('ram', s.memoria_percent); meter('bat', s.bateria_percent);
    const c = $('caps-list'); c.textContent = '';
    (a.enabled || []).forEach(cap => c.appendChild(el('span', 'chip' + ((a.auto_confirm || []).includes(cap) ? ' auto' : ''), cap)));
  }
  function estadoCls(st) { st = String(st || '').toUpperCase(); return st === 'VERIFIED' ? 'ok' : st === 'FAILED' ? 'bad' : 'run'; }
  async function refrescarLog() {
    try {
      const r = await api('/api/hud/acciones'); const ul = $('log-list'); ul.textContent = '';
      if (!r.acciones.length) { ul.appendChild(el('li', 'muted', 'Sin acciones todavía.')); return; }
      r.acciones.slice(0, 12).forEach(a => {
        const li = el('li'); const hora = String(a.created_at || a.timestamp || '').slice(11, 19);
        li.appendChild(el('span', estadoCls(a.status), (a.status || '') + ' '));
        li.appendChild(document.createTextNode(hora + ' ' + (a.action || '') + ' ' + (a.target || '')));
        ul.appendChild(li);
      });
    } catch { /* agente apagado */ }
  }
  async function refrescarTareas() {
    try {
      const r = await api('/api/hud/tareas'); const ul = $('tareas-list'); ul.textContent = '';
      if (!r.tareas.length) { ul.appendChild(el('li', 'muted', 'Sin tareas en curso.')); return; }
      r.tareas.forEach(t => ul.appendChild(el('li', '', (t.title || t.titulo || 'Tarea') + ' · ' + (t.status || '') + (t.progress !== undefined ? ' ' + t.progress + '%' : ''))));
    } catch { /* sin agente */ }
  }
  async function refrescarNotas() {
    try {
      const r = await api('/api/hud/notas'); const ul = $('notas-list'); ul.textContent = '';
      if (!r.notas.length) { ul.appendChild(el('li', 'muted', 'Sin notas. Decí: “crea una nota agenda que diga…”.')); return; }
      r.notas.slice(0, 10).forEach(n => ul.appendChild(el('li', '', n.nombre)));
    } catch { /* sin acceso */ }
  }
  async function refrescarVoz() {
    try {
      const r = await api('/api/asistente/voz'); const ul = $('voz-list'); ul.textContent = '';
      if (!r.pendientes.length) { ul.appendChild(el('li', 'muted', 'Nada pendiente.')); return; }
      r.pendientes.slice().reverse().slice(0, 8).forEach(item => {
        const li = el('li'); li.appendChild(el('div', '', '“' + item.text + '”'));
        li.appendChild(el('div', 'muted', item.description || item.action));
        const bb = el('div', 'row-btns');
        const ok = el('button', 'btn primary', 'Ejecutar'), no = el('button', 'btn', 'Descartar'); ok.type = no.type = 'button';
        ok.addEventListener('click', async () => {
          const card = addCard('▸ ' + (item.description || item.action), 'desde la voz manos libres');
          await ejecutar({ action: item.action, params: item.params || {}, description: item.description || item.action, approval_token: item.approval_token }, card);
          await api('/api/asistente/voz/' + encodeURIComponent(item.id), { method: 'DELETE' }).catch(() => {}); refrescarVoz();
        });
        no.addEventListener('click', async () => { await api('/api/asistente/voz/' + encodeURIComponent(item.id), { method: 'DELETE' }).catch(() => {}); refrescarVoz(); });
        bb.append(ok, no); li.appendChild(bb); ul.appendChild(li);
      });
    } catch { /* sin acceso */ }
  }
  async function refrescarCasa() {
    let r; try { r = await api('/api/hud/casa'); } catch { return; }
    const box = $('casa-list'); box.textContent = '';
    if (!r.configurado) { box.appendChild(el('span', 'muted', 'Configurá SKY_HA_URL y SKY_HA_TOKEN en .env para controlar tu casa.')); return; }
    if (!r.ok) { box.appendChild(el('span', 'muted', r.error || 'Home Assistant no responde.')); return; }
    const visibles = (r.entidades || []).filter(e => ['light', 'switch', 'fan', 'scene'].includes(e.domain)).slice(0, 18);
    if (!visibles.length) { box.appendChild(el('span', 'muted', 'Sin luces, enchufes ni escenas.')); return; }
    visibles.forEach(e => {
      const b = el('button', 'chip' + (e.state === 'on' ? ' on' : ''), e.name); b.type = 'button';
      b.title = e.entity_id + ' · ' + e.state;
      b.addEventListener('click', async () => {
        const service = e.domain === 'scene' ? 'scene.turn_on' : e.domain + '.toggle';
        try {
          const op = { service, entity_ids: [e.entity_id], data: {} };
          const prep = await api('/api/asistente/casa/preparar', { method: 'POST', body: JSON.stringify(op) });
          await api('/api/asistente/casa', { method: 'POST', body: JSON.stringify({ ...op, approval_token: prep.approval_token }) });
        }
        catch (err) { addMsg('sky', 'Casa: ' + err.message, 'err'); }
        refrescarCasa();
      });
      box.appendChild(b);
    });
  }

  async function refrescarAvisos() {
    try {
      const r = await api('/api/hud/avisos');
      for (const a of r.avisos || []) {
        addMsg('sky', a.texto, 'aviso'); S.lastSky = a.texto;
        await speak(a.texto);
      }
      if ((r.avisos || []).length) refrescarAgenda();
    } catch { /* sin acceso */ }
  }
  async function refrescarAgenda() {
    try {
      const r = await api('/api/hud/agenda'); const ul = $('agenda-list'); ul.textContent = '';
      if (!r.recordatorios.length) { ul.appendChild(el('li', 'muted', 'Sin recordatorios. Decí: “recuérdame en 10 minutos…”.')); return; }
      r.recordatorios.slice(0, 10).forEach(x => {
        const d = new Date(x.cuando), hoy = new Date();
        const cuando = (d.toDateString() === hoy.toDateString() ? 'hoy ' : d.toLocaleDateString('es', { weekday: 'short', day: 'numeric' }) + ' ')
          + d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
        const li = el('li', '', (x.clase === 'alarma' ? '⏰ ' : '🔔 ') + cuando + ' · ' + x.texto);
        const b = el('button', 'x', '×'); b.type = 'button'; b.title = 'Borrar';
        b.addEventListener('click', async () => { await api('/api/hud/agenda/' + encodeURIComponent(x.id), { method: 'DELETE' }).catch(() => {}); refrescarAgenda(); });
        li.prepend(b); ul.appendChild(li);
      });
    } catch { /* sin acceso */ }
  }
  async function abrirDiagnostico() {
    const cont = el('div');
    cont.appendChild(el('p', 'muted', 'Revisando…'));
    abrirVentana('diag', 'Diagnóstico de SKY', cont, { w: 620, h: 560 });
    try {
      const r = await api('/api/hud/diagnostico'); cont.textContent = '';
      cont.appendChild(el('p', '', r.resumen));
      const ul = el('ul', 'diag-list');
      r.items.forEach(i => {
        const li = el('li', i.ok ? 'ok' : (i.importante ? 'bad' : 'opt'));
        li.appendChild(el('b', '', (i.ok ? '✔ ' : i.importante ? '✖ ' : '· ') + i.nombre));
        li.appendChild(el('small', '', i.detalle));
        if (i.solucion) li.appendChild(el('div', 'fix', '→ ' + i.solucion));
        ul.appendChild(li);
      });
      cont.appendChild(ul);
    } catch (e) { cont.textContent = 'No se pudo revisar: ' + e.message; }
  }

  /* ------------------------------------------------------------------ controles */
  function setConv(v) { S.conv = v; const b = $('btn-conv'); b.setAttribute('aria-pressed', String(v)); b.classList.toggle('on', v); store.lset('sky-conv', v ? '1' : '0'); }
  function setVoz(v) { S.voz = v; const b = $('btn-tts'); b.setAttribute('aria-pressed', String(v)); b.classList.toggle('on', v); store.lset('sky-voz', v ? '1' : '0'); if (!v) callar(); }
  $('btn-mic').addEventListener('click', escuchar);
  canvas.addEventListener('click', escuchar);
  canvas.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); escuchar(); } });
  $('btn-conv').addEventListener('click', () => setConv(!S.conv));
  $('btn-tts').addEventListener('click', () => setVoz(!S.voz));
  $('btn-wake').addEventListener('click', () => { salidaAudio(); activarEscucha(!W.on); });
  $('btn-diag').addEventListener('click', abrirDiagnostico);
  document.addEventListener('pointerdown', () => { try { salidaAudio(); } catch { /* */ } }, { once: true });
  $('chat-form').addEventListener('submit', (e) => { e.preventDefault(); recibir($('chat-input').value, 'texto'); });
  document.addEventListener('keydown', (e) => {
    const enCampo = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement && document.activeElement.tagName);
    if (e.key === 'Escape') { callar(); detenerEscucha(); }
    if (!enCampo && (e.code === 'Space' || e.key === 'F2')) { e.preventDefault(); escuchar(); }
  });
  function mostrarPanel(id) {
    document.querySelectorAll('.mobile-tabs button').forEach(b => b.classList.toggle('active', b.dataset.panel === id));
    $('col-left').classList.toggle('show', id === 'col-left');
    $('col-right').classList.toggle('show', id === 'col-right');
    document.querySelector('.center').classList.toggle('hide', id !== 'core');
  }
  document.querySelectorAll('.mobile-tabs button').forEach(b => b.addEventListener('click', () => mostrarPanel(b.dataset.panel)));
  function reloj() {
    const d = new Date();
    $('clock-time').textContent = d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
    $('clock-date').textContent = d.toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' });
  }

  /* ------------------------------------------------------------------ inicio */
  async function iniciar() {
    resize(); requestAnimationFrame(frame); reloj(); setInterval(reloj, 15000);
    setVoz(store.lget('sky-voz', '1') === '1'); setConv(store.lget('sky-conv', '0') === '1');
    mostrarPanel('core'); pintarModulos();
    try {
      const b = await (await fetch('/api/client/bootstrap')).json();
      S.key = b.key || store.get('sky-owner-key');
    } catch { S.key = store.get('sky-owner-key'); }
    if (!S.key) {
      S.key = (prompt('Llave del dueño de SKY (X-SKY-KEY):') || '').trim();
      if (S.key) store.set('sky-owner-key', S.key);
    }
    await refrescarEstado();
    const h = new Date().getHours();
    addMsg('sky', (h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches') +
      ', Oscar. Sistemas en línea. Tocá el núcleo para hablar, o escribime.');
    refrescarLog(); refrescarTareas(); refrescarNotas(); refrescarVoz(); refrescarCasa();
    setInterval(refrescarEstado, 10000); setInterval(refrescarLog, 8000); setInterval(refrescarTareas, 8000);
    setInterval(refrescarVoz, 15000); setInterval(refrescarNotas, 30000); setInterval(refrescarCasa, 20000);
    refrescarAgenda(); setInterval(refrescarAgenda, 30000); setInterval(refrescarAvisos, 8000);
    if (store.lget('sky-wake', '0') === '1') activarEscucha(true);
  }
  iniciar();
})();
