// SKY Android: isolated Instagram Unified Login OAuth gateway.
// No connection to SKY Windows. Tokens never leave this server.
type Json = Record<string, unknown>;
const base = (Deno.env.get("SUPABASE_URL") || "").replace(/\/$/, "");
const funcName = "sky-instagram";
const callback = base + "/functions/v1/" + funcName + "/callback";
const env = (name: string) => (Deno.env.get(name) || "").trim();
const enc = new TextEncoder();
const encoder = (value: string) => enc.encode(value);
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), {
  status, headers: {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
  },
});
const page = (ok: boolean) => new Response(
  "<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'></head>" +
  "<body><h1>" + (ok ? "Instagram autorizado" : "No se completo la conexion") +
  "</h1><p>" + (ok ? "Regresa a SKY Android y comprueba el estado de Instagram." :
  "Vuelve a SKY Android e inicia una nueva autorizacion. Ningun token se ha mostrado.") +
  "</p></body></html>",
  { status: ok ? 200 : 400, headers: {
    "content-type": "text/html; charset=utf-8",
    "cache-control": "no-store",
    "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
  } },
);
const hex = (buffer: ArrayBuffer) => [...new Uint8Array(buffer)].map(v => v.toString(16).padStart(2, "0")).join("");
const digest = async (value: string) => hex(await crypto.subtle.digest("SHA-256", encoder(value)));
function equalBytes(left: Uint8Array, right: Uint8Array) {
  if (left.length !== right.length) return false;
  let diff = 0;
  for (let i = 0; i < left.length; i++) diff |= left[i] ^ right[i];
  return diff === 0;
}
const b64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes));
// A fresh ArrayBuffer satisfies strict WebCrypto types in current Deno/TypeScript.
const ownedBuffer = (data: Uint8Array): ArrayBuffer => {
  const result = new ArrayBuffer(data.byteLength);
  new Uint8Array(result).set(data);
  return result;
};
async function owner(req: Request) {
  const secret = env("SKY_INSTAGRAM_OWNER_KEY");
  const input = req.headers.get("authorization") || "";
  if (secret.length < 32 || !input.startsWith("Bearer ") || input.length > 600) return false;
  const provided = input.slice(7);
  const a = new Uint8Array(await crypto.subtle.digest("SHA-256", encoder(secret)));
  const b = new Uint8Array(await crypto.subtle.digest("SHA-256", encoder(provided)));
  return equalBytes(a, b);
}
function configured() {
  const url = env("SKY_META_LOGIN_URL");
  if (!base.startsWith("https://") || !env("SKY_META_APP_ID") ||
      !env("SKY_META_APP_SECRET") || env("SKY_INSTAGRAM_OWNER_KEY").length < 32 ||
      !env("SKY_INSTAGRAM_ENCRYPTION_KEY_B64") || !url) return false;
  try {
    const u = new URL(url);
    return u.protocol === "https:" &&
      ["www.facebook.com", "business.facebook.com", "www.instagram.com"].includes(u.hostname) &&
      (/\/dialog\/oauth$|\/oauth\/authorize$/.test(u.pathname)) &&
      u.searchParams.get("client_id") === env("SKY_META_APP_ID") &&
      u.searchParams.get("redirect_uri") === callback &&
      u.searchParams.get("response_type") === "code" &&
      !!u.searchParams.get("config_id");
  } catch { return false; }
}
function adminKey() {
  const secret = env("SUPABASE_SERVICE_ROLE_KEY");
  if (!secret || !base) throw Error("Private data store unavailable");
  return secret;
}
async function database(table: string, method: string, query = "", payload?: unknown,
                        prefer?: string): Promise<unknown> {
  const key = adminKey();
  const res = await fetch(base + "/rest/v1/" + table + query, {
    method,
    headers: {
      "apikey": key, "authorization": "Bearer " + key,
      "content-type": "application/json",
      ...(prefer ? { prefer } : {}),
    },
    ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
  });
  if (!res.ok) throw Error("Database unavailable");
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}
async function encryptionKey() {
  const raw = env("SKY_INSTAGRAM_ENCRYPTION_KEY_B64");
  let bytes: Uint8Array;
  try { bytes = Uint8Array.from(atob(raw), c => c.charCodeAt(0)); }
  catch { throw Error("Invalid server encryption key"); }
  if (bytes.length !== 32) throw Error("Invalid server encryption key length");
  return crypto.subtle.importKey("raw", ownedBuffer(bytes), { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
}
async function encryptToken(token: string) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const result = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await encryptionKey(), encoder(token));
  return { token_ciphertext: b64(new Uint8Array(result)), token_iv: b64(iv) };
}
async function start() {
  if (!configured()) return json({ error: "oauth_not_configured" }, 503);
  // Validate the encryption key BEFORE issuing a login URL.
  await encryptionKey();
  const raw = crypto.getRandomValues(new Uint8Array(32));
  const state = b64(raw).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  const stateHash = await digest(state);
  await database("sky_instagram_oauth_states", "POST", "", {
    state_hash: stateHash,
    expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
  }, "return=minimal");
  const login = new URL(env("SKY_META_LOGIN_URL"));
  login.searchParams.set("state", state);
  return json({ authorization_url: login.toString(), expires_in_seconds: 600 });
}
async function consumeState(value: string) {
  if (!/^[A-Za-z0-9_-]{35,100}$/.test(value)) return false;
  const stateHash = await digest(value);
  const filter = new URLSearchParams({
    state_hash: "eq." + stateHash,
    used_at: "is.null",
    expires_at: "gt." + new Date().toISOString(),
  });
  const updated = await database("sky_instagram_oauth_states", "PATCH", "?" + filter.toString(),
    { used_at: new Date().toISOString() }, "return=representation");
  return Array.isArray(updated) && updated.length === 1;
}
async function exchange(code: string) {
  const uri = new URL("https://graph.facebook.com/v26.0/oauth/access_token");
  uri.searchParams.set("client_id", env("SKY_META_APP_ID"));
  uri.searchParams.set("client_secret", env("SKY_META_APP_SECRET"));
  uri.searchParams.set("redirect_uri", callback);
  uri.searchParams.set("code", code);
  const response = await fetch(uri.toString(), { method: "GET", headers: { accept: "application/json" } });
  if (!response.ok) throw Error("Meta OAuth exchange denied");
  const data = await response.json() as Json;
  if (typeof data.access_token !== "string" || data.access_token.length < 20) throw Error("No access token");
  return data;
}
async function inspectToken(token: string) {
  const url = new URL("https://graph.facebook.com/v26.0/debug_token");
  url.searchParams.set("input_token", token);
  url.searchParams.set("access_token", env("SKY_META_APP_ID") + "|" + env("SKY_META_APP_SECRET"));
  const response = await fetch(url.toString(), { headers: { accept: "application/json" } });
  if (!response.ok) throw Error("Meta token check denied");
  const body = await response.json() as { data?: Json };
  const found = body.data || {};
  if (found.is_valid !== true || String(found.app_id || "") !== env("SKY_META_APP_ID")) {
    throw Error("Token is not valid for SKY-IA");
  }
  const scopes = Array.isArray(found.scopes) ? found.scopes.filter((v): v is string => typeof v === "string") : [];
  // A token without Instagram grants is not a connected Instagram token.
  if (!scopes.some(s => s === "instagram_basic" || s === "instagram_business_basic")) {
    throw Error("Missing Instagram grant");
  }
  return { scopes, expires_at: typeof found.expires_at === "number" && found.expires_at > 0 ?
    new Date(found.expires_at * 1000).toISOString() : null };
}
async function oauthCallback(req: Request) {
  if (!configured()) return page(false);
  const params = new URL(req.url).searchParams;
  if (params.has("error") || !params.has("code") || !params.has("state")) return page(false);
  const code = params.get("code") || "";
  const state = params.get("state") || "";
  if (code.length < 8 || code.length > 4096 || !(await consumeState(state))) return page(false);
  try {
    const issued = await exchange(code);
    const checked = await inspectToken(issued.access_token as string);
    const secured = await encryptToken(issued.access_token as string);
    // Account identity is deliberately NOT assumed from the Meta tester invitation.
    await database("sky_instagram_connections", "POST", "?on_conflict=id", {
      id: "owner", ...secured,
      scopes: checked.scopes,
      token_expires_at: checked.expires_at,
      verified_at: new Date().toISOString(),
    }, "resolution=merge-duplicates,return=minimal");
    return page(true);
  } catch {
    // No code, token, or Graph error detail is returned to the browser.
    return page(false);
  }
}

