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
  async function api(path, opts = {}, conPin = false) {
    const r = await fetch(path, { ...opts, headers: headers(opts.headers, !(opts.body instanceof FormData)) });
    let data = {};
    try { data = await r.json(); } catch { /* vacío */ }
    // SENTINEL: lo crítico pide el PIN en ese momento; lo valida el servidor.
    if (r.status === 403 && !conPin && typeof data.detail === 'string' && data.detail.startsWith('Se requiere tu PIN')) {
      const pin = await pedirPin(data.detail.replace('Se requiere tu PIN para ', 'Tu PIN para '));
      if (pin) return api(path, { ...opts, headers: { ...(opts.headers || {}), 'X-SKY-PIN': pin } }, true);
      throw new Error('Cancelado: hace falta tu PIN.');
    }
    if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : ('Error HTTP ' + r.status));
    return data;
  }
  function pedirPin(motivo) {
    return new Promise((resolve) => {
      const fondo = el('div', 'pin-fondo'); fondo.setAttribute('role', 'dialog'); fondo.setAttribute('aria-modal', 'true');
      const caja = el('form', 'pin-caja');
      caja.appendChild(el('b', '', 'SKY SENTINEL')); caja.appendChild(el('div', 's', motivo || 'Ingresá tu PIN'));
      const inp = el('input', 'hab-in'); inp.type = 'password'; inp.inputMode = 'numeric'; inp.autocomplete = 'off'; inp.maxLength = 12;
      inp.setAttribute('aria-label', 'PIN');
      const err = el('div', 'res bad', '');
      const bx = el('div', 'btns'); const ok = el('button', 'btn primary', 'Confirmar'); ok.type = 'submit';
      const no = el('button', 'btn', 'Cancelar'); no.type = 'button'; bx.append(ok, no);
      caja.append(inp, err, bx); fondo.appendChild(caja); document.body.appendChild(fondo); inp.focus();
      const fin = (v) => { fondo.remove(); resolve(v); };
      caja.addEventListener('submit', (e) => { e.preventDefault(); if (!/^\d{6,12}$/.test(inp.value)) { err.textContent = 'El PIN tiene de 6 a 12 dígitos.'; return; } fin(inp.value); });
      no.addEventListener('click', () => fin(null));
    });
  }
  async function desbloquear() {
    callar(); S.key = ''; store.set('sky-owner-key', '');
    for (;;) {
      const pin = await pedirPin('SKY está bloqueada. Ingresá tu PIN para desbloquearla.');
      if (!pin) continue;
      try {
        const r = await fetch('/api/sentinel/desbloquear', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin }) });
        const d = await r.json().catch(() => ({}));
        if (r.ok && d.key) { S.key = d.key; return; }
        addMsg('sky', d.detail || 'PIN incorrecto.', 'err');
      } catch (e) { addMsg('sky', 'No pude verificar el PIN: ' + e.message, 'err'); }
    }
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
  function guardarConsulta(role, text, origen) {
    if (!S.key || !text || !String(text).trim()) return;
    api('/api/hud/historial', {method:'POST', body:JSON.stringify({
      role, source:origen || S.currentOrigin || 'chat', text:String(text).slice(0,4000)})}).catch(() => {
      // No declarar guardado si el servidor no está disponible.
      S.historyPending = true;
    });
  }
  function addMsg(role, text, extra) {
    const m = el('div', 'msg ' + role + (extra ? ' ' + extra : ''), text);
    feed.appendChild(m); scroll();
    // Los mensajes normales se guardan en /api/asistente/ por el servidor
    // (texto y streaming). El HUD solo registra comandos 100 % locales.
    return m;
  }
  function addCard(title, sub) {
    const c = el('div', 'card');
    c.appendChild(el('div', 't', title));
    if (sub) c.appendChild(el('div', 's', sub));
    feed.appendChild(c); scroll(); return c;
  }
  function resultText(res) {
    if (!res) return 'Hecho.';
    if (res.ok === false) return res.error || res.message || 'No se pudo completar.';
    return res.message || 'Hecho.';
  }
  function renderResult(card, res) {
    const ok = res && res.ok !== false;
    card.appendChild(el('div', 'res' + (ok ? '' : ' bad'), (ok ? '✓ ' : '✗ ') + resultText(res)));
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
  function pedirMic() {
    return navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
      .catch((e) => { kpiEvento('voz', 'error_microfono', null, false); throw e; });
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
      const falla = () => { kpiEvento('voz', 'error_reproduccion', null, false); fin(); };
      a.onended = fin; a.onerror = falla; a.play().catch(falla);
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
      if (S.tEnvio) { kpiEvento('voz', 'primera_voz', performance.now() - S.tEnvio); S.tEnvio = null; }
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
    if (hablando) kpiEvento('voz', 'interrupcion');
    S.tEnvio = null;
    cola.length = 0; hablando = false; S.speaking = false;
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    if (audioActual) { audioActual.pause(); audioActual = null; }
    const w = esperas; esperas = []; w.forEach(f => f());
  }

  /* ------------------------------------------------------------------ voz: escuchar */
  async function micAnalyser() {
    const stream = await pedirMic();
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
    W.stream = await pedirMic();
    W.ac = new (window.AudioContext || window.webkitAudioContext)();
    W.an = W.ac.createAnalyser(); W.an.fftSize = 512; W.ac.createMediaStreamSource(W.stream).connect(W.an);
    W.buf = new Uint8Array(W.an.fftSize);
    const tipo = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(t => MediaRecorder.isTypeSupported(t)) || '';
    let partes = [], voz = 0, silencio = 0, inicio = 0;
    W.timer = setInterval(() => {
      if (!W.on || W.ocupado || S.listening || S.speaking || hablando ||
          estado === 'thinking' || estado === 'executing') return;
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
      // CONV + listening are both explicit owner controls. When both are on,
      // recognize direct speech without the 'SKY' prefix, as the browser
      // recognizer already does. Do not enable silently.
      const wakeOrder = ordenDespertador(r.text);
      const orden = wakeOrder !== null ? wakeOrder
        : (S.conv ? String(r.text || '').trim() : null);
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
      const txt = ev.results[ev.results.length - 1][0].transcript;
      const orden = ordenDespertador(txt);
      // Barge-in: only explicit SKY interrupt commands can stop speech.
      // Ordinary recognition during playback is ignored to suppress self-echo.
      if (S.speaking || hablando) {
        if (orden !== null && /^(?:para|det[eé]nte|calla|c[aá]llate|deja de hablar|silencio)\b/i.test(orden)) {
          callar();
          setState('listening', 'Interrumpida por indicación del usuario.');
        }
        return;
      }
      if (S.listening) return;
      if (orden === null && !S.conv) return;
      const efectivo = orden !== null ? orden : txt.trim();
      if (!efectivo) return;
      $('transcript').textContent = '“' + txt.trim() + '”';
      recibir(efectivo, 'voz');
    };
    sr.onend = () => { if (W.on && W.sr === sr && !S.listening) setTimeout(() => { try { sr.start(); } catch { /* */ } }, 400); };
    sr.onerror = () => { /* se reinicia en onend */ };
    sr.start();
  }

  // Adjuntos de la conversación actual. Se guardan por la API existente de SKY.
  const adjuntosChat = [];
  function mostrarAdjuntos() {
    const chips = $('chat-files'); chips.replaceChildren();
    chips.hidden = adjuntosChat.length === 0;
    adjuntosChat.forEach((a, i) => {
      const chip = el('span', 'chip');
      chip.appendChild(document.createTextNode('📎 ' + a.filename));
      const quitar = el('button', '', '×'); quitar.type = 'button';
      quitar.title = 'Quitar ' + a.filename;
      quitar.addEventListener('click', () => { adjuntosChat.splice(i, 1); mostrarAdjuntos(); });
      chip.appendChild(quitar); chips.appendChild(chip);
    });
  }
  async function subirAdjuntos(files) {
    for (const file of files) {
      // Cualquier extensión: límite por archivo para proteger memoria y disco.
      if (file.size > 50 * 1024 * 1024) {
        addMsg('sky', 'El archivo ' + file.name + ' supera 50 MB. Usá una versión más pequeña.', 'err');
        continue;
      }
      const fd = new FormData(); fd.append('file', file);
      try {
        const data = await api('/api/chat/upload', { method: 'POST', body: fd });
        if (!data.ok) throw Error('El servidor no confirmó la carga.');
        adjuntosChat.push({filename:data.filename, media_type:data.media_type,
          full_text:String(data.full_text || '').slice(0, 11000), media_url:data.media_url});
        mostrarAdjuntos();
        addMsg('sky', 'Adjunté ' + data.filename + ' (' + data.media_type + '). ' +
          (data.chars_extracted ? 'Texto disponible para preguntas.' : 'Formato recibido; la interpretación depende de herramientas compatibles.'));
      } catch (e) {
        addMsg('sky', 'No se pudo adjuntar ' + file.name + ': ' + e.message, 'err');
      }
    }
  }
  $('btn-attach').addEventListener('click', () => $('chat-file-input').click());
  $('chat-file-input').addEventListener('change', e => {
    subirAdjuntos(Array.from(e.target.files || []));
    e.target.value = '';
  });
  function contextoDeAdjuntos() {
    return adjuntosChat.map(a => 'ARCHIVO: ' + a.filename + ' · ' + a.media_type +
      '\nCONTENIDO EXTRAÍDO:\n' + a.full_text).join('\n\n').slice(0, 11900);
  }
  function confirmarEnvioAdjuntos() { adjuntosChat.splice(0); mostrarAdjuntos(); }

  /* ------------------------------------------------------------------ conversación */
  const SI = /^(si|sí|dale|hacelo|hazlo|confirmo|confirmar|adelante|ok|okay|de acuerdo|claro|ejecuta|ejecutalo)\b/i;
  const NO = /^(no|cancela|cancelar|dejalo|déjalo|olvidalo|olvídalo|mejor no)\b/i;
  function recibir(texto, origen) {
    S.currentOrigin = origen === 'voz' ? 'voz' : 'chat';
    if (S.pending && origen === 'voz') {
      const t = texto.trim().toLowerCase();
      if (SI.test(t) && S.pending.soloClic) { addMsg('user', texto); speak('Por seguridad, esto no se confirma sólo con la voz: tocá Ejecutar.'); return; }
      if (SI.test(t)) { addMsg('user', texto); S.pending.run(); return; }
      if (NO.test(t)) { addMsg('user', texto); S.pending.cancel(); speak('Cancelado.'); return; }
    }
    const requestedModule = solicitudModulo(texto);
    if (requestedModule) {
      addMsg('user', texto); guardarConsulta('user', texto);
      abrirModuloTecnico(requestedModule);
      return;
    }
    // Los comandos de ventanas son locales al HUD, no delegados a la IA.
    const mini = ordenVentanaLocal(texto);
    if (mini) {
      addMsg('user', texto);
      guardarConsulta('user',texto);
      if (mini === 'chat') abrirCuadroTexto();
      else if (mini === 'history') abrirHistorial();
      else if (mini === 'creative') abrirVentana('studio-creativo','SKY · Estudio creativo','/creative',{w:610,h:490});
      else if (mini === 'diagnostic') abrirDiagnostico();
      else if (mini === 'programming') abrirProgramacion();
      const reply = 'Abrí ' + ({chat:'un cuadro de texto',history:'el historial completo',
        creative:'el Estudio Creativo',diagnostic:'el diagnóstico',programming:'programación'}[mini]) + ' en una ventana.';
      addMsg('sky',reply);
      guardarConsulta('assistant',reply);
      return;
    }
    // Voice/text may OPEN the verified communications panel; never place
    // carrier calls, send texts or enable camera solely from voice commands.
    const openPhone=/^(?:(?:oye|hey)\s+)?(?:sky[,.: ]+)?(?:abr[ií]|abre|abrir|mostr[aá]|mostrar)\s+(?:el\s+|m[oó]dulo\s+de\s+)?(?:tel[eé]fono|llamadas|videoconferencia)(?:\s+de\s+sky)?[.!]?$/i;
    if(openPhone.test(String(texto).trim())){
      addMsg('user',texto);abrirTelefono();
      addMsg('sky','Abrí SKY Teléfono. Verificá tu número y confirmá las operaciones con los controles y el PIN.');
      return;
    }
    enviar(texto, origen === 'voz' ? 'voz' : 'chat');
  }
  async function enviar(texto, modo) {
    texto = String(texto || '').trim();
    if (!texto && adjuntosChat.length) texto = 'Analizá y resumí los archivos adjuntos.';
    if (!texto) return;
    const fileContext = modo === 'chat' ? contextoDeAdjuntos() : '';
    addMsg('user', texto); $('chat-input').value = '';
    S.tEnvio = performance.now();
    setState('thinking', modo === 'voz' ? 'Pensando…' : 'Procesando…');
    // SKY-PERF: voz Y chat reciben deltas de la API; mantener fallback antiguo.
    if (window.ReadableStream) { await enviarStream(texto, modo, fileContext); return; }
    try {
      const data = await api('/api/asistente/mensaje', { method: 'POST', body: JSON.stringify({
        texto, historial: S.historial.slice(-12), modo, dispositivo: 'local', file_context: fileContext }) });
      S.historial.push({ role: 'user', content: texto });
      await responder(data, modo);
      if (fileContext) confirmarEnvioAdjuntos();
    } catch (e) {
      addMsg('sky', 'No pude contactar a SKY: ' + e.message, 'err'); setState('error', 'Sin conexión con SKY');
    }
  }
  async function enviarStream(texto, modo = 'voz', fileContext = '') {
    const voz = modo === 'voz';
    // SKY-STREAM-TIMEOUT: no dejar el HUD en PROCESANDO indefinidamente.
    const control = new AbortController();
    let finalizado = false;
    const aviso = setTimeout(() => {
      if (!finalizado && estado === 'thinking') setState('thinking', 'Ollama sigue procesando la respuesta…');
    }, 12000);
    const limite = setTimeout(() => control.abort(), 90000);
    let acumulado = '', pendiente = '', resto = '', vivo = null;
    const soltarFrases = (forzar) => {
      if (!voz) return;  // texto: nunca iniciar síntesis de voz por los deltas
      const m = pendiente.match(/^[\s\S]*[.!?…:;](?=\s|$)/);
      if (m && m[0].trim().length > 2) { encolar(limpiarParaVoz(m[0])); pendiente = pendiente.slice(m[0].length); }
      if (forzar && pendiente.trim()) { encolar(limpiarParaVoz(pendiente)); pendiente = ''; }
    };
    try {
      const r = await fetch('/api/asistente/stream', {
        method: 'POST', headers: headers(), signal: control.signal,
        body: JSON.stringify({ texto, historial: S.historial.slice(-12), modo, dispositivo: 'local', file_context: fileContext })
      });
      if (!r.ok || !r.body) throw new Error('HTTP ' + r.status);
      S.historial.push({ role: 'user', content: texto });
      const lector = r.body.getReader(), dec = new TextDecoder();
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
            if (!vivo) vivo = addMsg('sky', '', 'live');
            acumulado += ev.delta; vivo.textContent = acumulado; scroll();
            if (voz) { pendiente += ev.delta; soltarFrases(false); }
          }
          if (ev.final) {
            finalizado = true;
            if (vivo) vivo.classList.remove('live');
            if (ev.final.transmitido) {
              if (voz) soltarFrases(true);
              const msg = ev.final.mensaje || acumulado;
              if (vivo) vivo.textContent = msg; else addMsg('sky', msg);
              if (voz && !acumulado && msg) encolar(limpiarParaVoz(msg));
              S.lastSky = msg;
              S.historial.push({ role: 'assistant', content: msg.slice(0, 4000) });
              if (voz) { await speak(''); seguirConversacion(); }
              if (!S.speaking) setState('idle', 'Listo.');
            } else {
              if (vivo && !acumulado.trim()) vivo.remove();
              await responder(ev.final, modo);
            }
            if (fileContext) confirmarEnvioAdjuntos();
            return;
          }
        }
      }
      throw new Error('La conexión terminó sin una respuesta final.');
    } catch (e) {
      if (vivo) vivo.classList.remove('live');
      const mensaje = control.signal.aborted
        ? 'Ollama tardó más de 90 segundos. Probá otra vez o revisá su uso de memoria con ollama ps.'
        : 'SKY no completó la respuesta: ' + e.message;
      addMsg('sky', mensaje, 'err');
      setState('error', 'No se completó la respuesta');
    } finally {
      clearTimeout(aviso);
      clearTimeout(limite);
    }
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
  /* ------------------------------------------------------------------ cycle: real results, one approved action at a time */
  async function cicloUI(data, modo) {
    let plan = data.ciclo;
    if (!plan || !plan.id) { await decir('El ciclo no tiene identificador.'); return; }
    const card = addCard('Ciclo operativo SKY', plan.total + ' pasos · ' + plan.dispositivo);
    const title = el('div', 's', 'SKY ejecutará cada acción únicamente con tu autorización y comprobará el resultado.');
    card.appendChild(title);
    async function abortar() {
      try {
        plan = await api('/api/asistente/ciclo/' + encodeURIComponent(plan.id), { method: 'DELETE' });
        card.appendChild(el('div', 'res', 'Ciclo cancelado.'));
        setState('idle', 'Cancelado');
      } catch (e) { card.appendChild(el('div', 'res bad', e.message)); }
    }
    const cancelar = el('button', 'btn', 'Cancelar ciclo');
    cancelar.type = 'button';
    cancelar.addEventListener('click', () => {
      if (S.pending) S.pending.cancel();
      abortar();
    });
    card.appendChild(cancelar);
    async function verificar() {
      setState('thinking', 'Verificando acción...');
      try {
        plan = await api('/api/asistente/ciclo/' + encodeURIComponent(plan.id) + '/verificar',
          { method: 'POST' });
        card.appendChild(el('div', 's', 'Estado de verificación: ' + plan.state));
        presentar();
      } catch (e) {
        card.appendChild(el('div', 'res bad', 'No se pudo verificar: ' + e.message));
        setState('error', 'Verificación pendiente');
      }
    }
    async function ejecutarPaso() {
      setState('executing', 'Ejecutando paso ' + (plan.cursor + 1));
      try {
        plan = await api('/api/asistente/ciclo/' + encodeURIComponent(plan.id) + '/siguiente', {
          method: 'POST', body: JSON.stringify({ aprobado: true })
        });
        const last = plan.last_step || {};
        card.appendChild(el('div', 'res', 'Paso ' + (plan.cursor || 1) + ': ' + (last.status || plan.state)));
        if (plan.state === 'VERIFIED') await speak('Ciclo completado y verificado.');
        else if (plan.state === 'WAITING_VERIFICATION') await speak('La orden fue enviada, pero todavía no está verificada.');
        else if (plan.state === 'FAILED') await speak('La ejecución falló. Detuve los siguientes pasos.');
        presentar();
        refrescarLog(); refrescarTareas();
      } catch (e) {
        card.appendChild(el('div', 'res bad', 'Falló la operación: ' + e.message));
        setState('error', 'No se completó');
      }
    }
    function presentar() {
      if (plan.state === 'READY') {
        const step = plan.steps[plan.cursor];
        if (!step) return;
        const label = 'Paso ' + (plan.cursor + 1) + '/' + plan.total + ': ' + step.label;
        card.appendChild(el('div', 's', label));
        confirmar(card, label, ejecutarPaso, step.risk >= 3);
        setState('idle', 'Esperando autorización');
        if (modo === 'voz') speak('¿Ejecuto el paso ' + (plan.cursor + 1) + '?').catch(() => {});
      } else if (plan.state === 'WAITING_VERIFICATION') {
        const btn = el('button', 'btn primary', 'Comprobar ejecución');
        btn.type = 'button'; btn.addEventListener('click', () => { btn.remove(); verificar(); });
        card.appendChild(btn);
        setState('idle', 'Pendiente de verificación');
      } else if (plan.state === 'VERIFIED') {
        card.appendChild(el('div', 'res', 'Todos los pasos tienen resultado VERIFIED.'));
        const canRemember = plan.steps.every(x => ['status', 'launch_app'].includes(x.action));
        if (canRemember) {
          const field = el('input', 'hab-in');
          field.type = 'text'; field.maxLength = 60;
          field.placeholder = 'Nombre del procedimiento verificado';
          field.setAttribute('aria-label', 'Nombre para recordar el procedimiento');
          const save = el('button', 'btn', 'Recordar procedimiento');
          save.type = 'button';
          save.addEventListener('click', async () => {
            if (field.value.trim().length < 3) {
              card.appendChild(el('div', 'res bad', 'Escribí un nombre de al menos 3 caracteres.'));
              return;
            }
            save.disabled = true;
            try {
              const res = await api('/api/sky/learning/capture', {
                method: 'POST', body: JSON.stringify({
                  cycle_id: plan.id, name: field.value.trim(), approved: true
                })
              });
              card.appendChild(el('div', 'res', 'Procedimiento guardado: ' + res.name +
                '. Podés decir «SKY, repetí procedimiento ' + res.id + '».'));
              save.remove(); field.remove();
            } catch (err) {
              save.disabled = false;
              card.appendChild(el('div', 'res bad', 'No se guardó: ' + err.message));
            }
          });
          card.append(field, save);
        }
        setState('idle', 'Ciclo verificado');
      } else {
        setState('error', 'Ciclo ' + plan.state);
      }
      scroll();
    }
    presentar();
  }

  async function responder(data, modo) {
    if (data.tipo === 'respuesta' || data.tipo === 'local') {
      if (Array.isArray(data.correos) && data.correos.length) {
        const c = addCard('Correos nuevos (' + data.correos.length + ')', 'sin marcar como leídos');
        c.appendChild(el('pre', '', data.correos.map(m => '▸ ' + m.de + ' — ' + m.asunto + '\n   ' + (m.resumen || '').slice(0, 140)).join('\n')));
      }
      if (data.recordatorio || data.proveedor === 'sky-agenda') refrescarAgenda();
      if (data.modulo === 'kpi') abrirKPI(data.kpi);
      if (data.modulo === 'perfil') abrirPerfil();
      if (data.modulo === 'sentinel') abrirSentinel();
      if (data.bloquear_hud) { await decir(data.mensaje || ''); await desbloquear(); return; }
      if (data.modulo === 'habilidades') abrirHabilidades(); else if (ventanas.has('habilidades')) HAB.cargar();
      if (data.imagen) mostrarImagen(data.imagen);
      if (data.modulo === 'auto') abrirAuto();
      else if (ventanas.has('auto')) AUTO.cargar();
      if (data.parada) { if (!data.parada.reanudar) { callar(); if (S.pending) S.pending.cancel(); } tarjetaParada(); setState('error', 'Parada de emergencia'); }
      if (data.aprendizaje && ventanas.has('kpi')) KPI.cargar();
      await decir(data.mensaje || ''); return;
    }
    if (data.tipo === 'error') { setState('error', 'Revisá el motor de IA'); addMsg('sky', data.mensaje || 'Error.', 'err'); await speak('Tengo un problema: ' + (data.mensaje || '').split('.')[0]); return; }
    if (data.tipo === 'ciclo') { await cicloUI(data, modo); return; }
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
    const card = addCard('▸ ' + p.description, 'acción · ' + p.action + (data.nivel_riesgo ? ' · nivel ' + data.nivel_riesgo + ' ' + ['', '(bajo)', '(moderado)', '(alto: confirmación obligatoria)'][data.nivel_riesgo] : ''));
    if (data.ejecucion) {
      renderResult(card, data.ejecucion); setState('idle', 'Listo.');
      await speak(resultText(data.ejecucion)); refrescarLog(); seguirConversacion(); return;
    }
    if (data.aviso) { card.appendChild(el('div', 'note', data.aviso)); setState('idle', 'Permiso desactivado');
      await speak('Esa función está desactivada en tu equipo. Te dejé cómo activarla.'); seguirConversacion(); return; }
    confirmar(card, p.description, () => ejecutar(p, card, data.aprender), (data.nivel_riesgo || 0) >= 3);
    setState('idle', 'Esperando tu confirmación');
    if (modo === 'voz') { await speak('¿Lo hago? ' + p.description + '.'); if (S.conv || modo === 'voz') escuchar(); }
  }
  function tarjetaParada() {
    const card = addCard('⏹ Parada de emergencia activa', 'Ninguna acción se ejecuta en tus equipos ni en tu casa hasta que la levantes.');
    const btns = el('div', 'btns');
    const b = el('button', 'btn primary', 'Reanudar'); b.type = 'button';
    b.addEventListener('click', async () => {
      try { await api('/api/asistente/emergencia', { method: 'DELETE' }); btns.remove(); card.appendChild(el('div', 'res', 'Reanudado. Vuelvo a actuar según tus permisos.')); setState('idle', 'Listo.'); S.paradaVista = false; refrescarEstado(); }
      catch (e) { card.appendChild(el('div', 'res bad', 'No pude reanudar: ' + e.message)); }
    });
    btns.appendChild(b); card.appendChild(btns); scroll();
  }
  function kpiEvento(tipo, nombre, ms, ok = true) {
    api('/api/hud/kpi/evento', { method: 'POST', body: JSON.stringify({ tipo, nombre, ms: ms == null ? null : Math.round(ms), ok }) }).catch(() => {});
  }
  function confirmar(card, desc, run, soloClic = false) {
    const btns = el('div', 'btns');
    const si = el('button', 'btn primary', 'Ejecutar'); si.type = 'button';
    const no = el('button', 'btn', 'Cancelar'); no.type = 'button';
    btns.append(si, no); card.appendChild(btns); scroll();
    const pend = {
      run: () => { btns.remove(); S.pending = null; run(); },
      cancel: () => { btns.remove(); S.pending = null; card.appendChild(el('div', 's', 'Cancelado.')); setState('idle', 'Listo.'); kpiEvento('tarea', 'cancelada'); },
      soloClic,
    };
    si.addEventListener('click', pend.run); no.addEventListener('click', pend.cancel);
    S.pending = pend;
  }
  async function ejecutar(p, card, frase) {
    setState('executing', p.description);
    try {
      const cuerpo = { action: p.action, params: p.params, dispositivo: 'local' };
      if (frase) cuerpo.frase = String(frase).slice(0, 120);
      const res = await api('/api/asistente/ejecutar', { method: 'POST', body: JSON.stringify(cuerpo) });
      renderResult(card, res); setState('idle', 'Listo.');
      if (res && res.aprendido_ahora) card.appendChild(el('div', 's', 'Aprendido: la próxima vez lo hago al instante.'));
      await speak(resultText(res));
    } catch (e) { renderResult(card, { ok: false, error: e.message }); setState('error', 'No se completó'); await speak('No se pudo: ' + e.message); }
    refrescarLog(); refrescarTareas(); refrescarNotas(); seguirConversacion();
  }
  async function casaOrden(data, modo) {
    const p = data.propuesta;
    const card = addCard('▸ ' + p.description, 'casa · ' + p.service + (data.nivel_riesgo ? ' · nivel ' + data.nivel_riesgo : ''));
    const correr = async () => {
      setState('executing', p.description);
      try {
        const r = await api('/api/asistente/casa', { method: 'POST', body: JSON.stringify({ service: p.service, entity_ids: p.entity_ids, data: p.data || {}, frase: (data.aprender || '').slice(0, 120) }) });
        renderResult(card, r); setState('idle', 'Listo.'); await speak('Listo.');
      } catch (e) { renderResult(card, { ok: false, error: e.message }); setState('error', 'Casa'); }
      refrescarCasa(); seguirConversacion();
    };
    if (data.ejecucion) { renderResult(card, data.ejecucion); setState('idle', 'Listo.'); await speak(data.ejecucion.ok === false ? 'No pude.' : 'Listo.'); seguirConversacion(); return; }
    confirmar(card, p.description, correr, (data.nivel_riesgo || 0) >= 3);
    if (modo === 'voz') { await speak('¿Confirmás? ' + p.description + '.'); escuchar(); }
  }

  async function correoOrden(data, modo) {
    const b = data.borrador;
    const card = addCard('▸ ' + data.mensaje, 'correo · para ' + b.para);
    card.appendChild(el('pre', '', 'Asunto: ' + b.asunto + '\n\n' + b.cuerpo));
    confirmar(card, data.mensaje, async () => {
      setState('executing', 'Enviando correo');
      try {
        const r = await api('/api/asistente/correo', { method: 'POST', body: JSON.stringify(data.borrador_id ? { ...b, borrador_id: data.borrador_id } : b) });
        renderResult(card, r); setState('idle', 'Listo.'); await speak(r.message || 'Enviado.');
      } catch (e) { renderResult(card, { ok: false, error: e.message }); setState('error', 'Correo'); }
      seguirConversacion();
    }, true);
    setState('idle', 'Revisá el correo antes de enviarlo');
    if (modo === 'voz') { await speak('Te dejé el borrador. Revisalo y tocá Ejecutar para enviarlo.'); }
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
  function cerrarVentana(id) {
    const w = ventanas.get(id);
    if (!w) return;
    if (id === 'sky-text-box') {
      const center = document.querySelector('.center');
      center.append(feed, $('chat-form'));
    }
    w.el.remove(); ventanas.delete(id); dock();
  }
  function enfocar(id) { const w = ventanas.get(id); if (w) { w.el.style.zIndex = ++zTop; dock(id); } }
  // Solo accesos internos conocidos. No abrir enlaces arbitrarios por un texto.
  function ordenVentanaLocal(sentence) {
    const s = String(sentence || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim()
      .replace(/^(oye|hey)\s+/,'').replace(/^sky[,.:\s-]+/,'');
    if (!/^(abre|abri|abrir|mostra|muestra|mostrar)\s+/.test(s)) return null;
    const target=s.replace(/^(abre|abri|abrir|mostra|muestra|mostrar)\s+/,'')
      .replace(/\s+(en\s+)?(una\s+)?(ventana|ventanita|cuadro)\s+(pequena|mini|flotante).*$/,'')
      .replace(/^(?:(?:en\s+)?(?:una\s+)?(?:ventana|ventanita)\s+(?:pequena|mini|flotante)\s+)+/,'')
      .replace(/^(un|una|el|la|mis)\s+/,'').trim();
    if (/^(cuadro\s+de\s+texto|chat|texto|conversacion)$/.test(target) ||
        /^(?:panel\s+(?:de\s+)?)?(?:chat|conversacion|texto)(?:\s+de\s+sky)?$/.test(target) ||
        target === 'panel de sky') return 'chat';
    if (/^(historial|historial\s+de\s+(conversaciones|consultas)|consultas)$/.test(target)) return 'history';
    if (/^(estudio\s+creativo|creativo|creacion\s+de\s+(imagenes|videos))$/.test(target)) return 'creative';
    if (/^(diagnostico|estado\s+del\s+sistema)$/.test(target)) return 'diagnostic';
    if (/^(programacion|developer)$/.test(target)) return 'programming';
    return null;
  }
  function abrirCuadroTexto() {
    const content = el('div','sky-mini-chat');
    abrirVentana('sky-text-box','SKY · Escribir y conversar',content,{w:530,h:450});
    if (!content.parentElement) return;
    content.append(feed, $('chat-form'));
    $('chat-input').focus();
  }
  async function abrirHistorial() {
    if (ventanas.has('sky-full-history')) {
      ventanas.get('sky-full-history').el.classList.remove('hidden');
      enfocar('sky-full-history'); return;
    }
    const pane = el('div','sky-history');
    const search = el('input','sky-history-search');
    search.placeholder='Buscar entre todas las consultas guardadas'; search.maxLength=100;
    search.setAttribute('aria-label','Buscar historial');
    const list=el('div','sky-history-list'), more=el('button','btn','Cargar consultas anteriores');
    more.type='button'; let before=null,moreAvailable=true;
    pane.append(search,list,more);
    abrirVentana('sky-full-history','SKY · Historial persistente',pane,{w:610,h:490});
    async function load(reset=false) {
      if (reset) { before=null;moreAvailable=true;list.replaceChildren(); }
      if (!moreAvailable) return;
      more.disabled=true;more.textContent='Cargando…';
      try {
        const params=new URLSearchParams({limit:'60'});
        if (before) params.set('before',String(before));
        if (search.value.trim()) params.set('q',search.value.trim());
        const data=await api('/api/hud/historial?'+params.toString());
        for(const entry of data.entries) {
          const item=el('article','sky-history-entry');
          const stamp=el('small','',new Date(entry.created_at).toLocaleString()+' · '+
            (entry.role==='user'?'Consulta':'SKY')+' · '+entry.source);
          const content=el('p','',entry.text);
          item.append(stamp,content);list.append(item);
        }
        before=data.next_before;moreAvailable=data.has_more;
        if (!data.entries.length && !list.children.length) list.append(el('p','',
          'Todavía no hay consultas guardadas en este equipo.'));
      } catch(err) {list.append(el('p','', 'No se pudo consultar el historial: '+err.message));}
      more.hidden=!moreAvailable;more.disabled=false;more.textContent='Cargar consultas anteriores';
    }
    more.onclick=()=>load();
    search.addEventListener('change',()=>load(true));
    load(true);
  }
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
    else if (sub === 'close_panel') {   // la ventana visible que está más arriba
      let top = null, z = -1;
      ventanas.forEach((w, id) => { const zi = +w.el.style.zIndex || 0; if (!w.el.classList.contains('hidden') && zi > z) { z = zi; top = id; } });
      if (top) cerrarVentana(top);
    }
    else if (sub.startsWith('close_')) {
      const grupo = { close_docs: ['office'], close_modules: [...ventanas.keys()], close_projects: ['flows'], close_chat: ['clasico'] }[sub]
        || [sub.slice(6)];
      grupo.forEach(cerrarVentana);
    }
    dock();
  }

  /* ------------------------------------------------------------------ SKY Developer: ejecución opt-in */
  const DEV = {root: null};
  function abrirProgramacion(){
    if(!DEV.root || !ventanas.has('programacion')) DEV.root=el('div','kpi');
    abrirVentana('programacion','SKY Developer · Compilación verificada',DEV.root,{w:940,h:720});
    if(DEV.root.dataset.ready==='1')return;
    DEV.root.dataset.ready='1';
    const root=DEV.root;
    const intro=seccion(root,'Crear, compilar y probar código');
    intro.append(el('div','s','SKY ejecuta únicamente en contenedores Docker locales previamente descargados, sin red ni carpetas personales. Requiere activación del dueño, PIN y aprobación para cada ejecución.'));
    const state=el('div','res','Consultando ejecutores…');intro.append(state);
    const area=seccion(root,'Código fuente y pruebas');
    const lang=el('select','hab-in'),code=el('textarea','hab-in');
    const tests=el('textarea','hab-in'),expected=el('input','hab-in');
    const webFiles=el('div','kpi'),cssEditor=el('textarea','hab-in'),jsEditor=el('textarea','hab-in');
    cssEditor.rows=7;cssEditor.spellcheck=false;cssEditor.placeholder='styles.css · CSS3 responsivo';
    jsEditor.rows=7;jsEditor.spellcheck=false;jsEditor.placeholder='app.js · JavaScript del navegador';
    webFiles.append(el('div','s','CSS3 · styles.css'),cssEditor,
                    el('div','s','JavaScript · app.js'),jsEditor);
    webFiles.hidden=true;
    code.rows=12;code.spellcheck=false;code.placeholder='Escribí el código del archivo principal…';
    tests.rows=4;tests.spellcheck=false;
    tests.placeholder='Pruebas opcionales (Python unittest o JavaScript node --test)';
    expected.type='text';expected.placeholder='Salida esperada (opcional, sin distinguir espacios extremos)';
    const actions=el('div','btns');
    const check=el('button','btn','Verificar compiladores');
    const run=el('button','btn primary','Validar / compilar / ejecutar');
    const preview=el('button','btn','Vista previa web');preview.type='button';
    check.type='button';run.type='button';
    actions.append(check,preview,run);
    const output=el('pre','res','Las pruebas físicas no se presumen: mirá el resultado verificable aquí.');
    output.style.whiteSpace='pre-wrap';output.style.overflowWrap='anywhere';
    area.append(lang,code,webFiles,tests,expected,actions,output);
    /* SKY Design Studio: real package manifests and source export, never silent installs. */
    const designArea=seccion(root,'SKY Design Studio · Sitios y apps animadas');
    designArea.append(el('div','s','Creá una interfaz con identidad, temática relevante, iconos y transiciones. Las bibliotecas pertenecen al proyecto generado; compilar requiere el SDK y tu aprobación.'));
    const designFields=el('div','kpi-bar');
    const designTitle=el('input','hab-in'),designBrief=el('textarea','hab-in');
    designTitle.type='text';designTitle.maxLength=90;designTitle.value='Mi experiencia digital';
    designTitle.placeholder='Nombre de la web o app';
    designBrief.rows=3;designBrief.maxLength=500;
    designBrief.placeholder='Describí a quién va dirigida, objetivo y funciones. Ejemplo: turismo de naturaleza para familias';
    const designPlatform=el('select','hab-in'),designStyle=el('select','hab-in'),designLayout=el('select','hab-in');
    [['react','Web · React + Motion + Lucide + Inter'],['flutter','App · Flutter + flutter_animate']].forEach(([v,l])=>{
      const o=el('option','',l);o.value=v;designPlatform.append(o);
    });
    [['auto','Estilo elegido por SKY'],['aurora','Aurora neón'],['ember','Luz cálida'],['monochrome','Minimal futurista']].forEach(([v,l])=>{
      const o=el('option','',l);o.value=v;designStyle.append(o);
    });
    [['auto','Distribución personalizada'],['editorial','Editorial'],['dashboard','Dashboard'],['immersive','Inmersiva']].forEach(([v,l])=>{
      const o=el('option','',l);o.value=v;designLayout.append(o);
    });
    const iconPack=el('select','hab-in'), fontPack=el('select','hab-in'), motionMode=el('select','hab-in');
    [['lucide','Iconos · Lucide SVG'],['tabler','Iconos · Tabler SVG']].forEach(([v,l])=>{
      const o=el('option','',l);o.value=v;iconPack.append(o);
    });
    [['inter','Tipografía · Inter'],['manrope','Tipografía · Manrope'],
     ['poppins','Tipografía · Poppins']].forEach(([v,l])=>{
      const o=el('option','',l);o.value=v;fontPack.append(o);
    });
    [['normal','Animaciones fluidas'],['none','Sin animación (accesibilidad)']].forEach(([v,l])=>{
      const o=el('option','',l);o.value=v;motionMode.append(o);
    });
    function updateDesignLibraryChoices(){
      const flutter=designPlatform.value==='flutter';
      iconPack.disabled=flutter;fontPack.disabled=flutter;
      if(flutter){iconPack.value='lucide';fontPack.value='inter';}
    }
    designPlatform.addEventListener('change',updateDesignLibraryChoices);
    updateDesignLibraryChoices();
    designFields.append(designTitle,designBrief,designPlatform,designStyle,designLayout,
                        iconPack,fontPack,motionMode);
    const designBtns=el('div','btns'),designCreate=el('button','btn primary','Crear diseño real');
    const designDownload=el('button','btn','Descargar proyecto ZIP');
    const designAI=el('button','btn','Diseñar con IA');designAI.type='button';
    const modelProvider=el('select','hab-in'),cloudOk=el('input');
    cloudOk.type='checkbox';cloudOk.checked=false;
    [['ollama','Ollama local (sin nube)'],['openai','OpenAI'],['anthropic','Claude (Anthropic)'],
     ['gemini','Gemini'],['mistral','Mistral'],['groq','Groq'],['deepseek','DeepSeek']].forEach(
      ([v,label])=>{const o=el('option','',label);o.value=v;modelProvider.append(o);});
    const cloudLabel=el('label','s',' Autorizo enviar SOLO nombre y descripción del diseño al proveedor externo seleccionado.');
    cloudLabel.prepend(cloudOk);
    cloudLabel.style.display='flex';cloudLabel.style.alignItems='center';cloudLabel.style.gap='7px';
    designCreate.type='button';designDownload.type='button';
    designDownload.disabled=true;designBtns.append(designCreate,designAI,designDownload);
    const designResult=el('pre','res','Generá el proyecto y comprobá sus dependencias. No equivale a compilarlo.');
    designResult.style.whiteSpace='pre-wrap';designResult.style.overflowWrap='anywhere';
    designArea.append(designFields,modelProvider,cloudLabel,designBtns,designResult);
    let currentDesign=null, currentDesignArgs=null, currentDesignPlan=null;
    function designPayload(){
      return {title:designTitle.value,brief:designBrief.value,platform:designPlatform.value,
              style:designStyle.value,layout:designLayout.value,
              icon_pack:iconPack.value,font_family:fontPack.value,motion:motionMode.value};
    }
    designCreate.addEventListener('click',async()=>{
      designCreate.disabled=true;designDownload.disabled=true;
      currentDesign=null;currentDesignArgs=null;currentDesignPlan=null;
      designResult.textContent='Generando archivos de diseño…';
      try {
        const payload=designPayload();
        const result=await api('/api/developer/design/create',{
          method:'POST',body:JSON.stringify(payload)});
        currentDesign=result;currentDesignArgs=payload;
        designResult.textContent='Plataforma: '+result.platform+
          '\nSector identificado: '+result.domain+
          '\nEstilo: '+result.style+' · estructura: '+result.layout+
          '\nColores: '+JSON.stringify(result.colors)+
          '\nArchivos editables: '+Object.keys(result.files).join(', ')+
          '\nPaquetes de diseño elegidos: '+JSON.stringify(result.selected_libraries)+
          '\nBibliotecas reales declaradas: '+JSON.stringify(result.libraries_declared,null,2)+
          '\nComprobaciones necesarias:\n'+result.commands_to_test_in_separate_approved_project.join('\n')+
          '\n\nIMPORTANTE: los archivos se generaron, pero NO se han compilado en tu equipo.';
        designDownload.disabled=false;
      }catch(e){designResult.textContent='Error de diseño: '+e.message;}
      finally{designCreate.disabled=false;}
    });
    designAI.addEventListener('click',async()=>{
      const cloud=modelProvider.value!=='ollama';
      if(cloud&&!cloudOk.checked){
        designResult.textContent='Para usar un modelo externo debés marcar el consentimiento de nube.';
        return;
      }
      if(!confirm('¿Autorizás la consulta a '+modelProvider.value+' con el nombre y descripción del diseño? SKY no enviará archivos ni credenciales.'))return;
      designAI.disabled=true;designDownload.disabled=true;
      currentDesign=null;currentDesignArgs=null;currentDesignPlan=null;
      try{
        const args=designPayload();
        const d=await api('/api/developer/design/ai/create',{
          method:'POST',body:JSON.stringify({...args,approved:true,
            provider:modelProvider.value,allow_cloud:cloud&&cloudOk.checked})});
        currentDesign=d;currentDesignArgs=args;currentDesignPlan=d.design_plan;
        designResult.textContent='Diseño dirigido por IA real: '+d.provider_used+'/'+d.model_used+
          '\nNube usada: '+(d.cloud_used?'sí, autorizada':'no')+
          '\nPropuesta creativa: '+d.design_plan.subtitle+
          '\nDescripción: '+d.design_plan.description+
          '\nComponentes: '+d.design_plan.features.map(x=>x.title+' — '+x.detail).join('; ')+
          '\nEstilo: '+d.style+'; distribución: '+d.layout+
          '\nPaquetes seleccionados: '+JSON.stringify(d.selected_libraries)+
          '\nBibliotecas declaradas: '+JSON.stringify(d.libraries_declared)+
          '\nGeneración estructurada: SÍ. SDK instalado en este equipo: NO comprobado.'+
          '\nCompilación física de este diseño: NO realizada.';
        designDownload.disabled=false;
      }catch(e){designResult.textContent='No se pudo diseñar con IA: '+e.message;}
      finally{designAI.disabled=false;}
    });
    designDownload.addEventListener('click',async()=>{
      if(!currentDesignArgs||!currentDesign)return;
      designDownload.disabled=true;
      try{
        const downloadPayload={...currentDesignArgs};
        if(currentDesignPlan)downloadPayload.design_plan=currentDesignPlan;
        const r=await fetch('/api/developer/design/download',{
          method:'POST',headers:headers(),body:JSON.stringify(downloadPayload)});
        if(!r.ok){
          let detail='Error HTTP '+r.status;
          try{const j=await r.json();detail=j.detail||detail;}catch{/* binary or non-json */}
          throw new Error(detail);
        }
        const blob=await r.blob();
        if(blob.size<100)throw new Error('El ZIP descargado parece estar vacío.');
        const address=URL.createObjectURL(blob);
        const link=document.createElement('a');
        link.href=address;link.download='sky-design-'+currentDesignArgs.platform+'.zip';
        document.body.appendChild(link);link.click();link.remove();
        setTimeout(()=>URL.revokeObjectURL(address),1500);
      }catch(e){designResult.textContent+=' \nNo se pudo descargar: '+e.message;}
      finally{designDownload.disabled=false;}
    });

    /* Guided software engineering. No library/IDE is installed by browsing a catalogue. */
    const workbench=seccion(root,'Ecosistema de desarrollo · proyectos, SDK, bibliotecas y explicación');
    workbench.append(el('div','s','Explorá referencias oficiales o comprobá tu entorno; una referencia no significa que la herramienta esté instalada o que sea segura.'));
    const browseRow=el('div','btns');
    const cat=el('select','hab-in');
    [['frameworks','Frameworks'],['databases','Bases de datos'],['ides','IDE / editores'],
     ['icons','Bibliotecas de iconos'],['fonts','Tipografías'],['languages','Lenguajes']].forEach(
       ([value,label])=>{const opt=el('option','',label);opt.value=value;cat.append(opt);});
    const searchTech=el('input','hab-in');searchTech.placeholder='Buscar tecnología por nombre';searchTech.maxLength=100;
    const browse=el('button','btn','Buscar catálogo');
    const readiness=el('button','btn','Revisar SDK / IDE');
    const starter=el('button','btn','Crear base HTML5/CSS3/JS');
    [browse,readiness,starter].forEach(b=>{b.type='button';});
    browseRow.append(cat,searchTech,browse,readiness,starter);
    const techResult=el('pre','res','Catálogo consultable sin instalaciones ni cambios en tu equipo.');
    techResult.style.whiteSpace='pre-wrap';techResult.style.overflowWrap='anywhere';
    workbench.append(browseRow,techResult);
    browse.addEventListener('click',async()=>{
      browse.disabled=true;
      try{
        const path='/api/developer/workbench/catalogue?category='+encodeURIComponent(cat.value)
                   +'&query='+encodeURIComponent(searchTech.value)+'&limit=70';
        const d=await api(path);
        techResult.textContent=(d.items||[]).map(x=>x.name+' · '+(x.official_docs||'sin enlace oficial')+
          '\n  Estado: '+x.status+' · perfil Docker: '+(x.docker_profile_defined?'definido':'sin perfil')).join('\n\n')
          || 'No se encontraron referencias con ese nombre.';
        techResult.textContent+='\n\nNota: este resultado NO acredita instalación ni pruebas.';
      }catch(e){techResult.textContent='Error de catálogo: '+e.message;}
      finally{browse.disabled=false;}
    });
    readiness.addEventListener('click',async()=>{
      readiness.disabled=true;
      try{
        const d=await api('/api/developer/workbench/readiness');
        techResult.textContent='Entorno: '+d.host_platform+'\n'+
          (d.tools||[]).map(x=>x.tool+' → '+x.state).join('\n')+
          '\n\nLas herramientas fuera del PATH pueden existir, pero no están verificadas.';
      }catch(e){techResult.textContent='Error SDK: '+e.message;}
      finally{readiness.disabled=false;}
    });
    starter.addEventListener('click',async()=>{
      starter.disabled=true;
      try{
        const d=await api('/api/developer/workbench/starter/web',{
          method:'POST',body:JSON.stringify({title:'Mi proyecto SKY',subtitle:'Sitio web interactivo creado con SKY'})});
        if(!profiles.has('Web'))throw Error('El perfil Web no se cargó.');
        lang.value='Web';syncLanguage();
        code.value=d.files['index.html'];
        cssEditor.value=d.files['styles.css'];jsEditor.value=d.files['app.js'];
        techResult.textContent='Plantilla cargada en los tres editores. Aún NO fue compilada ni comprobada. Ejecutá la validación con tu PIN.';
      }catch(e){techResult.textContent='Error plantilla: '+e.message;}
      finally{starter.disabled=false;}
    });
    const packageArea=el('details');
    packageArea.append(el('summary','','Buscar paquetes reales · npm / PyPI / pub.dev (opcional)'));
    const packageRow=el('div','btns'),registry=el('select','hab-in'),pkgName=el('input','hab-in');
    [['npm','npm · JavaScript / iconos'],['pypi','PyPI · Python'],['pub','pub.dev · Flutter/Dart']].forEach(
      ([v,label])=>{const opt=el('option','',label);opt.value=v;registry.append(opt);});
    pkgName.placeholder='Ej. lucide-react, fastapi, google_fonts';pkgName.maxLength=110;
    const lookup=el('button','btn','Verificar metadatos');lookup.type='button';
    const pkgOutput=el('pre','res','Consulta pública y voluntaria, sin instalar paquetes.');
    pkgOutput.style.whiteSpace='pre-wrap';
    packageRow.append(registry,pkgName,lookup);packageArea.append(packageRow,pkgOutput);
    workbench.append(packageArea);
    lookup.addEventListener('click',async()=>{
      lookup.disabled=true;
      try{
        if(!confirm('¿Querés consultar el nombre del paquete en su registro público oficial? No se instalará.'))return;
        const d=await api('/api/developer/workbench/packages/lookup?registry='+
          encodeURIComponent(registry.value)+'&name='+encodeURIComponent(pkgName.value));
        pkgOutput.textContent='Paquete: '+d.package+'\nVersión reportada: '+d.latest_reported+
          '\nDescripción: '+d.description+'\nFuente: '+d.source_url+
          '\nLicencia verificada: NO · vulnerabilidades auditadas: NO · instalado: NO';
      }catch(e){pkgOutput.textContent='No verificado: '+e.message;}
      finally{lookup.disabled=false;}
    });
    const guideArea=el('details');
    guideArea.append(el('summary','','Explicar cada línea de código · sin modificar el original'));
    const explainRow=el('div','btns'),fileFocus=el('select','hab-in');
    const explain=el('button','btn','Explicar siguientes 80 líneas');explain.type='button';
    const lesson=el('pre','res','Explicación estructural orientativa, no sustituye pruebas ni una auditoría.');
    lesson.style.whiteSpace='pre-wrap';lesson.style.overflowWrap='anywhere';
    explainRow.append(fileFocus,explain);
    guideArea.append(explainRow,lesson);workbench.append(guideArea);
    let guideCursor=1;
    function guideChoice(){
      const choices=lang.value==='Web'
        ?[['HTML','index.html'],['CSS','styles.css'],['JavaScript','app.js']]
        :[[lang.value,profiles.get(lang.value)?.main_file||'Código']];
      fileFocus.replaceChildren();
      choices.forEach(([language,label])=>{
        const opt=el('option','',label);opt.value=language;fileFocus.append(opt);
      });
      guideCursor=1;
    }
    fileFocus.addEventListener('change',()=>{guideCursor=1;lesson.textContent='Listo para explicar desde la primera línea.';});
    explain.addEventListener('click',async()=>{
      explain.disabled=true;
      try{
        const selected=fileFocus.value;
        const source=lang.value==='Web'&&selected==='CSS'?cssEditor.value:
          lang.value==='Web'&&selected==='JavaScript'?jsEditor.value:code.value;
        const d=await api('/api/developer/workbench/explain',{
          method:'POST',body:JSON.stringify({
            language:selected,source,start_line:guideCursor,max_lines:80})});
        const lines=(d.annotations||[]).map(x=>'L'+x.line+'  '+x.code+
          '\n    ↳ '+x.explanation_es).join('\n');
        lesson.textContent=(guideCursor===1?'':lesson.textContent+'\n')+lines+
          (d.has_more?'\n\nContinuá para explicar desde la línea '+d.next_start_line:
            '\n\nExplicación completa en el rango solicitado. Diagnóstico sintáctico: '+
            (d.syntax_checked?(d.syntax_valid?'válido':'inválido'):'no ejecutado'));
        guideCursor=d.next_start_line||1;
      }catch(e){lesson.textContent='Error de explicación: '+e.message;guideCursor=1;}
      finally{explain.disabled=false;}
    });
    const inspectArea=el('details');
    inspectArea.append(el('summary','','Inspeccionar proyecto / dependencias · Flutter, Unity, Android, etc.'));
    inspectArea.append(el('div','s','Analizá los archivos del editor actual o pegá un JSON de rutas→contenido. No ingresés .env, claves, contraseñas ni información privada.'));
    const projectMap=el('textarea','hab-in');
    projectMap.rows=5;projectMap.spellcheck=false;
    projectMap.placeholder='Opcional: {"package.json":"{\"dependencies\":{\"react\":\"^19\"}}"}';
    const inspectBtn=el('button','btn','Analizar proyecto sin ejecutar');inspectBtn.type='button';
    const inspectResult=el('pre','res','Inspección estática: no instala dependencias ni abre archivos de la computadora.');
    inspectResult.style.whiteSpace='pre-wrap';inspectResult.style.overflowWrap='anywhere';
    inspectArea.append(projectMap,inspectBtn,inspectResult);workbench.append(inspectArea);
    inspectBtn.addEventListener('click',async()=>{
      inspectBtn.disabled=true;
      try{
        const files=projectMap.value.trim()?JSON.parse(projectMap.value):selection();
        const d=await api('/api/developer/workbench/inspect',{
          method:'POST',body:JSON.stringify({files})});
        inspectResult.textContent='Lenguajes: '+JSON.stringify(d.language_files)+
          '\nFrameworks: '+d.frameworks_detected.join(', ')+
          '\nBases de datos: '+d.databases_detected.join(', ')+
          '\nIDE: '+d.ide_project_hints.join(', ')+
          '\nDependencias detectadas: '+d.dependency_count+
          '\nRecomendaciones:\n'+d.recommended_validation.join('\n')+
          '\nAdvertencias:\n'+d.warnings.join('\n')+
          '\n\nInstalación/compilación/pruebas: NO ejecutadas.';
      }catch(e){inspectResult.textContent='No se pudo inspeccionar: '+e.message;}
      finally{inspectBtn.disabled=false;}
    });

    function syncLanguage(){
      const web=lang.value==='Web';
      webFiles.hidden=!web;preview.hidden=!web && lang.value!=='HTML';
      tests.hidden=web || lang.value==='HTML' || lang.value==='CSS';
      if(web){
        code.placeholder='index.html · HTML5 con <link href="styles.css"> y <script src="app.js">';
        tests.value='';
      }else if(lang.value==='HTML')code.placeholder='index.html · HTML5 semántico, accesible y responsivo';
      else if(lang.value==='CSS')code.placeholder='styles.css · CSS3';
      else code.placeholder='Código principal del lenguaje seleccionado';
    }
    lang.addEventListener('change',()=>{syncLanguage();guideChoice();});
    const profiles=new Map();
    function selection(){
      const p=profiles.get(lang.value);
      if(!p)throw Error('Elegí un lenguaje compatible.');
      const files={[p.main_file]:code.value};
      if(lang.value==='Web'){
        files['styles.css']=cssEditor.value;
        files['app.js']=jsEditor.value;
      }
      if(tests.value.trim()){
        if(lang.value==='Python')files['tests/test_main.py']=tests.value;
        else if(lang.value==='JavaScript')files['tests/main.test.js']=tests.value;
        else throw Error('Este lenguaje no dispone aún de pruebas separadas en el ejecutor.');
      }
      return files;
    }
    async function load(){
      try{
        const d=await api('/api/developer/build/capabilities');
        lang.replaceChildren();
        for(const p of d.supported||[]){
          profiles.set(p.language,p);
          const opt=el('option','',p.language+' · '+p.main_file);
          opt.value=p.language;lang.append(opt);
        }
        syncLanguage();guideChoice();
        state.textContent=d.enabled
          ? 'Ejecución disponible; se exigirá PIN y confirmación.'
          : 'El ejecutor está desactivado. Activá SKY_CODE_RUNNER_ENABLED y SKY_CODE_RUNNER_CONTAINER_ACK en el equipo propietario.';
      }catch(e){state.textContent='No se pudo cargar el catálogo: '+e.message;}
    }
    preview.addEventListener('click',()=>{
      if(!confirm('¿Querés previsualizar HTML, CSS y JavaScript dentro de un iframe aislado? No es una prueba de seguridad ni compatibilidad entre navegadores.'))return;
      const rootHTML=code.value||'<!doctype html><html><head><title>SKY</title></head><body></body></html>';
      const csp='<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; img-src data:; script-src &apos;unsafe-inline&apos;; style-src &apos;unsafe-inline&apos;; connect-src &apos;none&apos;; form-action &apos;none&apos;; base-uri &apos;none&apos;">';
      const pageCSS=lang.value==='Web'?cssEditor.value:'';
      const pageJS=lang.value==='Web'?jsEditor.value:'';
      const inlineStyle='<style>'+pageCSS.replace(/<\/style/gi,'<\\/style')+'</style>';
      const inlineScript='<script>'+pageJS.replace(/<\/script/gi,'<\\/script')+'</script>';
      const withHead=rootHTML.replace(/<head(?:\s[^>]*)?>/i,match=>match+csp+inlineStyle);
      const secured=withHead===rootHTML?csp+inlineStyle+rootHTML:withHead;
      const documentText=lang.value==='Web'
        ?secured.replace(/<\/body\s*>/i,inlineScript+'</body>'):secured;
      const sandbox=el('iframe');
      sandbox.setAttribute('sandbox','allow-scripts');
      sandbox.setAttribute('referrerpolicy','no-referrer');
      sandbox.style.width='100%';sandbox.style.height='420px';sandbox.style.border='0';
      sandbox.srcdoc=documentText;
      const panel=el('div','kpi');
      panel.append(el('div','s','Vista preliminar sin conexión y con origen aislado; no equivale a prueba en navegador real.'),sandbox);
      abrirVentana('sky-web-preview','SKY · Vista previa HTML5/CSS3',panel,{w:960,h:620});
    });
    check.addEventListener('click',async()=>{
      check.disabled=true;
      try{
        const d=await api('/api/developer/toolchains?language='+encodeURIComponent(lang.value));
        output.textContent=JSON.stringify(d.checks||[],null,2)+
          '\nNota: compilador detectado ≠ código compilado.';
      }catch(e){output.textContent='Error: '+e.message;}
      finally{check.disabled=false;}
    });
    run.addEventListener('click',async()=>{
      if(!confirm('¿Autorizás ejecutar este código en el contenedor Docker aislado del equipo propietario?'))return;
      run.disabled=true;output.textContent='Compilando y verificando resultado…';
      try{
        const payload={language:lang.value,files:selection(),approved:true};
        if(expected.value.trim())payload.expected_stdout=expected.value.trim();
        const d=await api('/api/developer/build/execute',{
          method:'POST',body:JSON.stringify(payload)});
        output.textContent='ESTADO: '+d.status+'\nImagen local: '+d.image_id+
          '\nCOMPILACIÓN:\n'+JSON.stringify(d.compile,null,2)+
          '\nEJECUCIÓN:\n'+JSON.stringify(d.run,null,2)+
          '\nPRUEBAS:\n'+JSON.stringify(d.tests,null,2);
      }catch(e){output.textContent='No se pudo ejecutar: '+e.message;}
      finally{run.disabled=false;}
    });
    load();
  }

  /* ------------------------------------------------------------------ módulos */
  const MODULOS = [
    { id: 'clasico', t: 'Clásico', d: 'Chat multi-IA, adjuntos, imágenes y búsqueda', url: '/sky' },
    { id: 'aula', t: 'Docencia', d: 'Clases con voz, videos, 3D y evaluación por tres saberes', accion: () => abrirAula() },
    { id: 'programacion', t: 'Programación', d: 'Compilar y probar código en Docker aislado, con tu autorización', accion: () => abrirProgramacion() },
    { id: 'telefono', t: 'Teléfono', d: 'Verificar número, SMS, llamadas y video autorizados', accion: () => abrirTelefono() },
    { id: 'creative', t: 'Creative', d: 'Video, animación y edición por capas', url: '/creative' },
    { id: 'office', t: 'Office', d: 'Word, Excel, PowerPoint y PDF', url: '/office' },
    { id: 'flows', t: 'Flujos', d: 'Automatizaciones con aprobación', url: '/flows' },
    { id: 'world', t: 'Metaverso', d: 'Mundos 3D y escenas', url: '/world' },
    { id: 'studio', t: 'Studio 3D', d: 'Foto a modelo GLB', url: '/studio' },
    { id: 'community', t: 'Comunidad', d: 'Espacios compartidos', url: '/community' },
    { id: 'negocio', t: 'BAQUEANO', d: 'Panel de negocio del dueño', url: '/owner/baqueano' },
    { id: 'player', t: 'Reproductor', d: 'YouTube dentro de SKY', accion: () => preguntarReproducir() },
    { id: 'kpi', t: 'Rendimiento', d: 'KPIs reales, fallos y aprendizaje', accion: () => abrirKPI() },
    { id: 'auto', t: 'Automatización', d: 'Tareas programadas, skills, borradores y WhatsApp', accion: () => abrirAuto() },
    { id: 'perfil', t: 'Perfil', d: 'Quién sos: SKY lo lee en cada respuesta', accion: () => abrirPerfil() },
    { id: 'habilidades', t: 'Habilidades', d: 'Catálogo, Skill Builder e integraciones', accion: () => abrirHabilidades() },
    { id: 'sentinel', t: 'Seguridad', d: 'SKY SENTINEL: PIN, accesos, dispositivos y emergencia', accion: () => abrirSentinel() },
    { id: 'streamlit', t: 'Panel técnico', d: 'Panel heredado dentro de SKY, únicamente al solicitarlo', accion: () => abrirModuloTecnico('tablero') },
  ];
  // Los 27 módulos heredados se presentan aquí, pero jamás se cargan al iniciar.
  // El catálogo original de atajos del HUD se conserva bajo "Herramientas avanzadas".
  let modulosTecnicos = [];
  let cursorModulos = null;
  const normalizarModulo = value => String(value || '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ').replace(/\s+/g, ' ').trim();

  function solicitudModulo(sentence) {
    const frase = normalizarModulo(sentence)
      .replace(/^(?:oye |mira |hey )?(?:sky )?/, '');
    if (!/^(?:activa|activar|abre|abri|abrir|inicia|iniciar|muestra|mostra|mostrame|pon|pone|ejecuta)\b/.test(frase)) return null;
    const nombre = frase.replace(/^(?:activa|activar|abre|abri|abrir|inicia|iniciar|muestra|mostra|mostrame|pon|pone|ejecuta)\s+/, '')
      .replace(/^(?:(?:el|la|los|las|modulo|modulos|seccion|panel|de|del)\s+)+/, '');
    const aliases = modulosTecnicos.flatMap(m =>
      [m.title, m.label, ...(m.aliases || [])].map(a => ({id:m.id, nombre:normalizarModulo(a)})));
    aliases.sort((a,b) => b.nombre.length - a.nombre.length);
    return aliases.find(a => nombre === a.nombre || nombre.startsWith(a.nombre + ' '))?.id || null;
  }

  async function abrirModuloTecnico(moduleId) {
    const modulo = modulosTecnicos.find(m => m.id === moduleId);
    if (!modulo) return;
    const winId = 'sky-tecnico-' + moduleId;
    if (ventanas.has(winId)) {
      const win = ventanas.get(winId);
      win.el.classList.remove('hidden'); enfocar(winId); return;
    }
    setState('thinking', 'Activando ' + modulo.title + '…');
    try {
      const abrir = await api('/api/sky/modules/' + encodeURIComponent(moduleId) + '/open', { method: 'POST' });
      if (!abrir.ready) {
        let listo = false;
        for (let i = 0; i < 16; i++) {
          await new Promise(resolve => setTimeout(resolve, 500));
          const estadoModulo = await api('/api/sky/modules/' + encodeURIComponent(moduleId) + '/status');
          if (estadoModulo.ready) { listo = true; break; }
        }
        if (!listo) throw new Error('El módulo aún no está disponible. Revisá el registro de Streamlit.');
      }
      // URL provista por SKY y restringida a rutas conocidas; nunca desde texto arbitrario.
      abrirVentana(winId, modulo.title, abrir.url, { w: 1060, h: 710 });
      if (window.matchMedia('(max-width:900px)').matches) mostrarPanel('core');
      setState('idle', modulo.title + ' activado');
      addMsg('sky', 'Activé el módulo ' + modulo.title + ' dentro de SKY.');
    } catch (err) {
      const detalle = 'No pude activar ' + modulo.title + ': ' + err.message;
      addMsg('sky', detalle, 'err'); setState('error', 'Módulo no disponible');
    }
  }

  async function cargarModulosTecnicos() {
    try {
      const data = await api('/api/sky/modules');
      modulosTecnicos = data.modules || [];
      const cursor = await api('/api/sky/modules/events/latest');
      cursorModulos = cursor.cursor;
      pintarModulos();
      // Recibe órdenes desde la escucha Vosk del servicio local (sin usar otro micrófono).
      setInterval(async () => {
        if (cursorModulos === null) return;
        try {
          const r = await api('/api/sky/modules/events?after=' + cursorModulos);
          for (const evento of r.events || []) {
            cursorModulos = Math.max(cursorModulos, evento.id);
            await abrirModuloTecnico(evento.module_id);
          }
        } catch { /* API temporalmente ocupada: se reintentará */ }
      }, 3000);
    } catch (e) {
      console.warn('Catálogo SKY no disponible:', e.message);
      pintarModulos();
    }
  }

  function pintarModulos() {
    const box = $('tiles'); box.textContent = '';
    document.querySelectorAll('#p-mod > .sky-extra-modules').forEach(el => el.remove());
    for (const m of modulosTecnicos) {
      const b = el('button', 'tile'); b.type = 'button';
      b.appendChild(el('b', '', m.title));
      b.appendChild(el('small', '', m.backend === 'hud'
        ? 'Integrado en el HUD · activar al pedirlo'
        : 'Función original · cargar al pedirla'));
      b.addEventListener('click', () => abrirModuloTecnico(m.id));
      box.appendChild(b);
    }
    // Nunca se retiran atajos ni controles desarrollados previamente.
    const details = el('details', 'sky-extra-modules');
    const summary = el('summary', '', 'Herramientas adicionales de SKY');
    const inner = el('div', 'tiles'); details.append(summary, inner);
    MODULOS.forEach(m => {
      const b = el('button', 'tile'); b.type = 'button';
      b.appendChild(el('b', '', m.t)); b.appendChild(el('small', '', m.d));
      b.addEventListener('click', () => {
        if (m.externo) { window.open(m.externo, '_blank', 'noopener'); return; }
        if (m.accion) { m.accion(); return; }
        abrirVentana(m.id, m.t, m.url);
        if (window.matchMedia('(max-width:900px)').matches) mostrarPanel('core');
      });
      inner.appendChild(b);
    });
    // Antes de autenticar o si la API falla, seguir mostrando lo existente.
    if (!modulosTecnicos.length) {
      details.open = true;
      box.append(...Array.from(inner.children));
    } else {
      $('p-mod').appendChild(details);
    }
  }

  /* ------------------------------------------------------------------ SKY Teléfono, con PIN y consentimiento explícito */
  const PHONE = {root:null, video:null};
  function abrirTelefono() {
    if(!PHONE.root || !ventanas.has('telefono')) PHONE.root=el('div','kpi');
    abrirVentana('telefono','SKY Teléfono · Comunicaciones verificadas',PHONE.root,{w:940,h:720});
    if(PHONE.root.dataset.ready)return;
    PHONE.root.dataset.ready='1';
    const root=PHONE.root;
    const intro=seccion(root,'Tu teléfono, conectado con tu permiso');
    intro.append(el('div','s','SKY no controla la SIM ni sustituye a Claro, Tigo u otra operadora. SMS y llamadas utilizan Twilio; pueden generar cargos. Antes hay que verificar tu número y configurar el PIN SENTINEL.'));
    const status=el('div','res','Comprobando la configuración…');intro.append(status);
    const verify=seccion(root,'1. Verificar tu número personal');
    const phone=el('input','hab-in');phone.type='tel';phone.placeholder='+505XXXXXXXX';
    phone.autocomplete='tel';phone.maxLength=22;phone.setAttribute('aria-label','Tu número con código de país');
    const codeInput=el('input','hab-in');codeInput.type='text';codeInput.inputMode='numeric';
    codeInput.maxLength=10;codeInput.placeholder='Código recibido por SMS';
    const verifyButtons=el('div','btns');
    const request=el('button','btn','Solicitar código');request.type='button';
    const finish=el('button','btn primary','Verificar número');finish.type='button';
    const revoke=el('button','btn','Desvincular mi número');revoke.type='button';
    verifyButtons.append(request,finish,revoke);verify.append(phone,codeInput,verifyButtons);
    const actionSection=seccion(root,'2. Mensaje de texto o llamada telefónica');
    const to=el('input','hab-in');to.type='tel';to.maxLength=22;
    to.placeholder='Destinatario + código de país';to.setAttribute('aria-label','Número de contacto internacional');
    const message=el('textarea','hab-in');message.rows=3;message.maxLength=800;
    message.placeholder='Mensaje SMS (hasta 800 caracteres)';
    const approvalRow=el('div','kpi-bar');
    const consent=el('input','');consent.type='checkbox';consent.id='sky-phone-consent';
    const consentLabel=el('label','', 'Tengo permiso para contactar a este número y entiendo los posibles costos.');
    consentLabel.htmlFor=consent.id;approvalRow.append(consent,consentLabel);
    const send=el('button','btn primary','Enviar SMS real');send.type='button';
    const call=el('button','btn','Iniciar llamada al móvil y conectar');call.type='button';
    const actionButtons=el('div','btns');actionButtons.append(send,call);
    actionSection.append(to,message,approvalRow,actionButtons);
    // Mobile SIM handoff: OS dialer/SMS owns the final call or message.
    const nativeActions=el('div','btns');
    const nativeCall=el('button','btn','Abrir marcador del móvil');
    nativeCall.type='button';
    const nativeSMS=el('button','btn','Abrir SMS del móvil');
    nativeSMS.type='button';
    nativeActions.append(nativeCall,nativeSMS);actionSection.append(nativeActions);
    actionSection.append(el('div','s',
      'Estas opciones abren aplicaciones del teléfono; no envían ni llaman automáticamente. Podés utilizar tu SIM de Claro, Tigo u otra operadora.'));
    async function nativeHandoff(scheme,button){
      button.disabled=true;
      try{
        const check=await api('/api/sky/phone/native/validate?number='+encodeURIComponent(to.value));
        if(!check.allowed)throw Error('Número no permitido por SKY.');
        if(!confirm('¿Abrir la aplicación de '+(scheme==='tel'?'llamadas':'mensajes')+
            ' del dispositivo para '+check.masked+'? Deberás confirmar allí.'))return;
        const target=scheme+':'+check.destination;
        const anchor=el('a','btn','Continuar en la aplicación del móvil');
        anchor.href=target;anchor.rel='noopener';
        status.replaceChildren(document.createTextNode('SKY verificó el número. Tocá este enlace para continuar en tu teléfono: '),anchor);
        status.append(document.createTextNode(' · El sistema del móvil te pedirá confirmar la acción.'));
      }catch(e){status.textContent='No se pudo abrir la aplicación móvil: '+e.message;}
      finally{button.disabled=false;}
    }
    nativeCall.addEventListener('click',()=>nativeHandoff('tel',nativeCall));
    nativeSMS.addEventListener('click',()=>nativeHandoff('sms',nativeSMS));
    actionSection.append(el('div','s','La llamada primero suena en tu teléfono verificado; al contestar se conecta el destinatario. No usa el micrófono del navegador. Una llamada puede cobrar dos tramos.'));
    const blockSection=seccion(root,'3. Bloquear y desbloquear en SKY');
    blockSection.append(el('div','s','El bloqueo impide llamadas y SMS salientes por SKY hacia esos números; no bloquea llamadas de la SIM, Android, iOS ni de la compañía.'));
    const block=el('button','btn','Bloquear destinatario');block.type='button';
    const reload=el('button','btn','Actualizar bloqueos');reload.type='button';
    const blockers=el('div','res','');blockSection.append(block,reload,blockers);
    const video=seccion(root,'4. Videoconferencia dentro de SKY');
    video.append(el('div','s','La videoconferencia funciona por Internet mediante un servicio externo autorizado. Solo comparte micrófono y cámara después de tu permiso en el navegador.'));
    const create=el('button','btn primary','Preparar videoconferencia');create.type='button';
    const enter=el('button','btn','Entrar a la sala');enter.type='button';enter.disabled=true;
    const leave=el('button','btn','Salir y detener cámara');leave.type='button';leave.disabled=true;
    const videoButtons=el('div','btns');videoButtons.append(create,enter,leave);
    const invitation=el('div','res','');const roomHost=el('div','');
    video.append(videoButtons,invitation,roomHost);
    let pendingMeeting=null;
    async function refresh(){
      try{
        const d=await api('/api/sky/phone/status');
        status.textContent='Módulo: '+(d.enabled?'habilitado':'desactivado')+
          ' · Tu número: '+(d.owner_phone_verified?(d.verified_number_masked||'verificado'):'sin verificar')+
          ' · SMS/llamadas de pago: '+(d.paid_actions_enabled?'habilitados':'desactivados')+
          ' · Bloqueados: '+d.blocked_count;
      }catch(e){status.textContent='No pude consultar SKY Teléfono: '+e.message;}
    }
    async function post(path,payload,button){
      button.disabled=true;
      try{return await api('/api/sky/phone'+path,{
        method:'POST',body:JSON.stringify(payload)
      });}
      finally{button.disabled=false;}
    }
    request.addEventListener('click',async()=>{
      try{
        const d=await post('/verify/start',{number:phone.value,approved:true},request);
        status.textContent='Código solicitado a '+d.phone_masked+
          '. Revisá tu SMS; no se verificó todavía.';
      }catch(e){status.textContent=e.message;}
    });
    finish.addEventListener('click',async()=>{
      try{
        const d=await post('/verify/check',{number:phone.value,code:codeInput.value},finish);
        codeInput.value='';
        status.textContent=d.verified?'Número verificado correctamente.':'Código no aprobado. Revisá e intentá otra vez.';
        await refresh();
      }catch(e){status.textContent=e.message;}
    });
    revoke.addEventListener('click',async()=>{
      if(!confirm('¿Desvincular tu número verificado de SKY?'))return;
      try{await post('/verify/revoke',{approved:true},revoke);await refresh();}
      catch(e){status.textContent=e.message;}
    });
    send.addEventListener('click',async()=>{
      if(!consent.checked){status.textContent='Necesitás confirmar el permiso del destinatario.';return;}
      if(!confirm('¿Enviar un SMS real a '+to.value+'? Puede tener costo.'))return;
      try{
        const d=await post('/sms',{to:to.value,message:message.value,
          approved:true,recipient_consented:true},send);
        status.textContent='SMS aceptado por proveedor: '+d.status+
          '. Entrega al destinatario todavía NO verificada.';
      }catch(e){status.textContent=e.message;}
    });
    call.addEventListener('click',async()=>{
      if(!consent.checked){status.textContent='Confirmá primero el consentimiento.';return;}
      if(!confirm('¿Llamar a tu móvil verificado y conectarte con '+to.value+
          '? La llamada tiene costo y usa tu teléfono físico.'))return;
      try{
        const d=await post('/voice/callback',{to:to.value,
          approved:true,recipient_consented:true},call);
        status.textContent='Solicitud: '+d.status+
          '. Atendé tu móvil verificado. La conexión no está confirmada todavía.';
      }catch(e){status.textContent=e.message;}
    });
    block.addEventListener('click',async()=>{
      if(!confirm('¿Bloquear '+to.value+' solamente dentro de SKY?'))return;
      try{
        await post('/blocked',{number:to.value,approved:true},block);
        status.textContent='Bloqueo de SKY actualizado.';await refreshBlocks();await refresh();
      }catch(e){status.textContent=e.message;}
    });
    async function refreshBlocks(){
      blockers.replaceChildren();
      try{
        const d=await api('/api/sky/phone/blocked');
        if(!d.numbers.length)blockers.textContent='Sin números bloqueados.';
        d.numbers.forEach(item=>{
          const row=el('div','kpi-bar');row.append(el('span','',item.masked));
          const unblock=el('button','btn','Desbloquear');unblock.type='button';
          unblock.addEventListener('click',async()=>{
            if(!confirm('¿Permitir nuevamente las operaciones de SKY para '+item.masked+'?'))return;
            unblock.disabled=true;
            try{
              await api('/api/sky/phone/blocked/'+encodeURIComponent(item.id),{
                method:'DELETE',body:JSON.stringify({approved:true})});
              await refreshBlocks();await refresh();
            }catch(e){status.textContent=e.message;unblock.disabled=false;}
          });
          row.append(unblock);blockers.append(row);
        });
      }catch(e){blockers.textContent=e.message;}
    }
    reload.addEventListener('click',refreshBlocks);
    create.addEventListener('click',async()=>{
      if(!confirm('¿Preparar una sala de video externa? Los datos de audio/video se transmitirán al proveedor al ingresar.'))return;
      try{
        pendingMeeting=await post('/video/meeting',{approved:true},create);
        enter.disabled=false;
        invitation.replaceChildren(el('div','s',
          'Sala preparada, todavía sin conexión. Copiá el enlace solo a personas invitadas.'));
        const link=el('a','',pendingMeeting.meeting_url);
        link.href=pendingMeeting.meeting_url;link.rel='noopener noreferrer';link.target='_blank';
        invitation.append(link);
        const copy=el('button','btn','Copiar invitación');copy.type='button';
        copy.addEventListener('click',async()=>{
          try{await navigator.clipboard.writeText(pendingMeeting.meeting_url);
            copy.textContent='Copiado';}
          catch(e){copy.textContent='Copiá el enlace manualmente';}
        });invitation.append(copy);
      }catch(e){status.textContent=e.message;}
    });
    enter.addEventListener('click',async()=>{
      if(!pendingMeeting)return;
      enter.disabled=true;
      try{
        const host=pendingMeeting.host;
        if(!/^[a-z0-9][a-z0-9.-]{3,155}$/.test(host))throw Error('Host de video inválido.');
        if(!window.JitsiMeetExternalAPI){
          const script=document.createElement('script');
          script.src='https://'+host+'/external_api.js';
          script.async=true;
          await new Promise((resolve,reject)=>{
            script.addEventListener('load',resolve,{once:true});
            script.addEventListener('error',()=>reject(Error('No se pudo cargar videoconferencia')),{once:true});
            document.head.append(script);
          });
        }
        roomHost.replaceChildren();
        PHONE.video=new window.JitsiMeetExternalAPI(host,{
          roomName:pendingMeeting.room,parentNode:roomHost,width:'100%',height:490,
          configOverwrite:{prejoinPageEnabled:true,disableInviteFunctions:true}
        });
        leave.disabled=false;status.textContent='Sala externa abierta. Controlá permisos de micrófono y cámara.';
      }catch(e){status.textContent='Video no disponible: '+e.message;enter.disabled=false;}
    });
    leave.addEventListener('click',()=>{
      if(PHONE.video){try{PHONE.video.dispose();}catch(e){/* desactivar vista */}PHONE.video=null;}
      roomHost.replaceChildren();leave.disabled=true;enter.disabled=false;
      status.textContent='Vista de video cerrada en SKY.';
    });
    refresh();refreshBlocks();
  }

  /* ------------------------------------------------------------------ SKY Aula existente: extensión multimedia y evaluativa */
  const AULA = { raiz: null, lesson: null };
  function abrirAula() {
    if (!AULA.raiz || !ventanas.has('aula')) AULA.raiz = el('div', 'kpi');
    abrirVentana('aula', 'SKY Docente · Aula interactiva', AULA.raiz, { w: 1000, h: 730 });
    if (AULA.raiz.dataset.ready) return;
    AULA.raiz.dataset.ready = '1';
    const root = AULA.raiz;
    const title = seccion(root, 'Preparar clase con SKY');
    const fields = el('div', 'kpi-bar');
    const topic = el('input','hab-in'); topic.type='text'; topic.maxLength=160;
    topic.placeholder='Tema (ej.: partes de la computadora)'; topic.setAttribute('aria-label','Tema de la clase');
    const level = el('select','hab-in');
    ['inicial','primaria','secundaria','tecnico','universitario','maestria','doctorado'].forEach(v=>{
      const opt=el('option','',v);opt.value=v;level.append(opt);
    });level.value='tecnico';level.setAttribute('aria-label','Nivel educativo');
    const goal = el('input','hab-in');goal.type='text';goal.maxLength=300;
    goal.placeholder='Objetivo de aprendizaje'; goal.setAttribute('aria-label','Objetivo');
    const ref = el('textarea','hab-in');ref.maxLength=12000;ref.rows=3;
    ref.placeholder='Material del programa o texto de referencia (opcional; se señala como no verificado)';
    const start = el('button','btn primary','Iniciar clase');start.type='button';
    fields.append(topic,level,goal);title.append(fields,ref,start);
    const lessonPanel=seccion(root,'Explicación guiada y práctica');
    const status=el('div','s','Prepará una clase para comenzar.');lessonPanel.append(status);
    const speech=el('div','res','');
    speech.setAttribute('aria-live','polite');lessonPanel.append(speech);
    const actions=el('div','btns');
    const next=el('button','btn','Siguiente momento');next.type='button';next.disabled=true;
    const speakBtn=el('button','btn','SKY, explicá con voz');speakBtn.type='button';speakBtn.disabled=true;
    const answer=el('input','hab-in');answer.type='text';answer.maxLength=800;
    answer.placeholder='Respuesta o explicación del estudiante (sin datos personales)';
    const feedback=el('button','btn','Retroalimentar');feedback.type='button';feedback.disabled=true;
    actions.append(next,speakBtn,answer,feedback);lessonPanel.append(actions);
    const resources=seccion(root,'Recursos educativos · búsqueda voluntaria');
    const resourceActions=el('div','btns');
    const videos=el('button','btn','Buscar videos en YouTube');videos.type='button';
    const research=el('button','btn','Buscar bibliografía');research.type='button';
    const computer3d=el('button','btn','Explorar computadora 3D');computer3d.type='button';
    resourceActions.append(videos,research,computer3d);resources.append(resourceActions);
    const results=el('div','res','');resources.append(results);
    const guideForm=el('div','res','');
    const guideId=el('input','hab-in');guideId.type='text';guideId.maxLength=11;
    guideId.placeholder='ID del video seleccionado';guideId.setAttribute('aria-label','Identificador YouTube');
    const transcript=el('textarea','hab-in');transcript.rows=3;transcript.maxLength=15000;
    transcript.placeholder='Texto o transcripción aportado por el docente (100–15.000 caracteres)';
    transcript.setAttribute('aria-label','Transcripción para explicación del video');
    const prepareGuide=el('button','btn','Explicar video por partes');prepareGuide.type='button';
    guideForm.append(el('div','s','Para explicar el contenido del video, aportá su transcripción o notas verificadas. SKY no inventa haber visto sus escenas.'),
      guideId,transcript,prepareGuide);
    resources.append(guideForm);
    const guideResult=el('div','res','');resources.append(guideResult);
    prepareGuide.addEventListener('click',async()=>{
      prepareGuide.disabled=true;guideResult.replaceChildren();
      try{
        const data=await api('/api/sky/academy/education/resources/video-guide',{
          method:'POST',body:JSON.stringify({
            topic:settings().topic,video_id:guideId.value.trim(),transcript:transcript.value})});
        guideResult.append(el('div','s',data.warning));
        for(const part of data.parts){
          const paragraph=el('p','',part.voice_ready_text);
          guideResult.append(paragraph,el('div','s',part.question));
          const speakPart=el('button','btn','SKY explica parte '+part.number);
          speakPart.type='button';
          speakPart.addEventListener('click',()=>speak(part.voice_ready_text));
          guideResult.append(speakPart);
        }
      }catch(e){guideResult.textContent='Guía no disponible: '+e.message;}
      finally{prepareGuide.disabled=false;}
    });
    const evaluation=seccion(root,'Evaluación · conocer / hacer / ser y convivir');
    const options=el('div','btns'),kind=el('select','hab-in'),mode=el('select','hab-in');
    ['rubrica','lista_cotejo','guia_observacion','ticket_salida','estudio_caso',
     'portafolio','autoevaluacion','coevaluacion','prueba_practica','cuestionario'].forEach(v=>{
      const o=el('option','',v.replaceAll('_',' '));o.value=v;kind.append(o);
    });
    ['diagnostica','formativa','sumativa'].forEach(v=>{
      const o=el('option','',v);o.value=v;mode.append(o);
    });
    // El docente puede adecuar la ponderación a su programa formativo.
    const weightsRow=el('div','btns'),weightFields={};
    for(const [code,title,initial] of [
      ['conocer','Conocer (%)',30],['hacer','Hacer (%)',50],['ser','Ser/convivir (%)',20]]){
      const label=el('label','s',title);
      const input=el('input','hab-in');input.type='number';
      input.min='0';input.max='100';input.step='1';input.value=String(initial);
      input.setAttribute('aria-label','Peso de '+title);
      label.append(input);weightsRow.append(label);weightFields[code]=input;
    }
    function assessmentWeights(){
      const weights=Object.fromEntries(Object.entries(weightFields)
        .map(([code,input])=>[code,Number(input.value)]));
      if(Object.values(weights).some(n=>!Number.isInteger(n)||n<0||n>100) ||
          Object.values(weights).reduce((a,b)=>a+b,0)!==100)
        throw Error('Los pesos de conocer, hacer y ser deben ser enteros entre 0 y 100 y sumar 100%.');
      return weights;
    }
    const build=el('button','btn primary','Generar instrumento');build.type='button';
    const download=el('button','btn','Descargar en Word');download.type='button';
    options.append(mode,kind,build,download);evaluation.append(weightsRow,options);
    const evalResult=el('div','res','');evaluation.append(evalResult);
    function settings() {
      if (topic.value.trim().length < 3) throw Error('Indicá el tema de la clase.');
      return {topic:topic.value.trim(),level:level.value,
        goal:goal.value.trim() || 'Explicar y aplicar '+topic.value.trim()};
    }
    function showStep(data) {
      const step=data.step || {};
      status.textContent='Momento '+(step.stage_number||'?')+'/'+(step.total_stages||7)+' · '+(step.stage_name||'');
      speech.replaceChildren(document.createTextNode(step.voice_ready_text||'No hay explicación.'));
      if(step.real_life_case && step.real_life_case.available){
        const box=el('div','note','Caso para practicar: '+step.real_life_case.scenario);
        const list=el('ol','');
        (step.real_life_case.steps||[]).forEach(v=>list.append(el('li','',v)));
        box.append(list,el('div','s',step.real_life_case.reflection));
        speech.append(box);
      }
      next.disabled=false;speakBtn.disabled=false;feedback.disabled=false;
      if(step.visual_3d && step.visual_3d.available) {
        computer3d.textContent='Abrir escena 3D del tema';
      }
    }
    start.addEventListener('click',async()=>{
      start.disabled=true;
      try{
        const params=settings();
        const data=await api('/api/sky/academy/education/sessions',{
          method:'POST',body:JSON.stringify({topic:params.topic,level:params.level,
          learning_goal:params.goal,reference_text:ref.value,duration_minutes:45})});
        AULA.lesson=data.lesson_id;showStep(data);
      }catch(e){speech.textContent='No se pudo iniciar la clase: '+e.message;}
      finally{start.disabled=false;}
    });
    next.addEventListener('click',async()=>{
      if(!AULA.lesson)return;
      next.disabled=true;
      try{
        const data=await api('/api/sky/academy/education/sessions/'+
          encodeURIComponent(AULA.lesson)+'/next',{method:'POST'});
        if(data.no_more_steps){status.textContent='Clase concluida';next.disabled=true;return;}
        showStep(data);
      }catch(e){status.textContent=e.message;}
    });
    speakBtn.addEventListener('click',async()=>{if(speech.textContent)await speak(speech.textContent);});
    feedback.addEventListener('click',async()=>{
      if(!AULA.lesson||answer.value.trim().length<2)return;
      feedback.disabled=true;
      try{
        const d=await api('/api/sky/academy/education/sessions/'+encodeURIComponent(AULA.lesson)+'/respond',{
          method:'POST',body:JSON.stringify({answer:answer.value.trim()})});
        speech.textContent=d.voice_ready_text||d.message||'';
        if(S.voz)await speak(speech.textContent);
      }catch(e){speech.textContent=e.message;}finally{feedback.disabled=false;}
    });
    videos.addEventListener('click',async()=>{
      videos.disabled=true;results.replaceChildren();
      try{
        const d=await api('/api/sky/academy/education/resources/videos',{
          method:'POST',body:JSON.stringify({...settings(),limit:4})});
        results.append(el('div','s',d.message||d.status));
        if(d.searched_live && d.videos.length){
          d.videos.forEach(v=>{
            const link=el('a','',v.title+' — '+v.channel);
            link.href=v.watch_url;link.target='_blank';link.rel='noopener noreferrer';
            const row=el('p','');row.append(link);results.append(row);
            const watch=el('button','btn','Ver video autorizado');
            watch.addEventListener('click',()=>{
              guideId.value=v.id;
              const video=document.createElement('iframe');
              video.title='YouTube educativo: '+v.title;
              video.src=v.embed_url;video.loading='lazy';video.allow='encrypted-media; picture-in-picture';
              video.referrerPolicy='strict-origin-when-cross-origin';
              video.style.width='100%';video.style.aspectRatio='16/9';
              row.after(video);watch.disabled=true;
            });row.append(watch);
          });
        }else if(d.fallback_search_url){
          const link=el('a','','Abrir búsqueda de YouTube');link.href=d.fallback_search_url;
          link.target='_blank';link.rel='noopener noreferrer';results.append(link);
        }
      }catch(e){results.textContent='Búsqueda no disponible: '+e.message;}
      finally{videos.disabled=false;}
    });
    research.addEventListener('click',async()=>{
      research.disabled=true;results.replaceChildren();
      try{
        const d=await api('/api/sky/academy/education/resources/research',{
          method:'POST',body:JSON.stringify({...settings(),limit:5})});
        results.append(el('div','s','Bibliografía '+d.status+
          '. Son metadatos; SKY no ha leído artículos completos.'));
        (d.items||[]).forEach(p=>results.append(el('p','',p.title||'Referencia sin título')));
      }catch(e){results.textContent=e.message;}
      finally{research.disabled=false;}
    });
    computer3d.addEventListener('click',()=>abrirVentana('aula-3d',
      'SKY · Computadora tridimensional','/aula/3d/computadora',{w:1040,h:740}));
    async function instrumentData() {
      const v=settings();return api('/api/sky/academy/education/assessments',{
        method:'POST',body:JSON.stringify({topic:v.topic,level:v.level,goal:v.goal,
          instrument:kind.value,evaluation_type:mode.value,weights:assessmentWeights()})});
    }
    build.addEventListener('click',async()=>{
      build.disabled=true;evalResult.replaceChildren();
      try{
        const d=await instrumentData();
        evalResult.append(el('h3','',d.type+' · '+d.instrument));
        for(const dimension of d.dimensions){
          evalResult.append(el('p','',dimension.label+': '+dimension.criterion));
          for(const l of dimension.levels||[]){
            evalResult.append(el('div','s',l.value+' — '+l.label+': '+l.descriptor));
          }
        }
        evalResult.append(el('div','s','Borrador: el docente revisa criterios y evidencias.'));
      }catch(e){evalResult.textContent=e.message;}finally{build.disabled=false;}
    });
    download.addEventListener('click',async()=>{
      download.disabled=true;
      try{
        const v=settings();const response=await fetch('/api/sky/academy/education/assessments/document',{
          method:'POST',headers:headers(),body:JSON.stringify({topic:v.topic,level:v.level,
           goal:v.goal,instrument:kind.value,evaluation_type:mode.value,
           weights:assessmentWeights(),kind:'docx'})});
        if(!response.ok)throw Error('HTTP '+response.status);
        const url=URL.createObjectURL(await response.blob());
        const link=document.createElement('a');link.href=url;link.download='SKY-Aula-Evaluacion.docx';
        link.click();setTimeout(()=>URL.revokeObjectURL(url),15000);
      }catch(e){evalResult.textContent='Descarga no disponible: '+e.message;}
      finally{download.disabled=false;}
    });
  }

  /* ------------------------------------------------------------------ módulo de rendimiento (KPIs reales) */
  const KPI = { abierto: false, periodo: 'hoy', raiz: null, timer: null };
  function fmtMs(ms) { return ms == null ? '—' : (ms < 1000 ? ms + ' ms' : (ms / 1000).toFixed(1).replace('.', ',') + ' s'); }
  const ORIGEN = { reglas: 'Reglas', aprendido: 'Atajos aprendidos', cerebro: 'Cerebro local', ia: 'IA conversacional' };
  function abrirKPI(datos) {
    if (!KPI.raiz) {
      const raiz = el('div', 'kpi');
      const barra = el('div', 'kpi-bar');
      ['hoy', 'semana'].forEach(p => {
        const b = el('button', 'btn' + (p === KPI.periodo ? ' primary' : ''), p === 'hoy' ? 'Hoy' : '7 días'); b.type = 'button'; b.dataset.p = p;
        b.addEventListener('click', () => { KPI.periodo = p; barra.querySelectorAll('button[data-p]').forEach(x => x.classList.toggle('primary', x.dataset.p === p)); KPI.cargar(); });
        barra.appendChild(b);
      });
      const r = el('button', 'btn', 'Actualizar'); r.type = 'button'; r.addEventListener('click', () => KPI.cargar());
      barra.appendChild(r); barra.appendChild(el('span', 'kpi-gen', ''));
      raiz.appendChild(barra); raiz.appendChild(el('div', 'kpi-cuerpo'));
      KPI.raiz = raiz;
    }
    const w = abrirVentana('kpi', 'Rendimiento de SKY', KPI.raiz, { w: 980, h: 640 });
    KPI.abierto = true;
    const cerrar = w.el.querySelector('header button[title="Cerrar"]');
    if (cerrar && !cerrar.dataset.kpi) { cerrar.dataset.kpi = '1'; cerrar.addEventListener('click', () => { KPI.abierto = false; KPI.raiz = null; clearInterval(KPI.timer); }); }
    if (datos && datos.periodo === KPI.periodo) pintarKPI(datos); else KPI.cargar();
    clearInterval(KPI.timer);
    KPI.timer = setInterval(() => { if (ventanas.has('kpi') && document.visibilityState === 'visible') KPI.cargar(); else if (!ventanas.has('kpi')) clearInterval(KPI.timer); }, 20000);
  }
  KPI.cargar = async function () {
    if (!KPI.raiz) return;
    try {
      const [d, a] = await Promise.all([api('/api/hud/kpi?periodo=' + KPI.periodo), api('/api/hud/aprendizaje').catch(() => null)]);
      pintarKPI(d, a);
    } catch (e) { const c = KPI.raiz.querySelector('.kpi-cuerpo'); c.textContent = ''; c.appendChild(el('div', 'note', 'No pude leer los KPIs: ' + e.message)); }
  };
  function tarjeta(titulo, valor, sub, clase) {
    const t = el('div', 'kpi-tile' + (clase ? ' ' + clase : ''));
    t.appendChild(el('small', '', titulo)); t.appendChild(el('b', '', valor)); if (sub) t.appendChild(el('span', '', sub));
    return t;
  }
  function seccion(cuerpo, titulo) { const s = el('section', 'kpi-sec'); s.appendChild(el('h4', '', titulo)); cuerpo.appendChild(s); return s; }
  function tabla(cols, filas) {
    const t = el('table', 'kpi-tab'); const h = el('tr'); cols.forEach(c => h.appendChild(el('th', '', c))); t.appendChild(h);
    filas.forEach(f => { const tr = el('tr'); f.forEach(v => tr.appendChild(el('td', '', String(v)))); t.appendChild(tr); });
    return t;
  }
  function pintarKPI(d, aprend) {
    if (!KPI.raiz) return;
    KPI.raiz.querySelector('.kpi-gen').textContent = 'Medido ' + (d.generado || '').replace('T', ' ') + ' · ' + d.eventos + ' eventos';
    const c = KPI.raiz.querySelector('.kpi-cuerpo'); c.textContent = '';
    const a = d.acciones, t = d.asistente, ap = d.api, ag = d.agente;
    const tiles = el('div', 'kpi-tiles');
    tiles.appendChild(tarjeta('Tareas completadas', a.completadas + ' / ' + a.total, a.tasa_exito == null ? 'sin tareas' : a.tasa_exito + ' % de éxito', a.fallidas ? '' : 'ok'));
    tiles.appendChild(tarjeta('Tareas fallidas', String(a.fallidas), a.total ? 'de ' + a.total + ' · mediana ' + fmtMs(a.p50_ms) : '', a.fallidas ? 'bad' : 'ok'));
    tiles.appendChild(tarjeta('Mensajes atendidos', String(t.turnos), t.errores ? t.errores + ' con error' : 'sin errores', t.errores ? 'warn' : ''));
    tiles.appendChild(tarjeta('API · p95', fmtMs(ap.p95_ms), ap.peticiones + ' peticiones · ' + ap.errores_5xx + ' errores 5xx', ap.errores_5xx ? 'warn' : ''));
    tiles.appendChild(tarjeta('Agente del equipo', ag.disponibilidad == null ? '—' : ag.disponibilidad + ' %', ag.sin_respuesta ? ag.sin_respuesta + ' sin respuesta' : 'disponible', ag.sin_respuesta ? 'warn' : ''));
    if (d.sistema && d.sistema.cpu_equipo != null) tiles.appendChild(tarjeta('Equipo', 'CPU ' + Math.round(d.sistema.cpu_equipo) + ' %', 'RAM ' + Math.round(d.sistema.memoria_equipo) + ' % · SKY ' + d.sistema.memoria_sky_mb + ' MB'));
    c.appendChild(tiles);

    const sp = seccion(c, 'Problemas detectados');
    if (!d.problemas.length) sp.appendChild(el('div', 'kpi-ok', 'Sin problemas de rendimiento (comparado con los 7 días anteriores).'));
    d.problemas.forEach(p => {
      const b = el('div', 'kpi-prob ' + (p.severidad === 'alta' ? 'bad' : 'warn'));
      b.appendChild(el('b', '', p.titulo)); b.appendChild(el('div', '', p.detalle)); b.appendChild(el('small', '', '→ ' + p.sugerencia));
      sp.appendChild(b);
    });

    if (d.serie.length) {
      const ss = seccion(c, d.periodo === 'hoy' ? 'Tareas por hora' : 'Tareas por hora (7 días)');
      const max = Math.max(1, ...d.serie.map(x => x.completadas + x.fallidas));
      const g = el('div', 'kpi-serie');
      d.serie.slice(-24).forEach(x => {
        const col = el('div', 'kpi-col'); col.title = x.hora + ': ' + x.completadas + ' completadas, ' + x.fallidas + ' fallidas';
        const pila = el('div', 'kpi-pila');
        const f = el('i', 'f'); f.style.height = (x.fallidas / max * 100) + '%';
        const o = el('i', 'o'); o.style.height = (x.completadas / max * 100) + '%';
        pila.append(f, o); col.appendChild(pila); col.appendChild(el('small', '', x.hora.slice(-5, -3)));
        g.appendChild(col);
      });
      ss.appendChild(g);
    }
    if (a.ultimas_fallidas.length) seccion(c, 'Tareas que fallaron').appendChild(tabla(['Hora', 'Tarea', 'Motivo'], a.ultimas_fallidas.map(f => [f.hora, f.nombre, f.motivo || '—'])));
    if (a.por_accion.length) seccion(c, 'Por tipo de tarea').appendChild(tabla(['Tarea', 'Completadas', 'Fallidas', 'Mediana'], a.por_accion.map(x => [x.nombre, x.completadas, x.fallidas, fmtMs(x.p50_ms)])));
    const orig = Object.entries(t.por_origen || {});
    if (orig.length) seccion(c, 'Cómo resolví tus mensajes').appendChild(tabla(['Vía', 'Mensajes', 'Mediana', 'p95'], orig.sort((x, y) => y[1].n - x[1].n).map(([k, v]) => [ORIGEN[k] || k, v.n, fmtMs(v.p50_ms), fmtMs(v.p95_ms)])));
    if (ap.rutas_lentas.length) seccion(c, 'Rutas más lentas de la API').appendChild(tabla(['Ruta', 'Peticiones', 'Mediana', 'p95'], ap.rutas_lentas.map(x => [x.ruta, x.n, fmtMs(x.p50_ms), fmtMs(x.p95_ms)])));
    if (aprend) {
      const sa = seccion(c, 'Aprendizaje');
      sa.appendChild(el('div', 's', aprend.atajos + ' atajos · ' + aprend.ordenes_ensenadas + ' órdenes enseñadas · ' + aprend.temas + ' temas de internet · ' + aprend.memorias + ' datos sobre vos' + (aprend.internet ? '' : ' · internet desactivado')));
      if (aprend.intereses.length) sa.appendChild(el('div', 's', 'Sigo: ' + aprend.intereses.join(', ')));
      if (aprend.temas_recientes.length) sa.appendChild(el('div', 's', 'Aprendí sobre: ' + aprend.temas_recientes.join(', ')));
      (aprend.lista_atajos || []).concat(aprend.lista_ensenadas || []).forEach(x => {
        const fila = el('div', 'kpi-atajo');
        fila.appendChild(el('span', '', '«' + x.frase + '» → ' + x.hace + (x.veces ? ' · ' + x.veces + ' usos' : '')));
        const b = el('button', 'btn', 'Olvidar'); b.type = 'button';
        b.addEventListener('click', async () => { try { await api('/api/hud/aprendizaje/atajos/' + encodeURIComponent(x.frase), { method: 'DELETE' }); fila.remove(); } catch (e) { b.textContent = 'Error'; } });
        fila.appendChild(b); sa.appendChild(fila);
      });
    }
  }

  /* ------------------------------------------------------------------ perfil (USER.md) */
  async function abrirPerfil() {
    const raiz = el('div', 'kpi');
    raiz.appendChild(el('div', 's', 'Escribí quién sos, tus herramientas, suscripciones, horarios y objetivos. SKY lo tiene en cuenta en cada respuesta. No pongas contraseñas.'));
    const ta = el('textarea', 'perfil-txt'); ta.maxLength = 8000; ta.spellcheck = true; ta.setAttribute('aria-label', 'Tu perfil');
    raiz.appendChild(ta);
    const bar = el('div', 'kpi-bar');
    const g = el('button', 'btn primary', 'Guardar'); g.type = 'button';
    const est = el('span', 'kpi-gen', '');
    bar.append(g, est); raiz.appendChild(bar);
    abrirVentana('perfil', 'Tu perfil', raiz, { w: 760, h: 620 });
    try { const r = await api('/api/hud/perfil'); ta.value = r.texto || ''; est.textContent = r.ruta || ''; } catch (e) { est.textContent = 'No pude leerlo: ' + e.message; }
    g.addEventListener('click', async () => {
      try { const r = await api('/api/hud/perfil', { method: 'PUT', body: JSON.stringify({ texto: ta.value }) }); est.textContent = 'Guardado · ' + r.caracteres + ' caracteres'; }
      catch (e) { est.textContent = 'No se guardó: ' + e.message; }
    });
  }

  /* ------------------------------------------------------------------ automatización: tareas, skills, borradores, WhatsApp */
  const AUTO = { raiz: null };
  const DIAS_TXT = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];
  function abrirAuto() {
    if (!AUTO.raiz || !ventanas.has('auto')) { AUTO.raiz = el('div', 'kpi'); }
    abrirVentana('auto', 'Automatización', AUTO.raiz, { w: 900, h: 640 });
    AUTO.cargar();
  }
  AUTO.cargar = async function () {
    if (!AUTO.raiz) return;
    const c = AUTO.raiz; let d;
    try {
      const [t, sk, b, wa] = await Promise.all([api('/api/hud/programadas'), api('/api/hud/skills'), api('/api/hud/borradores'), api('/api/hud/whatsapp').catch(() => ({}))]);
      d = { t, sk, b, wa };
    } catch (e) { c.textContent = ''; c.appendChild(el('div', 'note', 'No pude leer la automatización: ' + e.message)); return; }
    c.textContent = '';
    const s1 = seccion(c, 'Tareas programadas');
    if (!d.t.tareas.length) s1.appendChild(el('div', 's', 'Ninguna. Decí por ejemplo: «todos los días a las 8 prepara las respuestas de los correos».'));
    d.t.tareas.forEach(r => {
      const fila = el('div', 'kpi-atajo');
      const dias = (r.dias && r.dias.length && r.dias.length < 7) ? r.dias.map(x => DIAS_TXT[x]).join(' ') : 'todos los días';
      fila.appendChild(el('span', '', r.hora + ' · ' + r.nombre + ' · ' + dias + (r.ultima ? ' · última: ' + r.ultima : '')));
      const bx = el('div', 'btns');
      const tg = el('button', 'btn' + (r.activa === false ? '' : ' primary'), r.activa === false ? 'Pausada' : 'Activa'); tg.type = 'button';
      tg.setAttribute('aria-pressed', String(r.activa !== false));
      tg.addEventListener('click', async () => { try { await api('/api/hud/programadas/' + r.id, { method: 'PATCH', body: JSON.stringify({ activa: r.activa === false }) }); AUTO.cargar(); } catch (e) { tg.textContent = 'Error'; } });
      const del = el('button', 'btn', 'Borrar'); del.type = 'button';
      del.addEventListener('click', async () => { try { await api('/api/hud/programadas/' + r.id, { method: 'DELETE' }); AUTO.cargar(); } catch (e) { del.textContent = 'Error'; } });
      bx.append(tg, del); fila.appendChild(bx); s1.appendChild(fila);
    });
    const s2 = seccion(c, 'Skills');
    s2.appendChild(el('div', 's', 'Carpeta: ' + d.sk.carpeta + ' · Creá una diciendo «crea una skill modo trabajo que abra Word y ponga lofi para estudiar».'));
    d.sk.skills.forEach(k => {
      const fila = el('div', 'kpi-atajo');
      fila.appendChild(el('span', '', k.nombre + (k.integrada ? ' (integrada)' : '') + ' — ' + (k.descripcion || k.pasos.length + ' pasos')));
      const bx = el('div', 'btns');
      const run = el('button', 'btn primary', 'Ejecutar'); run.type = 'button';
      run.addEventListener('click', async () => {
        run.disabled = true;
        try { const r = await api('/api/hud/skills/' + k.id + '/ejecutar', { method: 'POST' }); const card = addCard('▸ ' + k.nombre, 'skill'); card.appendChild(el('div', '', r.mensaje || 'Listo.')); await decir(r.mensaje || 'Listo.'); }
        catch (e) { run.textContent = 'Error'; }
        run.disabled = false; AUTO.cargar();
      });
      bx.appendChild(run);
      if (!k.integrada) { const del = el('button', 'btn', 'Borrar'); del.type = 'button'; del.addEventListener('click', async () => { await api('/api/hud/skills/' + k.id, { method: 'DELETE' }).catch(() => {}); AUTO.cargar(); }); bx.appendChild(del); }
      fila.appendChild(bx); s2.appendChild(fila);
    });
    const s3 = seccion(c, 'Borradores de correo (esperan tu aprobación)');
    const prep = el('button', 'btn', 'Preparar ahora'); prep.type = 'button';
    prep.addEventListener('click', async () => { prep.disabled = true; prep.textContent = 'Redactando…'; try { const r = await api('/api/hud/borradores/preparar', { method: 'POST' }); prep.textContent = r.nuevos.length + ' nuevos' + (r.error ? ' · ' + r.error : ''); } catch (e) { prep.textContent = e.message; } AUTO.cargar(); });
    s3.appendChild(prep);
    if (!d.b.borradores.length) s3.appendChild(el('div', 's', 'No hay borradores.'));
    d.b.borradores.forEach(b => {
      const box = el('div', 'kpi-prob');
      box.appendChild(el('b', '', 'Para ' + (b.de || b.para) + ' · ' + b.asunto));
      const ta = el('textarea', 'perfil-txt corto'); ta.value = b.cuerpo; ta.maxLength = 20000; box.appendChild(ta);
      const bx = el('div', 'btns');
      const env = el('button', 'btn primary', 'Enviar'); env.type = 'button';
      env.addEventListener('click', async () => {
        env.disabled = true;
        try {
          if (ta.value !== b.cuerpo) await api('/api/hud/borradores/' + b.id, { method: 'PATCH', body: JSON.stringify({ cuerpo: ta.value }) });
          await api('/api/hud/borradores/' + b.id + '/enviar', { method: 'POST' }); AUTO.cargar();
        } catch (e) { env.disabled = false; box.appendChild(el('div', 'res bad', 'No se envió: ' + e.message)); }
      });
      const des = el('button', 'btn', 'Descartar'); des.type = 'button';
      des.addEventListener('click', async () => { await api('/api/hud/borradores/' + b.id, { method: 'DELETE' }).catch(() => {}); AUTO.cargar(); });
      bx.append(env, des); box.appendChild(bx); s3.appendChild(box);
    });
    const s4 = seccion(c, 'WhatsApp');
    const wa = d.wa || {};
    if (!wa.configurado) s4.appendChild(el('div', 's', 'Sin configurar. Guía paso a paso: docs/guias/SKY_WHATSAPP.md' + (wa.faltan && wa.faltan.length ? ' · Falta: ' + wa.faltan.join(', ') : '')));
    else {
      s4.appendChild(el('div', 's', 'Conectado al número ' + wa.dueno + ' · último mensaje: ' + (wa.ultimo_mensaje || 'nunca') + ' · ' + (wa.ventana_abierta ? 'puedo escribirte ahora' : 'escribime primero para abrir la ventana de 24 h') + (wa.plantilla_avisos ? ' · avisos con plantilla' : '')));
      const pr = el('button', 'btn', 'Enviar mensaje de prueba'); pr.type = 'button';
      pr.addEventListener('click', async () => { try { await api('/api/hud/whatsapp/prueba', { method: 'POST' }); pr.textContent = 'Enviado'; } catch (e) { pr.textContent = e.message; } });
      s4.appendChild(pr);
    }
  };

  /* ------------------------------------------------------------------ imágenes creadas por SKY */
  async function mostrarImagen(nombre) {
    try {
      const r = await fetch('/api/hud/creaciones/imagenes/' + encodeURIComponent(nombre), { headers: headers({}, false) });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const url = URL.createObjectURL(await r.blob());
      const card = addCard('▸ Imagen creada por SKY', nombre);
      const img = el('img', 'sky-img'); img.src = url; img.alt = 'Imagen generada: ' + nombre;
      card.appendChild(img); scroll();
    } catch (e) { addMsg('sky', 'No pude mostrar la imagen: ' + e.message, 'err'); }
  }

  /* ------------------------------------------------------------------ habilidades y SKY Skill Builder */
  const HAB = { raiz: null };
  function abrirHabilidades() {
    if (!HAB.raiz || !ventanas.has('habilidades')) HAB.raiz = el('div', 'kpi');
    abrirVentana('habilidades', 'Habilidades de SKY', HAB.raiz, { w: 980, h: 680 });
    HAB.cargar();
  }
  HAB.cargar = async function () {
    if (!HAB.raiz) return;
    const c = HAB.raiz; let d;
    try { d = await api('/api/hud/habilidades'); } catch (e) { c.textContent = ''; c.appendChild(el('div', 'note', 'No pude leer las habilidades: ' + e.message)); return; }
    c.textContent = '';
    // Skill Builder
    const sb = seccion(c, 'SKY Skill Builder');
    sb.appendChild(el('div', 's', 'SKY diseña la habilidad, la revisa y la prueba aislada (sin red, sin archivos, sin instalar nada externo). Sólo se instala cuando vos la aprobás aquí.'));
    const fila = el('div', 'kpi-bar');
    const inp = el('input', 'hab-in'); inp.type = 'text'; inp.maxLength = 500; inp.placeholder = '¿Qué habilidad necesitás? Ej.: convertir monedas con el tipo de cambio del día';
    const go = el('button', 'btn primary', 'Proponer'); go.type = 'button';
    const est = el('span', 'kpi-gen', '');
    go.addEventListener('click', async () => {
      if (inp.value.trim().length < 6) { est.textContent = 'Contame un poco más.'; return; }
      go.disabled = true; est.textContent = 'Diseñando y probando…';
      try { const r = await api('/api/hud/builder/proponer', { method: 'POST', body: JSON.stringify({ pedido: inp.value.trim() }) }); est.textContent = r.reporte.aprobada ? 'Lista para revisar' : 'No pasó las pruebas'; inp.value = ''; }
      catch (e) { est.textContent = e.message; }
      go.disabled = false; HAB.cargar();
    });
    fila.append(inp, go, est); sb.appendChild(fila);
    if (d.necesidades.length) {
      sb.appendChild(el('div', 's', 'Pedidos que todavía no sé resolver:'));
      d.necesidades.forEach(n => {
        const f = el('div', 'kpi-atajo'); f.appendChild(el('span', '', '«' + n.frase + '» · ' + n.veces + ' veces'));
        const b = el('button', 'btn', 'Proponer habilidad'); b.type = 'button';
        b.addEventListener('click', () => { inp.value = n.frase; go.click(); });
        f.appendChild(b); sb.appendChild(f);
      });
    }
    d.builder.forEach(b => {
      const box = el('div', 'kpi-prob ' + (b.estado === 'instalada' ? '' : b.estado_ultima === 'probada' ? 'warn' : 'bad'));
      const m = b.manifiesto, rep = b.reporte;
      box.appendChild(el('b', '', m.nombre + ' · ' + (b.estado === 'instalada' ? 'instalada v' + b.version_instalada : b.estado) + ' · última v' + b.ultima + ' (' + b.estado_ultima + ')'));
      box.appendChild(el('div', '', (m.descripcion || '') + ' · Se usa diciendo: ' + m.disparadores.map(x => '«' + x + ' …»').join(', ')));
      if (rep.estatica && rep.estatica.length) box.appendChild(el('div', 'res bad', 'Revisión: ' + rep.estatica.join(' · ')));
      if (rep.error) box.appendChild(el('div', 'res bad', rep.error));
      (rep.pruebas || []).forEach(p => box.appendChild(el('div', p.ok ? 'res' : 'res bad', (p.ok ? '✓ ' : '✗ ') + p.entrada + ' → ' + (p.decir || p.error || '').slice(0, 160))));
      const det = el('details'); det.appendChild(el('summary', '', 'Ver código (v' + b.ultima + ')'));
      det.appendChild(el('pre', '', 'skill.json\n' + JSON.stringify(m, null, 2) + '\n\nskill.py\n' + (b.codigo_resumen || '')));
      box.appendChild(det);
      det.addEventListener('toggle', async () => {
        if (!det.open || det.dataset.cargado) return;
        try { const v = await api('/api/hud/builder/' + b.id); det.querySelector('pre').textContent = 'skill.json\n' + JSON.stringify(v.manifiesto, null, 2) + '\n\nskill.py\n' + v.codigo; det.dataset.cargado = '1'; } catch (e) { /* queda el resumen */ }
      });
      const perms = el('div', 'hab-perm');
      (m.permisos || []).forEach(pm => {
        const l = el('label', ''); const ck = el('input'); ck.type = 'checkbox'; ck.value = pm; ck.checked = (b.permisos_aprobados || []).includes(pm);
        l.append(ck, document.createTextNode(' ' + pm)); perms.appendChild(l);
      });
      if ((m.permisos || []).length) { box.appendChild(el('div', 's', 'Permisos que pide (marcá los que concedés):')); box.appendChild(perms); }
      const bx = el('div', 'btns');
      if (b.estado_ultima === 'probada' && !(b.estado === 'instalada' && b.version_instalada === b.ultima)) {
        const ap = el('button', 'btn primary', 'Aprobar e instalar v' + b.ultima); ap.type = 'button';
        ap.addEventListener('click', async () => {
          const permisos = [...perms.querySelectorAll('input:checked')].map(x => x.value);
          ap.disabled = true;
          try { await api('/api/hud/builder/' + b.id + '/aprobar', { method: 'POST', body: JSON.stringify({ version: b.ultima, permisos }) }); HAB.cargar(); }
          catch (e) { ap.disabled = false; box.appendChild(el('div', 'res bad', e.message)); }
        });
        bx.appendChild(ap);
      }
      if (b.estado === 'instalada') {
        const de = el('button', 'btn', 'Desactivar'); de.type = 'button';
        de.addEventListener('click', async () => { await api('/api/hud/builder/' + b.id + '/desactivar', { method: 'POST' }).catch(() => {}); HAB.cargar(); });
        bx.appendChild(de);
      }
      const el2 = el('button', 'btn', 'Eliminar'); el2.type = 'button';
      el2.addEventListener('click', async () => { await api('/api/hud/builder/' + b.id, { method: 'DELETE' }).catch(() => {}); HAB.cargar(); });
      bx.appendChild(el2); box.appendChild(bx); sb.appendChild(box);
    });
    // Nativas
    const sn = seccion(c, 'Habilidades de SKY');
    d.nativas.forEach(h => {
      const f = el('div', 'kpi-atajo');
      f.appendChild(el('span', '', h.nombre + ' — ' + h.descripcion + (h.integraciones_listas ? '' : ' (falta configurar su integración)') + ' · Ej.: «' + h.ejemplos[0] + '»'));
      if (h.protegida) f.appendChild(el('span', 's', 'siempre activa'));
      else {
        const tg = el('button', 'btn' + (h.activa ? ' primary' : ''), h.activa ? 'Activa' : 'Inactiva'); tg.type = 'button'; tg.setAttribute('aria-pressed', String(h.activa));
        tg.addEventListener('click', async () => { await api('/api/hud/habilidades/' + h.id, { method: 'PATCH', body: JSON.stringify({ activa: !h.activa }) }).catch(() => {}); HAB.cargar(); });
        f.appendChild(tg);
      }
      sn.appendChild(f);
    });
    // Integraciones
    const si = seccion(c, 'Integraciones (tener una cuenta no es tener su API)');
    si.appendChild(tabla(['Plataforma', 'Vía', 'Estado', 'Para qué', 'Nota'], d.integraciones.map(i => [i.nombre, i.via, i.estado, i.uso, i.nota])));
    // Extension Hub: catálogo informativo, jamás instala o ejecuta software externo.
    const extSection = seccion(c, 'SKY Extension Hub');
    extSection.appendChild(el('div', 's', 'Herramientas externas opcionales. SKY CORE conserva su identidad y permisos.'));
    try {
      const ext = await api('/api/sky/extensions');
      extSection.appendChild(tabla(['Herramienta', 'Área', 'Tipo', 'Estado'],
        ext.extensions.map(x => [x.name, x.domain, x.mode, x.state])));
    } catch (e) {
      extSection.appendChild(el('div', 's', 'Catálogo no disponible: ' + e.message));
    }
    // Verified Experience: only named, confirmed replay plans; no automatic tasks.
    const learnedSection = seccion(c, 'Procedimientos comprobados');
    learnedSection.appendChild(el('div', 's', 'Solo se guardan acciones confirmadas; al repetirlas SKY solicitará cada autorización.'));
    try {
      const memo = await api('/api/sky/learning/procedures');
      if (!memo.procedures.length) learnedSection.appendChild(el('div', 's', 'Todavía no hay procedimientos aprendidos.'));
      memo.procedures.forEach(p => {
        const row = el('div', 'kpi-atajo');
        row.appendChild(el('span', '', p.name + ' · ' + p.steps + ' pasos · ' +
          p.evidence_count + ' comprobación(es)'));
        const run = el('button', 'btn', 'Preparar');
        run.type = 'button';
        run.addEventListener('click', async () => {
          run.disabled = true;
          try {
            const answer = await api('/api/sky/learning/procedures/' +
              encodeURIComponent(p.id) + '/plan', {
              method: 'POST', body: JSON.stringify({ device: 'local', origin: 'chat' })
            });
            await cicloUI({ciclo: answer.ciclo}, 'chat');
          } catch (err) {
            row.appendChild(el('div', 'res bad', err.message));
          }
          run.disabled = false;
        });
        const forget = el('button', 'btn', 'Olvidar');
        forget.type = 'button';
        forget.addEventListener('click', async () => {
          forget.disabled = true;
          try {
            await api('/api/sky/learning/procedures/' + encodeURIComponent(p.id), {
              method: 'DELETE', body: JSON.stringify({ approved: true })
            });
            HAB.cargar();
          } catch (err) {
            row.appendChild(el('div', 'res bad', err.message)); forget.disabled = false;
          }
        });
        row.append(run, forget); learnedSection.appendChild(row);
      });
    } catch (e) {
      learnedSection.appendChild(el('div', 's', 'Memoria comprobada no disponible: ' + e.message));
    }
  };

  /* ------------------------------------------------------------------ SKY SENTINEL — Security Center */
  const SEN = { raiz: null };
  function abrirSentinel() {
    if (!SEN.raiz || !ventanas.has('sentinel')) SEN.raiz = el('div', 'kpi');
    abrirVentana('sentinel', 'SKY SENTINEL — Security Center', SEN.raiz, { w: 900, h: 640 });
    SEN.cargar();
  }
  SEN.cargar = async function () {
    if (!SEN.raiz) return;
    const c = SEN.raiz; let d;
    try { d = await api('/api/sentinel/estado'); } catch (e) { c.textContent = ''; c.appendChild(el('div', 'note', 'No pude leer la seguridad: ' + e.message)); return; }
    c.textContent = '';
    const tiles = el('div', 'kpi-tiles');
    tiles.appendChild(tarjeta('PIN', d.pin ? 'Activo' : 'Sin PIN', d.pin ? 'lo crítico lo pide' : 'configuralo abajo', d.pin ? 'ok' : 'bad'));
    tiles.appendChild(tarjeta('Acceso', d.solo_local ? 'Sólo este equipo' : 'Con llave', d.solo_local ? 'otros equipos rechazados' : 'celular/Tailscale con llave', d.solo_local ? 'ok' : ''));
    tiles.appendChild(tarjeta('2FA', d.mfa ? 'Activo' : 'Inactivo', 'segundo factor del creador', d.mfa ? 'ok' : ''));
    tiles.appendChild(tarjeta('Emergencia', d.parada ? 'PARADA' : 'Normal', d.parada ? 'nada se ejecuta' : 'acciones según permisos', d.parada ? 'bad' : 'ok'));
    tiles.appendChild(tarjeta('Accesos sin llave', String(d.kpis.accesos_fallidos_7d), 'últimos 7 días', d.kpis.accesos_fallidos_7d ? 'warn' : 'ok'));
    tiles.appendChild(tarjeta('PIN incorrectos', String(d.kpis.pin_fallidos_7d), 'últimos 7 días', d.kpis.pin_fallidos_7d ? 'warn' : 'ok'));
    c.appendChild(tiles);
    if (d.recomendaciones.length) { const s = seccion(c, 'Recomendaciones'); d.recomendaciones.forEach(x => s.appendChild(el('div', 'kpi-prob warn', x))); }
    const sc = seccion(c, 'Controles');
    const bx = el('div', 'btns');
    const bPin = el('button', 'btn primary', d.pin ? 'Cambiar PIN' : 'Configurar PIN'); bPin.type = 'button';
    bPin.addEventListener('click', async () => {
      const actual = d.pin ? await pedirPin('Tu PIN actual') : '';
      if (d.pin && !actual) return;
      const nuevo = await pedirPin('Nuevo PIN (6 a 12 dígitos, ni repetido ni consecutivo)');
      if (!nuevo) return;
      const otra = await pedirPin('Repetí el nuevo PIN');
      if (otra !== nuevo) { addMsg('sky', 'Los PIN no coinciden.', 'err'); return; }
      try { await api('/api/sentinel/pin', { method: 'POST', body: JSON.stringify({ nuevo, actual: actual || '' }) }); addMsg('sky', 'PIN guardado. Desde ahora SKY lo pide al abrirse y para lo crítico.'); }
      catch (e) { addMsg('sky', 'No se guardó el PIN: ' + e.message, 'err'); }
      SEN.cargar();
    });
    const bLoc = el('button', 'btn', d.solo_local ? 'Permitir otros equipos' : 'Sólo este equipo'); bLoc.type = 'button';
    bLoc.addEventListener('click', async () => { try { await api('/api/sentinel/solo-local', { method: 'POST', body: JSON.stringify({ activo: !d.solo_local }) }); } catch (e) { addMsg('sky', e.message, 'err'); } SEN.cargar(); });
    const bAut = el('button', 'btn', 'Pausar automatizaciones'); bAut.type = 'button';
    bAut.addEventListener('click', async () => { const r = await api('/api/sentinel/automatizaciones/pausar', { method: 'POST' }).catch(() => ({ pausadas: 0 })); bAut.textContent = r.pausadas + ' pausadas'; });
    const bEm = el('button', 'btn', d.parada ? 'Reanudar (PIN)' : 'PARADA DE EMERGENCIA'); bEm.type = 'button'; bEm.classList.add('peligro');
    bEm.addEventListener('click', async () => {
      try { if (d.parada) await api('/api/asistente/emergencia', { method: 'DELETE' }); else { await api('/api/asistente/emergencia', { method: 'POST' }); callar(); } }
      catch (e) { addMsg('sky', e.message, 'err'); }
      SEN.cargar(); refrescarEstado();
    });
    const bLock = el('button', 'btn', 'Bloquear SKY'); bLock.type = 'button'; bLock.disabled = !d.pin;
    bLock.addEventListener('click', () => desbloquear());
    bx.append(bPin, bLoc, bAut, bEm, bLock); sc.appendChild(bx);
    seccion(c, 'Dispositivos').appendChild(tabla(['Nombre', 'Tipo', 'Dirección'], d.dispositivos.map(x => [x.nombre, x.tipo, x.url])));
    if (d.habilidades_instaladas.length) seccion(c, 'Habilidades instaladas y sus permisos').appendChild(tabla(['Habilidad', 'Permisos'], d.habilidades_instaladas.map(x => [x.nombre, x.permisos.join(', ') || 'ninguno'])));
    seccion(c, 'Eventos de seguridad (7 días)').appendChild(d.accesos_recientes.length ? tabla(['Hora', 'Evento', 'Código', 'Detalle'], d.accesos_recientes.map(a => [a.hora, a.que, a.codigo || '', a.detalle])) : el('div', 'kpi-ok', 'Sin eventos.'));
    const sh = seccion(c, 'Auditoría');
    d.hallazgos.forEach(h => { const b = el('div', 'kpi-prob ' + (h.nivel === 'alta' ? 'bad' : h.nivel === 'media' ? 'warn' : '')); b.appendChild(el('b', '', '[' + h.nivel + '] ' + h.texto)); if (h.accion) b.appendChild(el('small', '', '→ ' + h.accion)); sh.appendChild(b); });
  };

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
    if (a.parada_emergencia) {
      pill('pill-agent', 'AGENTE · PARADA', 'bad');
      if (!S.paradaVista) { S.paradaVista = true; tarjetaParada(); }
    } else { S.paradaVista = false; pill('pill-agent', 'AGENTE · ' + String(a.profile || '').toUpperCase(), 'ok'); }
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
          await ejecutar({ action: item.action, params: item.params || {}, description: item.description || item.action }, card);
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
        try { await api('/api/asistente/casa', { method: 'POST', body: JSON.stringify({ service, entity_ids: [e.entity_id] }) }); }
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
    if (!enCampo && e.key === 'F4') { e.preventDefault(); abrirCuadroTexto(); }
    if (!enCampo && e.key === 'F6') { e.preventDefault(); abrirHistorial(); }
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
      if (b.requiere_pin) { await desbloquear(); } else S.key = b.key || store.get('sky-owner-key');
    } catch { S.key = store.get('sky-owner-key'); }
    if (!S.key) {
      S.key = (prompt('Llave del dueño de SKY (X-SKY-KEY):') || '').trim();
      if (S.key) store.set('sky-owner-key', S.key);
    }
    await cargarModulosTecnicos();
    await refrescarEstado();
    // Recupera el contexto reciente tras reiniciar el navegador; no borra
    // consultas anteriores ni muestra paneles por su cuenta.
    try {
      const h = await api('/api/hud/historial?limit=12');
      S.historial = (h.entries || []).slice().reverse().map(e => ({
        role:e.role, content:e.text}));
    } catch { S.historyPending = true; }
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
