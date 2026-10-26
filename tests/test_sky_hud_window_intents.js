const assert = require('node:assert/strict');
const {test} = require('node:test');
const {parse} = require('../metaverse/static/sky-window-intents.js');

test('YouTube command stays inside HUD as a small visible window', () => {
  assert.deepEqual(parse('SKY, abre YouTube y pon la música de Joseph en una ventana mini'),
    {kind:'youtube',query:'joseph',mode:'mini'});
});
test('User explicitly requests minimized (hidden until dock restore)', () => {
  assert.deepEqual(parse('ABRE YOUTUBE Y PON LA MUSICA DE JOSEPH EN UNA VENTANA MINIMIZADA'),
    {kind:'youtube',query:'joseph',mode:'minimized'});
});
test('Search module activation is local', () => {
  assert.deepEqual(parse('ACTIVA EL MODULO DE BUSCAR'),
    {kind:'search',provider:'web',mode:'normal'});
});
test('YouTube opening alone prepares internal search', () => {
  assert.deepEqual(parse('SKY, abrí Youtube'),
    {kind:'search',provider:'youtube',mode:'normal'});
});

test('YouTube opening with punctuation stays inside SKY', () => {
  assert.deepEqual(parse('¡Abre YouTube!'),
    {kind:'search',provider:'youtube',mode:'normal'});
});
test('Maximize, restore and close local windows', () => {
  assert.deepEqual(parse('maximiza youtube'), {kind:'window_control',target:'player',mode:'max'});
  assert.deepEqual(parse('restaurá el buscador'), {kind:'window_control',target:'search',mode:'normal'});
  assert.deepEqual(parse('cierra el reproductor'), {kind:'window_control',target:'player',mode:'close'});
});
test('Do not reinterpret unrelated Windows or filesystem commands', () => {
  assert.equal(parse('abre Microsoft Word'), null);
  assert.equal(parse('busca mis documentos en el disco'), null);
  assert.equal(parse('SKY, cómo funciona la memoria'), null);
});
