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
  return crypto.subtle.importKey("raw", bytes, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
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
  const expected = new Uint8Array(await crypto.subtle.sign("HMAC", key, body));
  const provided = Uint8Array.from(signature.slice(7).match(/.{2}/g) || [],
    s => parseInt(s, 16));
  return equalBytes(expected, provided);
}
async function webhook(req: Request) {
  if (req.method === "GET") {
    const p = new URL(req.url).searchParams;
    const challenge = p.get("hub.challenge") || "";
    const token = p.get("hub.verify_token") || "";
    const expected = env("SKY_INSTAGRAM_WEBHOOK_VERIFY_TOKEN");
    if (expected.length < 24 || p.get("hub.mode") !== "subscribe" ||
        !challenge || token.length !== expected.length ||
        !equalBytes(encoder(token), encoder(expected))) return json({ error: "forbidden" }, 403);
    return new Response(challenge, { headers: { "content-type": "text/plain", "cache-control": "no-store" } });
  }
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405);
  const body = new Uint8Array(await req.arrayBuffer());
  if (body.byteLength > 1024 * 1024) return json({ error: "too_large" }, 413);
  if (!(await signatureOk(body, req.headers.get("x-hub-signature-256") || ""))) {
    return json({ error: "invalid_signature" }, 403);
  }
  // Verified delivery only. No logging personal message bodies, no automated replies.
  return json({ received: true });
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
    if (path === "mobile-profile" && req.method === "GET") {
      if (!(await mobileAuthorized(req))) return json({ error: "unauthorized" }, 401);
      return await verifiedProfile();
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
    if (path === "disconnect" && req.method === "POST") return await disconnect();
    return json({ error: "not_found" }, 404);
  } catch {
    return json({ error: "service_unavailable" }, 503);
  }
});
