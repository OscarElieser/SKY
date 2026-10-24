/* SKY PWA: install on desktop and Android over HTTPS or localhost.
   No device-control privileges come from PWA installation. */
(() => {
  'use strict';
  if (!('serviceWorker' in navigator)) return;
  // Keep the PWA opt-in: mobile may be opened from a secure private SKY host.
  if (location.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(location.hostname)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sky-sw.js', {scope: '/'}).catch(() => {
      // Unsupported browser, HTTP or disabled Service Workers: SKY stays usable as web.
    });
  });
})();
