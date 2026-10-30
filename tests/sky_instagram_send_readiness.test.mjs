import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const backend = readFileSync("supabase/functions/sky-instagram/index.ts", "utf8");

test("readiness is a GET-only device-authenticated endpoint", () => {
  assert.match(backend, /path === "mobile-send-readiness" && req\.method === "GET"/);
  assert.match(backend, /path === "mobile-send-readiness"[\s\S]{0,165}mobileAuthorized\(req\)/);
  assert.match(backend, /return await mobileSendReadiness\(\)/);
  assert.doesNotMatch(backend, /path === "mobile-send" && req\.method === "POST"/);
});

test("checks Meta Page token and MESSAGING task without exposing credential data", () => {
  const start = backend.indexOf("async function mobileSendReadiness()");
  const end = backend.indexOf("async function mobileRevoke(", start);
  assert.ok(start > 0 && end > start);
  const block = backend.slice(start, end);
  assert.match(block, /"instagram_manage_messages"/);
  assert.match(block, /"id,tasks,access_token,instagram_business_account\{id,username\}"/);
  assert.match(block, /tasks\.includes\("MESSAGING"\)/);
  assert.match(block, /preflight_ok: ready, outgoing_enabled: false, send_tested: false/);
  assert.doesNotMatch(block, /return json\(\{[^\n]*(?:access_token:|token_ciphertext:|token_iv:)/);
  assert.doesNotMatch(block, /\bmethod:\s*"POST"/);
});

test("no misleading send success or message transmission is exposed", () => {
  assert.match(backend, /awaiting_supervised_send_implementation/);
  assert.match(backend, /send_tested: false/);
  assert.doesNotMatch(backend, /graph\.facebook\.com\/v26\.0\/.*messages/);
});