/** Read-only profile diagnostics. Instagram and Meta tokens never reach Android. */
async function decryptToken(record: Json): Promise<string> {
  const iv = Uint8Array.from(atob(String(record.token_iv || "")), c => c.charCodeAt(0));
  const ciphertext = Uint8Array.from(atob(String(record.token_ciphertext || "")), c => c.charCodeAt(0));
  if (iv.length !== 12 || ciphertext.length < 17) throw Error("Invalid stored encryption");
  const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv },
    await encryptionKey(), ciphertext);
  return new TextDecoder("utf-8", { fatal: true }).decode(plaintext);
}
async function graphRead(host: "graph.facebook.com" | "graph.instagram.com",
                         path: string, fields: string, token: string): Promise<Json | null> {
  const u = new URL("https://" + host + "/v26.0/" + path);
  u.searchParams.set("fields", fields);
  try {
    const response = await fetch(u, {
      headers: { authorization: "Bearer " + token, accept: "application/json" },
      redirect: "error", signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) return null;
    const data = await response.json() as Json;
    return data && typeof data === "object" && !Array.isArray(data) ? data : null;
  } catch { return null; }
}
const validHandle = (v: unknown) => typeof v === "string" &&
  /^[a-zA-Z0-9._]{1,30}$/.test(v);
const validId = (v: unknown) => typeof v === "string" && /^[0-9]{5,30}$/.test(v);

async function verifiedProfile(): Promise<Response> {
  const result = await database("sky_instagram_connections", "GET",
    "?id=eq.owner&select=token_ciphertext,token_iv,token_expires_at,verified_at");
  const row = Array.isArray(result) && result.length === 1 ? result[0] as Json : null;
  if (!row) return json({ token_valid: false, profile_verified: false, reason: "not_connected" });
  if (typeof row.token_expires_at === "string" &&
      Date.parse(row.token_expires_at) <= Date.now()) {
    return json({ token_valid: false, profile_verified: false, reason: "token_expired" });
  }
  let token: string;
  let tokenInfo: { scopes: string[]; expires_at: string | null };
  try {
    token = await decryptToken(row);
    tokenInfo = await inspectToken(token);
  } catch {
    return json({ token_valid: false, profile_verified: false, reason: "token_invalid_or_unavailable" });
  }
  const expiresAt = tokenInfo.expires_at;
  if (expiresAt && Date.parse(expiresAt) <= Date.now()) {
    return json({ token_valid: false, profile_verified: false,
      token_expires_at: expiresAt, reason: "token_expired" });
  }
  const baseStatus = { token_valid: true, profile_verified: false, token_expires_at: expiresAt };
  // The token grants decide the host. Facebook Login cannot impersonate Instagram Login.
  if (tokenInfo.scopes.includes("instagram_business_basic")) {
    const p = await graphRead("graph.instagram.com", "me", "id,username,account_type", token);
    if (p && validHandle(p.username) && validId(String(p.id || ""))) {
      return json({ ...baseStatus, profile_verified: true, username: p.username,
        profile_id: String(p.id), account_type: typeof p.account_type === "string" ?
        p.account_type : null, login_type: "instagram" });
    }
    return json({ ...baseStatus, reason: "instagram_profile_unavailable" });
  }
  if (tokenInfo.scopes.includes("instagram_basic")) {
    // Facebook Login requires a connected Facebook Page and Page grants.
    if (!tokenInfo.scopes.includes("pages_show_list") ||
        !tokenInfo.scopes.includes("pages_read_engagement")) {
      return json({ ...baseStatus, reason: "missing_facebook_page_permissions" });
    }
    const p = await graphRead("graph.facebook.com", "me/accounts",
      "instagram_business_account{id,username}", token);
    const accounts = Array.isArray(p?.data) ? p.data : [];
    const profiles = accounts.map((x: unknown) => {
      if (!x || typeof x !== "object") return null;
      const item = x as Json;
      const ig = item.instagram_business_account as Json | undefined;
      return ig && validId(String(ig.id || "")) && validHandle(ig.username) ?
        { profile_id: String(ig.id), username: ig.username as string } : null;
    }).filter((x): x is { profile_id: string; username: string } => x !== null);
    if (profiles.length === 1) {
      return json({ ...baseStatus, ...profiles[0], profile_verified: true,
        login_type: "facebook" });
    }
    return json({ ...baseStatus, reason: profiles.length > 1 ?
      "multiple_authorized_profiles" : "facebook_page_profile_unavailable" });
  }
  return json({ ...baseStatus, reason: "instagram_basic_permission_missing" });
}

async function status() {
  const data = await database("sky_instagram_connections", "GET",
    "?id=eq.owner&select=verified_at,token_expires_at,scopes");
  const record = Array.isArray(data) && data.length ? data[0] : null;
  return json({ configured: configured(), token_verified: !!record, connection: record || null,
    instagram_profile_verified: false });
}
async function disconnect() {
  await database("sky_instagram_connections", "DELETE", "?id=eq.owner", undefined, "return=minimal");
  return json({ disconnected: true, note: "Also revoke SKY-IA in Instagram app permissions." });
}
async function signatureOk(body: Uint8Array, signature: string) {
  const secret = env("SKY_META_APP_SECRET");
  if (!secret || !/^sha256=[0-9a-f]{64}$/.test(signature)) return false;
  const key = await crypto.subtle.importKey("raw", encoder(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const expected = new Uint8Array(await crypto.subtle.sign("HMAC", key, ownedBuffer(body)));
  const provided = Uint8Array.from(signature.slice(7).match(/.{2}/g) || [],
    s => parseInt(s, 16));
  return equalBytes(expected, provided);
}

/** Minimal private ingestion: never save raw webhooks, secrets, or Meta test samples. */
function eventObject(v: unknown): Json {
  return v && typeof v === "object" && !Array.isArray(v) ? v as Json : {};
}
function bounded(v: unknown, limit=80): string | null {
  if (typeof v !== "string" && typeof v !== "number") return null;
  const s=String(v); return s.length > 0 && s.length <= limit ? s : null;
}
function eventText(v: unknown): string | null {
  return typeof v === "string" ? v.slice(0,4000) : null;
}
function eventTime(v: unknown): string | null {
  if (typeof v !== "string" && typeof v !== "number") return null;
  const n=Number(v);
  const seconds=n >= 946684800000 && n <= 4102444800000 ?
    n/1000 : n;
  return Number.isFinite(seconds) && seconds >= 946684800 &&
    seconds <= 4102444800 ?
    new Date(seconds*1000).toISOString() : null;
}
type InstagramInboxEvent = {
  event_key:string; event_type:"message"|"comment"|"mention";
  ig_account_id:string; actor_id:string|null; target_id:string|null;
  external_event_id:string|null; message_text:string|null; event_at:string|null;
};
async function normalizeInstagramWebhook(input: Json):Promise<InstagramInboxEvent[]> {
  if (input.object !== "instagram" || !Array.isArray(input.entry)) return [];
  const events:InstagramInboxEvent[]=[];
  for (const entryValue of input.entry) {
    const entry=eventObject(entryValue), account=bounded(entry.id);
    if (!account) continue;
    if (Array.isArray(entry.messaging)) for (const raw of entry.messaging) {
      const m=eventObject(raw), msg=eventObject(m.message);
      const id=bounded(msg.mid,180);
      // Do not mistake delivery receipts or other messaging events for a DM.
      if (!id && typeof msg.text !== "string") continue;
      events.push({
        event_key:await digest(JSON.stringify(["instagram",account,"message",id || JSON.stringify(m)])),
        event_type:"message",ig_account_id:account,
        actor_id:bounded(eventObject(m.sender).id),
        target_id:bounded(eventObject(m.recipient).id),
        external_event_id:id, message_text:eventText(msg.text),
        event_at:eventTime(m.timestamp)
      });
    }
    if (Array.isArray(entry.changes)) for (const raw of entry.changes) {
      const change=eventObject(raw);
      if (change.field !== "comments" && change.field !== "mentions") continue;
      const v=eventObject(change.value);
      const kind=change.field === "comments" ? "comment" : "mention";
      const id=bounded(v.id,180);
      events.push({
        event_key:await digest(JSON.stringify(["instagram",account,kind,id || JSON.stringify(v)])),
        event_type:kind, ig_account_id:account,
        actor_id:bounded(eventObject(v.from).id),
        target_id:bounded(v.media_id) || bounded(eventObject(v.media).id),
        external_event_id:id,message_text:eventText(v.text),
        event_at:eventTime(entry.time)
      });
    }
  }
  return [...new Map(events.map(e=>[e.event_key,e])).values()];
}
async function privateInstagramInbox() {
  const select="?select=event_key,event_type,ig_account_id,actor_id,target_id,external_event_id,message_text,event_at,received_at,processing_status&order=received_at.desc&limit=50";
  const rows=await database("sky_instagram_webhook_events","GET",select);
  return json({ events:Array.isArray(rows) ? rows : [],limit:50 });
}
async function webhook(req:Request) {
  if (req.method === "GET") {
    const p=new URL(req.url).searchParams;
    const challenge=p.get("hub.challenge") || "";
    const token=p.get("hub.verify_token") || "";
    const expected=env("SKY_INSTAGRAM_WEBHOOK_VERIFY_TOKEN");
    if (expected.length < 24 || p.get("hub.mode") !== "subscribe" ||
        !challenge || token.length !== expected.length ||
        !equalBytes(encoder(token),encoder(expected))) return json({error:"forbidden"},403);
    return new Response(challenge,{headers:{"content-type":"text/plain","cache-control":"no-store"}});
  }
  if (req.method !== "POST") return json({error:"method_not_allowed"},405);
  const body=new Uint8Array(await req.arrayBuffer());
  if (body.byteLength > 1024*1024) return json({error:"too_large"},413);
  if (!(await signatureOk(body,req.headers.get("x-hub-signature-256") || "")))
    return json({error:"invalid_signature"},403);
  let parsed:Json;
  try { parsed=eventObject(JSON.parse(new TextDecoder().decode(body))); }
  catch { return json({error:"invalid_json"},400); }
  // Meta sends {"sample":...} test envelopes; do not store a fake customer message.
  if ("sample" in parsed) return json({received:true,sample:true,stored:0});
  const events=await normalizeInstagramWebhook(parsed);
  if (events.length>1000) return json({error:"too_many_events"},413);
  if (!events.length) return json({received:true,stored:0});
  // Atomic, idempotent batch. Failure yields 503 so Meta can retry.
  await database("sky_instagram_webhook_events","POST",
    "?on_conflict=event_key",events,"resolution=ignore-duplicates,return=minimal");
  // No automatic replies and no personal-content logs.
  return json({received:true,accepted:events.length});
}

/** Temporary pairing via owner-authorized CLI; mobile receives only revocable credential. */
const pairCode = () => Array.from(crypto.getRandomValues(new Uint8Array(9)), x => x.toString(16).padStart(2,"0")).join("");
async function pairCreate() {
  const code = pairCode();
  await database("sky_instagram_pairing_codes","POST","",{
    code_hash: await digest(code),
    expires_at: new Date(Date.now()+10*60*1000).toISOString()
  },"return=minimal");
  return json({pairing_code:code,expires_in_seconds:600});
}
async function pairClaim(req: Request) {
  const data = await req.json() as Json;
  const code = typeof data.code === "string" ? data.code.trim() : "";
  if(!/^[0-9a-f]{18}$/.test(code))return json({error:"invalid_code"},400);
  const q = new URLSearchParams({code_hash:"eq."+await digest(code),
    claimed_at:"is.null",expires_at:"gt."+new Date().toISOString()});
  const rows = await database("sky_instagram_pairing_codes","PATCH","?"+q.toString(),
    {claimed_at:new Date().toISOString()},"return=representation");
  if(!Array.isArray(rows)||rows.length!==1)return json({error:"invalid_or_expired_code"},403);
  const raw = b64(crypto.getRandomValues(new Uint8Array(32)))
    .replaceAll("+","-").replaceAll("/","_").replace(/=+$/g,"");
  await database("sky_instagram_mobile_devices","POST","",{
    token_hash:await digest(raw),device_label:"SKY Android",
    expires_at:new Date(Date.now()+30*24*60*60*1000).toISOString()
  },"return=minimal");
  return json({device_token:raw,expires_in_seconds:2592000});
}
async function mobileAuthorized(req:Request):Promise<boolean> {
  const h=req.headers.get("authorization")||"";
  if(!h.startsWith("Bearer "))return false;
  const token=h.slice(7);
  if(!/^[A-Za-z0-9_-]{43}$/.test(token))return false;
  const f=new URLSearchParams({token_hash:"eq."+await digest(token),
    revoked_at:"is.null",expires_at:"gt."+new Date().toISOString()});
  const records=await database("sky_instagram_mobile_devices","GET","?"+f.toString()+"&select=token_hash");
  return Array.isArray(records)&&records.length===1;
}
async function mobileStatus() {
  const record=await database("sky_instagram_connections","GET",
    "?id=eq.owner&select=verified_at,token_expires_at,scopes");
  const found=Array.isArray(record)&&record.length?record[0]:null;
  return json({authorized:!!found,profile_verified:false,connection:found});
}
/** Read-only preflight for Facebook Login/Page-based Instagram messaging.
 * Never returns tokens or sends a DM. A positive result is NOT a send receipt.
 */
async function mobileSendReadiness(): Promise<Response> {
  const found = await database("sky_instagram_connections", "GET",
    "?id=eq.owner&select=token_ciphertext,token_iv,token_expires_at,verified_at");
  const row = Array.isArray(found) && found.length === 1 ? found[0] as Json : null;
  if (!row || typeof row.verified_at !== "string") return json({
    connected: false, preflight_ok: false, send_tested: false,
    outgoing_enabled: false, reason: "no_verified_instagram_connection"
  });
  if (typeof row.token_expires_at === "string" &&
      Date.parse(row.token_expires_at) <= Date.now()) return json({
    connected: true, preflight_ok: false, send_tested: false,
    outgoing_enabled: false, reason: "expired_token"
  });
  let token: string, scopeInfo: { scopes:string[]; expires_at:string|null };
  try {
    token = await decryptToken(row);
    scopeInfo = await inspectToken(token);
  } catch {
    return json({ connected: true, preflight_ok: false,
      send_tested: false, outgoing_enabled: false, reason: "invalid_meta_token" });
  }
  if (scopeInfo.expires_at && Date.parse(scopeInfo.expires_at) <= Date.now())
    return json({ connected: true, preflight_ok: false,
      send_tested: false, outgoing_enabled: false, reason: "expired_meta_token" });

  if (scopeInfo.scopes.includes("instagram_business_manage_messages")) {
    return json({ connected: true, login_type: "instagram",
      preflight_ok: false, send_tested: false, outgoing_enabled: false,
      reason: "instagram_login_send_not_configured" });
  }
  const required = ["instagram_basic","instagram_manage_messages","pages_show_list"];
  const missing = required.filter(scope => !scopeInfo.scopes.includes(scope));
  if (missing.length > 0) {
    return json({ connected: true, login_type: "facebook", preflight_ok: false,
      send_tested: false, outgoing_enabled: false,
      reason: "missing_permissions", missing_permissions: missing });
  }
  const result = await graphRead("graph.facebook.com", "me/accounts",
    "id,tasks,access_token,instagram_business_account{id,username}", token);
  if (!result || !Array.isArray(result.data)) {
    return json({ connected: true, login_type: "facebook", preflight_ok: false,
      send_tested: false, outgoing_enabled: false,
      reason: "page_lookup_unavailable" });
  }
  const pages = result.data.map(item => {
    const p = eventObject(item);
    const ig = eventObject(p.instagram_business_account);
    const tasks = Array.isArray(p.tasks) ? p.tasks : [];
    return { pageId: String(p.id || ""), instagramId: String(ig.id || ""),
      hasPageToken: typeof p.access_token === "string" && p.access_token.length >= 20,
      messagingTask: tasks.includes("MESSAGING") };
  }).filter(p => validId(p.pageId) && validId(p.instagramId));
  if (pages.length !== 1) return json({
    connected: true, login_type: "facebook", preflight_ok: false,
    send_tested: false, outgoing_enabled: false,
    reason: pages.length > 1 ? "multiple_linked_pages" : "missing_linked_instagram_page"
  });
  const page = pages[0];
  // Never serialize page access tokens, user access tokens, or Meta secrets.
  const ready = page.hasPageToken && page.messagingTask;
  return json({ connected: true, login_type: "facebook",
    profile_verified: true, page_token_available: page.hasPageToken,
    page_messaging_task: page.messagingTask,
    preflight_ok: ready, outgoing_enabled: false, send_tested: false,
    reason: ready ? "awaiting_supervised_send_implementation" :
      "page_token_or_messaging_task_missing",
    extra_review: "Verify Meta App Review, permission scope, and messaging window before send."
  });
}


/**
 * Instagram owner-supervised reply transport. No automatic sending:
 * - every candidate references a verified, recent incoming webhook
 * - text is never persisted, only its digest
 * - one short-lived approval per exact device/event/text
 * - one atomic prepared->sending transition and no automatic retries
 * - sending is explicitly gated by a production server-side feature flag
 */
const outboundEnabled = () => env("SKY_INSTAGRAM_OUTGOING_ENABLED") === "true";
const approvalPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const eventPattern = /^[0-9a-f]{64}$/;
const replyLimit = 950;
const lastIncomingWindowMs = 23 * 60 * 60 * 1000; // conservative, within Meta's 24h window
const approvalLifeMs = 2 * 60 * 1000;

async function ownerDeviceHash(req: Request): Promise<string> {
  const header = req.headers.get("authorization") || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!/^[A-Za-z0-9_-]{43}$/.test(token)) throw Error("invalid_device");
  return digest(token);
}
async function replyInput(req: Request): Promise<Json> {
  const size = Number(req.headers.get("content-length") || "0");
  if (size > 5000) throw Error("payload_too_large");
  const raw = await req.text();
  if (raw.length > 5000) throw Error("payload_too_large");
  const body = JSON.parse(raw) as unknown;
  if (!body || typeof body !== "object" || Array.isArray(body))
    throw Error("invalid_payload");
  return body as Json;
}
function replyText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim();
  if (!text || text.length > replyLimit ||
      encoder(text).byteLength > 1000 ||
      /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/.test(text)) return null;
  return text;
}
function freshIncoming(event: Json): boolean {
  if (event.event_type !== "message" || !eventPattern.test(String(event.event_key || "")) ||
      !validId(String(event.ig_account_id || "")) ||
      !validId(String(event.actor_id || "")) ||
      !validId(String(event.target_id || "")) ||
      String(event.ig_account_id) !== String(event.target_id) ||
      typeof event.event_at !== "string") return false;
  const received = Date.parse(event.event_at);
  const elapsed = Date.now() - received;
  return Number.isFinite(received) && elapsed >= 0 && elapsed < lastIncomingWindowMs;
}
async function sourceIncoming(eventKey: string): Promise<Json | null> {
  if (!eventPattern.test(eventKey)) return null;
  const query = "?event_key=eq." + eventKey +
    "&select=event_key,event_type,ig_account_id,actor_id,target_id,event_at";
  const records = await database("sky_instagram_webhook_events", "GET", query);
  const event = Array.isArray(records) && records.length === 1 ?
    records[0] as Json : null;
  return event && freshIncoming(event) ? event : null;
}
async function instagramPageFor(accountId: string): Promise<
  { pageId: string; pageToken: string } | null
> {
  const connections = await database("sky_instagram_connections", "GET",
    "?id=eq.owner&select=token_ciphertext,token_iv,token_expires_at,verified_at");
  const record = Array.isArray(connections) && connections.length === 1 ?
    connections[0] as Json : null;
  if (!record || typeof record.verified_at !== "string" ||
      (typeof record.token_expires_at === "string" &&
       Date.parse(record.token_expires_at) <= Date.now())) return null;
  try {
    const userToken = await decryptToken(record);
    const grants = await inspectToken(userToken);
    if (!["instagram_basic","instagram_manage_messages","pages_show_list",
           "pages_read_engagement"].every(x => grants.scopes.includes(x))) return null;
    if (grants.expires_at && Date.parse(grants.expires_at) <= Date.now()) return null;
    const response = await graphRead("graph.facebook.com", "me/accounts",
      "id,tasks,access_token,instagram_business_account{id,username}", userToken);
    const pages = Array.isArray(response?.data) ? response.data : [];
    const matched = pages.map(p => {
      const page = eventObject(p);
      const ig = eventObject(page.instagram_business_account);
      const tasks = Array.isArray(page.tasks) ? page.tasks : [];
      return {
        id: String(page.id || ""),
        ig: String(ig.id || ""),
        token: typeof page.access_token === "string" ? page.access_token : "",
        permitted: tasks.includes("MESSAGING"),
      };
    }).filter(p => validId(p.id) && p.ig === accountId &&
      p.token.length > 20 && p.permitted);
    return matched.length === 1 ?
      { pageId: matched[0].id, pageToken: matched[0].token } : null;
  } catch { return null; }
}
async function mobileReplyPrepare(req: Request): Promise<Response> {
  // Disabled rollouts must not consume one-time approvals or create stale drafts.
  if (!outboundEnabled()) return json({ error: "supervised_send_not_enabled" }, 423);
  let body: Json;
  try { body = await replyInput(req); }
  catch { return json({ error: "invalid_payload" }, 400); }
  const eventKey = String(body.event_key || "");
  const message = replyText(body.text);
  if (!eventPattern.test(eventKey) || !message)
    return json({ error: "invalid_event_or_text" }, 400);
  const incoming = await sourceIncoming(eventKey);
  if (!incoming) return json({ error: "incoming_message_missing_or_outside_24h" }, 409);
  // The recipient is ALWAYS from an authenticated webhook; never from the phone.
  const page = await instagramPageFor(String(incoming.ig_account_id));
  if (!page) return json({ error: "send_permissions_or_page_not_ready" }, 409);
  const deviceHash = await ownerDeviceHash(req);
  const textHash = await digest(message);
  const check = new URLSearchParams({
    event_key: "eq." + eventKey,
    reply_digest: "eq." + textHash,
    device_token_hash: "eq." + deviceHash,
  });
  const previous = await database("sky_instagram_outbound_approvals", "GET",
    "?" + check.toString() + "&select=approval_id,state,expires_at");
  if (Array.isArray(previous) && previous.length) {
    return json({ error: "duplicate_or_previously_prepared",
      status: (previous[0] as Json).state }, 409);
  }
  // Conservative per-device limit. The unique constraint prevents same-event
  // duplicates even if two requests race the pre-check.
  const recent = await database("sky_instagram_outbound_approvals", "GET",
    "?device_token_hash=eq." + deviceHash +
    "&created_at=gt." + encodeURIComponent(new Date(Date.now() - 3600000).toISOString()) +
    "&select=approval_id&limit=12");
  if (Array.isArray(recent) && recent.length >= 10)
    return json({ error: "hourly_limit_reached" }, 429);
  const approvalId = crypto.randomUUID();
  const expires = new Date(Date.now() + approvalLifeMs).toISOString();
  try {
    await database("sky_instagram_outbound_approvals", "POST", "", {
      approval_id: approvalId, device_token_hash: deviceHash,
      event_key: eventKey, reply_digest: textHash,
      recipient_id: incoming.actor_id, ig_account_id: incoming.ig_account_id,
      expires_at: expires, state: "prepared"
    }, "return=minimal");
  } catch {
    return json({ error: "duplicate_or_unavailable" }, 409);
  }
  return json({
    prepared: true, approval_id: approvalId, expires_at: expires,
    recipient_label: "Instagram ···" + String(incoming.actor_id).slice(-5),
    outbound_enabled: outboundEnabled(),
    // Do not falsely report sendability when the server-side feature gate is off.
    can_confirm: outboundEnabled(),
    send_tested: false,
  });
}
async function mobileReplyStatus(req: Request): Promise<Response> {
  const id = new URL(req.url).searchParams.get("approval_id") || "";
  if (!approvalPattern.test(id)) return json({ error: "invalid_approval" }, 400);
  const deviceHash = await ownerDeviceHash(req);
  const q = new URLSearchParams({ approval_id: "eq." + id,
    device_token_hash: "eq." + deviceHash });
  const rows = await database("sky_instagram_outbound_approvals", "GET",
    "?" + q.toString() + "&select=state,meta_message_id,expires_at,completed_at");
  if (!Array.isArray(rows) || rows.length !== 1)
    return json({ error: "approval_not_found" }, 404);
  const r = rows[0] as Json;
  return json({ state: r.state, message_id: r.state === "sent" ? r.meta_message_id : null,
    expires_at: r.expires_at, completed_at: r.completed_at });
}
async function mobileReplyConfirm(req: Request): Promise<Response> {
  // Cannot send unless deliberately enabled after real end-to-end tests.
  if (!outboundEnabled())
    return json({ error: "supervised_send_not_enabled" }, 423);
  let body: Json;
  try { body = await replyInput(req); }
  catch { return json({ error: "invalid_payload" }, 400); }
  const id = String(body.approval_id || "");
  const message = replyText(body.text);
  if (!approvalPattern.test(id) || !message || body.owner_confirmed !== true)
    return json({ error: "explicit_approval_required" }, 400);
  const deviceHash = await ownerDeviceHash(req);
  const filter = new URLSearchParams({
    approval_id: "eq." + id, device_token_hash: "eq." + deviceHash
  });
  const records = await database("sky_instagram_outbound_approvals", "GET",
    "?" + filter.toString() + "&select=event_key,reply_digest,state,expires_at,ig_account_id,recipient_id");
  if (!Array.isArray(records) || records.length !== 1)
    return json({ error: "approval_missing" }, 404);
  const row = records[0] as Json;
  if (row.state !== "prepared") return json({ error: "already_consumed_or_in_progress",
    status: row.state }, 409);
  if (typeof row.expires_at !== "string" || Date.parse(row.expires_at) <= Date.now())
    return json({ error: "approval_expired" }, 409);
  if (await digest(message) !== row.reply_digest)
    return json({ error: "reply_changed_reapproval_required" }, 409);
  const incoming = await sourceIncoming(String(row.event_key || ""));
  if (!incoming || incoming.ig_account_id !== row.ig_account_id ||
      incoming.actor_id !== row.recipient_id)
    return json({ error: "incoming_message_no_longer_eligible" }, 409);
  const page = await instagramPageFor(String(row.ig_account_id));
  if (!page) return json({ error: "meta_permissions_not_ready" }, 409);

  // Atomic compare-and-swap: only one concurrent request can consume approval.
  const cas = new URLSearchParams({
    approval_id: "eq." + id, device_token_hash: "eq." + deviceHash,
    state: "eq.prepared", expires_at: "gt." + new Date().toISOString()
  });
  const locked = await database("sky_instagram_outbound_approvals", "PATCH",
    "?" + cas.toString(), { state: "sending" }, "return=representation");
  if (!Array.isArray(locked) || locked.length !== 1)
    return json({ error: "approval_already_consumed" }, 409);

  let nextState = "unknown";
  let receipt: string | null = null;
  try {
    const url = "https://graph.facebook.com/v26.0/" + page.pageId + "/messages";
    const response = await fetch(url, {
      method: "POST", redirect: "error",
      headers: { authorization: "Bearer " + page.pageToken,
        "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify({
        recipient: { id: String(row.recipient_id) },
        messaging_type: "RESPONSE",
        message: { text: message },
      }),
      signal: AbortSignal.timeout(10000),
    });
    if (response.ok) {
      const data = await response.json() as Json;
      const messageId = typeof data.message_id === "string" ?
        data.message_id : "";
      const returnedRecipient = typeof data.recipient_id === "string" ?
        data.recipient_id : "";
      if (messageId.length > 5 && messageId.length <= 250 &&
          returnedRecipient === row.recipient_id) {
        nextState = "sent";
        receipt = messageId;
      }
    } else if (response.status >= 400 && response.status < 500) {
      nextState = "failed";
    }
  } catch { /* timeout is unknown: NEVER retry automatically */ }
  try {
    await database("sky_instagram_outbound_approvals", "PATCH",
      "?approval_id=eq." + id + "&state=eq.sending", {
        state: nextState, completed_at: new Date().toISOString(),
        ...(receipt ? { meta_message_id: receipt } : {})
      }, "return=minimal");
  } catch { /* state 'sending' still prevents duplicate sends */ }
  return nextState === "sent" ?
    json({ sent: true, message_id: receipt, status: "sent" }) :
    json({ sent: false, status: nextState,
      error: nextState === "unknown" ? "delivery_not_confirmed_no_retry" :
        "meta_rejected_message" }, nextState === "failed" ? 422 : 503);
}

