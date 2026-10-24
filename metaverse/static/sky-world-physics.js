/* SKY World Physics: deterministic 2D obstacle resolution over saved 3D scene geometry.
   This is walk collision, not gravity, rigid-body dynamics or a security boundary. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.SKYWorldPhysics = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const PLAYER_RADIUS = 0.34;
  const WORLD_BOUND = 17.4; // Ground in the SKY procedural world spans +/-19 units.

  function finite(value) { return typeof value === 'number' && Number.isFinite(value); }
  function solid(object) {
    if (object?.interaction?.type === 'door' && object.interaction.active) return false;
    if (!object || !['box', 'house', 'tower', 'cylinder', 'cone',
      'tree', 'palm', 'rock'].includes(object.kind)) return false;
    const p = object.position, s = object.scale;
    if (!Array.isArray(p) || !Array.isArray(s) || p.length !== 3 || s.length !== 3 ||
        !p.every(finite) || !s.every(finite) || s.some(v => v <= 0)) return false;
    // Floating structures do not block a grounded player.
    return p[1] < 1.35 && p[1] + s[1] > 0;
  }

  function touches(x, z, object, radius) {
    const [ox, , oz] = object.position;
    const [sx, , sz] = object.scale;
    const yaw = Array.isArray(object.rotation) && finite(object.rotation[1])
      ? object.rotation[1] : 0;
    const c = Math.cos(yaw), s = Math.sin(yaw);
    const dx = x - ox, dz = z - oz;
    const localX = dx * c - dz * s;
    const localZ = dx * s + dz * c;
    const hx = sx / 2, hz = sz / 2;
    const cx = Math.max(-hx, Math.min(hx, localX));
    const cz = Math.max(-hz, Math.min(hz, localZ));
    return (localX - cx) ** 2 + (localZ - cz) ** 2 < radius ** 2;
  }

  function isBlocked(x, z, objects, radius = PLAYER_RADIUS) {
    if (!finite(x) || !finite(z) || !finite(radius) || radius <= 0) return true;
    if (Math.abs(x) > WORLD_BOUND - radius || Math.abs(z) > WORLD_BOUND - radius) return true;
    return (Array.isArray(objects) ? objects : []).some(o => solid(o) && touches(x, z, o, radius));
  }

  function resolveMovement(from, delta, objects, radius = PLAYER_RADIUS) {
    if (!from || !delta || ![from.x, from.z, delta.x, delta.z].every(finite))
      throw new TypeError('Avatar movement requires finite x/z coordinates');
    // Independent axes give basic wall sliding, not teleportation through obstacles.
    const dx = Math.max(-1, Math.min(1, delta.x));
    const dz = Math.max(-1, Math.min(1, delta.z));
    let x = from.x, z = from.z, collided = false;
    if (!isBlocked(x + dx, z, objects, radius)) x += dx;
    else if (dx !== 0) collided = true;
    if (!isBlocked(x, z + dz, objects, radius)) z += dz;
    else if (dz !== 0) collided = true;
    return {x, z, collided, moved: x !== from.x || z !== from.z};
  }

  return Object.freeze({isBlocked, resolveMovement, PLAYER_RADIUS, WORLD_BOUND});
});
