import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const backend = readFileSync("supabase/functions/sky-instagram/index.ts", "utf8");
const android = readFileSync(
  "mobile/android-agent/app/src/main/java/ni/sky/mobileagent/SkyInstagramMobileLink.kt",
  "utf8",
);

test("mobile profile API requires an authorized revocable device credential", () => {
  assert.match(backend, /path === "mobile-profile" && req\.method === "GET"/);
  assert.match(backend, /path === "mobile-profile"[\s\S]{0,140}mobileAuthorized\(req\)/);
  assert.match(backend, /return await verifiedProfile\(\)/);
});

test("identity checks revalidate Meta token and use the correct provider host", () => {
  assert.match(backend, /await decryptToken\(row\)/);
  assert.match(backend, /await inspectToken\(token\)/);
  assert.match(backend, /"graph\.instagram\.com", "me", "id,username,account_type"/);
  assert.match(backend, /"graph\.facebook\.com", "me\/accounts"/);
  assert.match(backend, /"pages_show_list"/);
  assert.match(backend, /"pages_read_engagement"/);
  assert.match(backend, /profiles\.length === 1/);
  assert.match(backend, /profile_verified: true/);
});

test("tokens and secrets never appear in the authorized profile JSON response", () => {
  const block = backend.slice(backend.indexOf("async function verifiedProfile()"),
    backend.indexOf("async function status()"));
  assert.ok(block.length > 800);
  assert.doesNotMatch(block, /json\(\{[^\n]*\btoken\s*[,}]/);
  assert.doesNotMatch(block, /json\(\{[^\n]*token_ciphertext/);
  assert.match(backend, /name: "AES-GCM"/);
});

test("Android has explicit identity-check action and does not publish", () => {
  assert.match(android, /"\/mobile-profile"/);
  assert.match(android, /"Verificar identidad real con Meta"/);
  assert.match(android, /!host\.isFinishing/);
  assert.match(android, /"ATENCIÓN: no coincide con el perfil local @"/);
  assert.doesNotMatch(android, /"\/mobile-publish"/);
});

test("mobile reauthorization is device authenticated, OAuth-only and opt-in", () => {
  assert.match(backend, /path === "mobile-start" && req\.method === "POST"/);
  assert.match(backend, /path === "mobile-start"[\s\S]{0,150}mobileAuthorized\(req\)/);
  assert.match(backend, /return await start\(\)/);
  assert.match(backend, /const raw = crypto\.getRandomValues\(new Uint8Array\(32\)\)/);
  assert.match(android, /"Renovar autorización oficial con Meta"/);
  assert.match(android, /"\/mobile-start","POST",credential/);
  assert.match(android, /Intent\(Intent\.ACTION_VIEW,url\)/);
  assert.match(android, /url\.scheme=="https"/);
  assert.match(android, /"www\.facebook\.com","business\.facebook\.com","www\.instagram\.com"/);
});
