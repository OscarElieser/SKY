/* Intents de ventanas del HUD: sólo navegación local, nunca acciones sobre Windows. */
(function (root) {
  "use strict";
  const norm = s => String(s || "").normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();

  function parse(input) {
    let s = norm(input).replace(/^(?:oye |hey |mira )*(?:sky )?/, "");
    let mode = null;
    const suffix = /\s+(?:en |a |de )?(?:una |la )?(?:ventana |ventanita )(?:modo |tamano )?(minimizada|minimizar|maximizada|maximizar|mini|pequena|normal|grande|pantalla completa)$/;
    const match = s.match(suffix);
    if (match) {
      const v = match[1];
      mode = v === "mini" || v === "pequena" ? "mini" :
        v === "minimizada" || v === "minimizar" ? "minimized" :
        v === "maximizada" || v === "maximizar" || v === "grande" ? "max" :
        v === "pantalla completa" ? "fullscreen" : "normal";
      s = s.slice(0, match.index).trim();
    }
    const directWindow = s.match(/^(minimiza|minimizar|maximiza|maximizar|restaura|restaurar|normaliza|cierra|cerrar)\s+(?:(?:la |el )?(?:ventana |reproductor |modulo )?(?:de )?)?(youtube|reproductor|video|buscador|busqueda|buscar)$/);
    if (directWindow) {
      const verb = directWindow[1];
      return {kind:"window_control", target:/youtube|reproductor|video/.test(directWindow[2])?"player":"search",
        mode:/minim/.test(verb)?"minimized":/maxim/.test(verb)?"max":/cierr/.test(verb)?"close":"normal"};
    }
    const player = s.match(/^(?:(?:abre|abri|abrir|activa|muestra)\s+(?:el\s+)?youtube\s+(?:y\s+)?)?(?:pon|pone|ponme|reproduce|reproducir|reproduci|busca|buscame|quiero escuchar|quiero ver)\s+(?:(?:la |el |un )?(?:musica|cancion|canciones|tema|temas|video|videos)\s+(?:de\s+)?)?(.+)$/);
    if (player && player[1] &&
        (/^(?:abre|abri|abrir|activa|muestra) (?:el )?youtube\b/.test(s) ||
         /^(?:pon|pone|ponme|reproduce|reproducir|reproduci|quiero escuchar|quiero ver) (?:la |el |un )?(?:musica|cancion|canciones|tema|temas|video|videos)\b/.test(s)) &&
        !/^(?:volumen|alarma|recordatorio|temporizador)\b/.test(player[1])) {
      return {kind:"youtube", query:player[1].slice(0,120), mode:mode || "normal"};
    }
    if (/^(?:abre|abri|abrir|activa|activar|inicia|iniciar|muestra|mostra)(?:\s+(?:el|la))?\s+(?:(?:modulo|panel|herramienta)\s+(?:de\s+)?)?(?:buscar|buscador|busqueda|search)(?:\s+web)?$/.test(s) ||
        /^(?:abre|abri|abrir|muestra)\s+(?:el\s+)?youtube$/.test(s)) {
      return {kind:"search", mode:mode || "normal", provider:/youtube$/.test(s)?"youtube":"web"};
    }
    return null;
  }
  const api = {parse};
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.SKYWindowIntents = api;
})(typeof window !== "undefined" ? window : null);
