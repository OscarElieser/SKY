import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { webcrypto } from "node:crypto";

const source = readFileSync("supabase/functions/sky-instagram/index.ts", "utf8");
const match = source.match(/const raw = ([\s\S]+?);\s+await database\("sky_instagram_mobile_devices"/);
assert.ok(match, "The production token expression must remain detectable");

// Exercise the expression used by the deployed Edge Function, not a copied implementation.
const generate = new Function("b64", "crypto", "return (" + match[1] + ");");
const b64 = (bytes) => Buffer.from(bytes).toString("base64");

test("Instagram credentials are always valid URL-safe 256-bit tokens", () => {
  for (let i = 0; i < 10_000; i++) {
    const token = generate(b64, webcrypto);
    assert.match(token, /^[A-Za-z0-9_-]{43}$/);
    assert.equal(Buffer.from(token.replaceAll("-", "+").replaceAll("_", "/") + "=", "base64").length, 32);
  }
});

test("Plus and slash base64 characters are normalized", () => {
  for (const value of [251, 255]) {
    const cryptoStub = { getRandomValues(array) { array.fill(value); return array; } };
    const token = generate(b64, cryptoStub);
    assert.match(token, /^[A-Za-z0-9_-]{43}$/);
  }
});

test("The token never depends on the Meta owner secret", () => {
  assert.doesNotMatch(match[1], /SKY_INSTAGRAM_OWNER_KEY|SKY_META_APP_SECRET/);
});