'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const physics = require('../metaverse/static/sky-world-physics.js');

const building = {kind:'house', position:[3,0,0],rotation:[0,0,0],scale:[2,4,2]};
const ground = {kind:'platform', position:[0,-.3,0],rotation:[0,0,0],scale:[38,.35,38]};

test('real collision rejects walking into a wall but permits sliding alongside', () => {
  const blocked = physics.resolveMovement({x:1.2,z:0},{x:.85,z:0},[ground,building]);
  assert.equal(blocked.x,1.2);
  assert.equal(blocked.collided,true);
  const slide=physics.resolveMovement({x:1.2,z:0},{x:.85,z:.85},[building]);
  assert.equal(slide.x,1.2);
  assert.equal(slide.z,.85);
  assert.equal(slide.moved,true);
});

test('ground/platform and objects in the air never block walking', () => {
  const floating={kind:'box',position:[0,3,0],rotation:[0,0,0],scale:[2,1,2]};
  assert.equal(physics.isBlocked(0,0,[ground,floating]),false);
  assert.equal(physics.isBlocked(0,0,[{...floating,position:[0,0,0]}]),true);
});

test('bounds, rotated walls and malformed input fail predictably', () => {
  assert.equal(physics.isBlocked(18,0,[]),true);
  assert.equal(physics.isBlocked(Number.NaN,0,[]),true);
  const rotated={kind:'box',position:[0,0,0],rotation:[0,Math.PI/4,0],scale:[5,2,.4]};
  assert.equal(physics.isBlocked(1,1,[rotated]),true);
  assert.throws(()=>physics.resolveMovement({x:0,z:0},{x:NaN,z:0},[]),TypeError);
});

test('legacy decorative and distant objects keep roads passable', () => {
  const decoration={kind:'torus',position:[0,0,0],rotation:[0,0,0],scale:[6,5,.5]};
  assert.equal(physics.isBlocked(0,0,[decoration]),false);
  const s=physics.resolveMovement({x:0,z:0},{x:0,z:-.85},[ground,decoration]);
  assert.equal(s.z,-.85);
});