async function mobileRevoke(req:Request) {
  const token=(req.headers.get("authorization")||"").slice(7);
  const query=new URLSearchParams({token_hash:"eq."+await digest(token)});
  await database("sky_instagram_mobile_devices","PATCH","?"+query.toString(),
    {revoked_at:new Date().toISOString()},"return=minimal");
  return json({disconnected:true});
}

Deno.serve(async (req: Request) => {
  try {
    const url = new URL(req.url);
    const path = url.pathname.split("/").filter(Boolean).slice(-1)[0] || "";
    if (req.method === "GET" && path === "health") {
      return json({ service: "sky-instagram", ready: configured(), tokens_exposed: false });
    }
    if (path === "callback" && req.method === "GET") return await oauthCallback(req);
    if (path === "webhook") return await webhook(req);
    if (path === "pair-claim" && req.method === "POST") return await pairClaim(req);
    if (path === "mobile-status" && req.method === "GET") {
      if (!(await mobileAuthorized(req)))return json({error:"unauthorized"},401);
      return await mobileStatus();
    }
    if (path === "mobile-events" && req.method === "GET") {
      if (!(await mobileAuthorized(req))) return json({error:"unauthorized"},401);
      return await privateInstagramInbox();
    }
    if (path === "mobile-profile" && req.method === "GET") {
      if (!(await mobileAuthorized(req))) return json({ error: "unauthorized" }, 401);
      return await verifiedProfile();
    }
    if (path === "mobile-send-readiness" && req.method === "GET") {
      if (!(await mobileAuthorized(req))) return json({ error: "unauthorized" }, 401);
      return await mobileSendReadiness();
    }
    if (path === "mobile-reply-prepare" && req.method === "POST") {
      if (!(await mobileAuthorized(req))) return json({ error: "unauthorized" }, 401);
      return await mobileReplyPrepare(req);
    }
    if (path === "mobile-reply-confirm" && req.method === "POST") {
      if (!(await mobileAuthorized(req))) return json({ error: "unauthorized" }, 401);
      return await mobileReplyConfirm(req);
    }
    if (path === "mobile-reply-status" && req.method === "GET") {
      if (!(await mobileAuthorized(req))) return json({ error: "unauthorized" }, 401);
      return await mobileReplyStatus(req);
    }
    // Reauthorization is initiated by the paired phone, never by an anonymous caller.
    // The Meta login URL has a one-time CSRF state; no Meta or owner tokens are returned.
    if (path === "mobile-start" && req.method === "POST") {
      if (!(await mobileAuthorized(req))) return json({ error: "unauthorized" }, 401);
      return await start();
    }
    if (path === "mobile-disconnect" && req.method === "POST") {
      if (!(await mobileAuthorized(req)))return json({error:"unauthorized"},401);
      return await mobileRevoke(req);
    }
    // All owner actions require a strong secret, including the start request.
    if (!(await owner(req))) return json({ error: "unauthorized" }, 401);
    if (path === "pair-create" && req.method === "POST") return await pairCreate();
    if (path === "start" && req.method === "POST") return await start();
    if (path === "status" && req.method === "GET") return await status();
    if (path === "profile" && req.method === "GET") return await verifiedProfile();
    if (path === "events" && req.method === "GET") return await privateInstagramInbox();
    if (path === "disconnect" && req.method === "POST") return await disconnect();
    return json({ error: "not_found" }, 404);
  } catch {
    return json({ error: "service_unavailable" }, 503);
  }
});
