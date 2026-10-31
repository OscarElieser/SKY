// SKY-IA control-plane readiness on the existing SKY Supabase project.
// Hosted monitoring is not hosted GPU inference. JWT verification is enforced
// by the Supabase gateway. There is no token in this source or in the response.
// This function neither controls devices nor reads customer conversations.
const jsonHeaders = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

Deno.serve(async (req: Request) => {
  if (req.method !== "GET") {
    return new Response(JSON.stringify({ error: "method_not_allowed" }), {
      status: 405, headers: { ...jsonHeaders, allow: "GET" },
    });
  }

  let backendStatus: "not_configured" | "reachable" | "unreachable" = "not_configured";
  const configured = Deno.env.get("SKY_BACKEND_HEALTH_URL")?.trim() || "";
  // Server-side configuration only, not caller-controlled. Never inspect or
  // report credentials, hostnames, response bodies or internal error details.
  if (configured) {
    try {
      const url = new URL(configured);
      if (url.protocol !== "https:" || url.username || url.password ||
          url.search || url.hash || url.pathname !== "/api/health") {
        backendStatus = "unreachable";
      } else {
        const ac = new AbortController();
        const response = await fetch(url.toString(), {
          method: "GET", redirect: "error", cache: "no-store",
          signal: AbortSignal.timeout(2500),
          headers: { accept: "application/json" },
        });
        backendStatus = response.ok ? "reachable" : "unreachable";
        ac.abort();
      }
    } catch {
      backendStatus = "unreachable";
    }
  }

  return new Response(JSON.stringify({
    service: "SKY-IA control plane",
    status: "online",
    cloud_provider: "supabase-edge",
    backend_api: backendStatus,
    ollama_inference: "not_verified",
    android_release_validated: false,
    commercial_launch_approved: false,
    note: "This checks the cloud control plane, not an AI model response or production capacity.",
  }), { status: 200, headers: jsonHeaders });
});
