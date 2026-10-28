'use strict';
// Pure text controls + integration contract; no mic, network, local files or LLM.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const guards = require('../metaverse/static/sky-hud-voice-guards.js');

test('SKY CALLATE y variantes son silencio local, nunca prompts para IA', () => {
  for (const text of ['SKY CALLATE', 'SKY, cállate', 'oye sky silencio',
                      'SKY para', 'detente', 'SKY, deja de hablar']) {
    assert.equal(guards.isStopSpeaking(text), true, text);
  }
});

test('no interceptar parada de emergencia ni conversaciones normales', () => {
  for (const text of ['SKY para todo', 'SKY abre Word',
                      'Explica qué es el silencio', 'Para qué sirve el sol']) {
    assert.equal(guards.isStopSpeaking(text), false, text);
  }
});

test('no interpretar subtítulos o audio incidental como una orden continua', () => {
  assert.equal(guards.shouldAcceptContinuous('Subtítulos por la comunidad de Amara.org', true), false);
  assert.equal(guards.shouldAcceptContinuous('La fotosíntesis es el proceso por el cual las plantas', true), false);
  assert.equal(guards.shouldAcceptContinuous('Subtitles provided by Amara.org', true), false);
  assert.equal(guards.shouldAcceptContinuous('¿Qué es la fotosíntesis?', true), true);
  assert.equal(guards.shouldAcceptContinuous('explicame el tema', true), true);
  assert.equal(guards.shouldAcceptContinuous('Sí', true), true);
});

test('con CONV apagado, la palabra SKY es obligatoria', () => {
  assert.equal(guards.shouldAcceptContinuous('¿Qué es la fotosíntesis?', false), false);
  assert.equal(guards.shouldAcceptContinuous('SKY, explicame la fotosíntesis', false), true);
});

test('la conversación activa se puede cancelar sin una solicitud al modelo', () => {
  const source = fs.readFileSync(path.join(__dirname, '../metaverse/static/hud.js'), 'utf8');
  assert.match(source, /if \(window\.SKYHUDVoiceGuards\?\.isStopSpeaking\(texto\)\)/);
  assert.match(source, /if \(abortarRespuestaActual\) abortarRespuestaActual\(\)/);
  assert.match(source, /canceladaPorUsuario = true/);
  assert.match(source, /if \(canceladaPorUsuario\) return/);
});

test('el guard del navegador carga antes del HUD y con version nueva', () => {
  const html = fs.readFileSync(path.join(__dirname, '../metaverse/static/hud.html'), 'utf8');
  const guard = html.indexOf('sky-hud-voice-guards.js?v=1.0');
  const hud = html.search(/\/static\/hud\.js\?v=[0-9.]+/);
  assert.ok(guard >= 0 && hud > guard);
});
