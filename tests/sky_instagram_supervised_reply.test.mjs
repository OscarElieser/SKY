import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const backend = readFileSync("supabase/functions/sky-instagram/index.ts", "utf8");
const main = readFileSync(
  "mobile/android-agent/app/src/main/java/ni/sky/mobileagent/MainActivity.kt", "utf8");
const mobile = readFileSync(
  "mobile/android-agent/app/src/main/java/ni/sky/mobileagent/SkyInstagramAlerts.kt", "utf8");

test("prepare, confirm and status routes require authorized paired mobile device", () => {
  for (const [name, method] of [["mobile-reply-prepare","POST"],
                                ["mobile-reply-confirm","POST"],
                                ["mobile-reply-status","GET"]]) {
    assert.ok(backend.includes(`path === "${name}" && req.method === "${method}"`));
    const idx=backend.indexOf(`path === "${name}" && req.method === "${method}"`);
    const boundary=backend.slice(idx,idx+210);
    assert.match(boundary,/mobileAuthorized\(req\)/);
  }
});

test("outbound is disabled by default and uses a deliberate per-message yes", () => {
  assert.match(backend,/const outboundEnabled = \(\) => env\("SKY_INSTAGRAM_OUTGOING_ENABLED"\) === "true"/);
  assert.match(backend,/if \(!outboundEnabled\(\)\)/);
  assert.match(backend,/body.owner_confirmed !== true/);
  assert.match(main,/SkyInstagramDraftFlow.Command.SEND_REQUEST -> \{\s*sendApprovedInstagramReply\(\)/);
  assert.match(main,/instagramLastDraftUntil = 0L/);
  assert.match(mobile,/\.put\("owner_confirmed", true\)/);
});

test("recipient must come from recent verified incoming webhook, never user text", () => {
  assert.match(backend,/recipient_id: incoming.actor_id/);
  assert.match(backend,/ig_account_id: incoming.ig_account_id/);
  assert.match(backend,/String\(event.ig_account_id\) !== String\(event.target_id\)/);
  assert.match(backend,/const lastIncomingWindowMs = 23 \* 60 \* 60 \* 1000/);
  assert.match(backend,/sourceIncoming\(String\(row.event_key \|\| ""\)\)/);
  assert.doesNotMatch(backend,/recipient_id:\s*body\./);
});

test("outgoing text isn't persisted, and content hash is rechecked", () => {
  const begin=backend.indexOf("async function mobileReplyPrepare");
  const end=backend.indexOf("async function mobileRevoke",begin);
  const code=backend.slice(begin,end);
  assert.match(code,/reply_digest: textHash/);
  assert.match(code,/if \(await digest\(message\) !== row.reply_digest\)/);
  assert.doesNotMatch(code,/message_text:\s*message|reply_text:\s*message/);
  assert.match(code,/approvalId = crypto.randomUUID\(\)/);
  assert.match(code,/device_token_hash: deviceHash/);
});

test("atomic one-time approval prevents duplicate send after errors", () => {
  assert.match(backend,/state: "eq.prepared", expires_at: "gt\."/);
  assert.match(backend,/\{ state: "sending" \}, "return=representation"/);
  assert.match(backend,/delivery_not_confirmed_no_retry/);
  assert.match(backend,/nextState === "sent"/);
  assert.match(backend,/returnedRecipient === row.recipient_id/);
  assert.match(main,/No voy a repetirlo automáticamente|No voy a repetirlo automáticamente/);
});

test("Meta timestamp accepts seconds and milliseconds, without false history", () => {
  assert.match(backend,/n >= 946684800000 && n <= 4102444800000/);
  assert.match(backend,/n\/1000 : n/);
  assert.match(backend,/typeof event.event_at !== "string"/);
});

test("no private tokens are returned to Android", () => {
  const start=backend.indexOf("async function mobileReplyPrepare");
  const end=backend.indexOf("async function mobileRevoke", start);
  const code=backend.slice(start,end);
  assert.doesNotMatch(code,/return json\(\{[^\n]*\bpageToken\b/);
  assert.doesNotMatch(code,/return json\(\{[^\n]*\btoken_ciphertext\b/);
});
