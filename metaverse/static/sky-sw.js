/* SKY IA offline policy: only immutable public shell assets; never cache /api,
   /hud, responses, tokens, audio, or user content. */
'use strict';
const CACHE_NAME = 'sky-public-assets-v1';
const STATIC_ASSETS = [
  '/static/hud.css?v=12.1',
  '/static/hud.js?v=12.1',
  '/static/sky-security-ui.js',
  '/static/sky-icon-192.png',
  '/static/sky-icon-512.png'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith('sky-public-assets-') && key !== CACHE_NAME)
      .map(key => caches.delete(key))
  )));
  self.clients.claim();
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/') || url.pathname === '/hud' ||
      url.pathname === '/manifest.webmanifest' || url.pathname === '/sky-sw.js') return;
  const isPublicShell = STATIC_ASSETS.some(path => path === url.pathname + url.search ||
    (path.indexOf('?') === -1 && path === url.pathname));
  if (!isPublicShell) return;
  event.respondWith(caches.match(event.request).then(hit => hit || fetch(event.request)));
});
