// Prueba real y CONTROLADA contra un ambiente staging aislado, nunca producción.
// Ejemplo: SKY_STAGING_URL=https://staging.ejemplo.org SKY_TEST_DEVICE_ID=... 
// SKY_TEST_DEVICE_TOKEN=... k6 run staging-load.k6.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const origin = (__ENV.SKY_STAGING_URL || '').replace(/\/$/, '');
const device = __ENV.SKY_TEST_DEVICE_ID || '';
const token = __ENV.SKY_TEST_DEVICE_TOKEN || '';
const users = Number(__ENV.SKY_TEST_VUS || 10);
if (!/^https:\/\//.test(origin) || !/staging|stage|sandbox|test/i.test(new URL(origin).hostname)) {
  throw new Error('Se requiere una URL HTTPS de staging. Producción está prohibida.');
}
if (!/^[a-z0-9-]{8,128}$/i.test(device) || !token || token.length < 16) {
  throw new Error('Se requiere un dispositivo de prueba emparejado y token privado.');
}
if (!Number.isInteger(users) || users < 1 || users > 100) {
  throw new Error('Esta prueba smoke admite entre 1 y 100 usuarios virtuales.');
}
export const errors = new Rate('sky_backend_errors');
export const options = {
  vus: users,
  duration: __ENV.SKY_TEST_DURATION || '1m',
  thresholds: {
    http_req_duration: ['p(95)<1500'],
    sky_backend_errors: ['rate<0.01'],
  },
};

export default function () {
  const response = http.get(
    `${origin}/api/sky/mobile-agent/devices/${encodeURIComponent(device)}/home-status`,
    {
      headers: { 'X-SKY-MOBILE-TOKEN': token, Accept: 'application/json' },
      tags: { endpoint: 'sky-android-status-staging' },
      timeout: '6s',
    }
  );
  const valid = check(response, {
    'HTTP 200': r => r.status === 200,
    'JSON con servidor activo': r => r.status === 200 && r.json('server_online') === true,
  });
  errors.add(!valid);
  sleep(1); // tasa limitada para no provocar daño a servicios no preparados
}
