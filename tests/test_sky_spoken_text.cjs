'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const spoken = require('../metaverse/static/sky-spoken-text.js');

test('natural reading does not read markdown syntax', () => {
  const raw = '# Resumen\n- **Primero:** agua.\n- Segundo: oxígeno.';
  const value = spoken.prepare(raw);
  assert.ok(value.includes('Primero: agua.'));
  assert.ok(value.includes('Segundo: oxígeno.'));
  assert.ok(!value.includes('*') && !value.includes('#'));
  assert.ok(raw.startsWith('# Resumen'));
});
test('decimal separators and familiar punctuation remain as pauses', () => {
  const value = spoken.prepare('¿Cuánto cuesta? ¡Vale 3,14 y 1.500 córdobas! 😊');
  assert.ok(value.includes('3,14'));
  assert.ok(value.includes('1.500'));
  assert.ok(!value.includes('¿') && !value.includes('¡') && !value.includes('😊'));
});
test('urls and code do not become spelled out', () => {
  const value = spoken.prepare('Mira [la guía](https://example.org) y\n```js\nsecret();\n```');
  assert.ok(value.includes('la guía'));
  assert.ok(value.includes('Código disponible en pantalla.'));
  assert.ok(!value.includes('https') && !value.includes('secret()'));
});
test('HUD calls spoken cleaner without mutating visible messages', () => {
  const hud = fs.readFileSync(path.join(__dirname, '../metaverse/static/hud.js'), 'utf8');
  assert.match(hud, /window\.SKYSpokenText\?\.prepare\(t\)/);
  assert.match(hud, /addMsg\('sky', texto, extra\)/);
  const html = fs.readFileSync(path.join(__dirname, '../metaverse/static/hud.html'), 'utf8');
  assert.ok(html.indexOf('sky-spoken-text.js?v=1.0') <
            html.indexOf('hud.js?v=14.6'));
});
