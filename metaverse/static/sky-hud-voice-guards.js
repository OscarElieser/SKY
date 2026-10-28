/* Controles conservadores de conversación continua y silencio del HUD SKY.
 * No toca la API, acciones del equipo, PIN o modelos; solo clasifica texto.
 * Compatible con navegador y node --test sin dependencias.
 */
(function (root, factory) {
  const helpers = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = helpers;
  if (root) root.SKYHUDVoiceGuards = helpers;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';

  const WAKE = /^(?:(?:oye|hey|ok|okay)\s+)?(?:sky|skye|skai|esky|eskai|esquai|es\s?kai|escai|scai)(?:\s|$)/;

  function normalize(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/[¡!¿?.,:;]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function withoutWake(value) {
    return normalize(value).replace(WAKE, '').trim();
  }

  function isStopSpeaking(value) {
    // "para todo" es una parada de emergencia DISTINTA. No interceptarla.
    const clean = withoutWake(value);
    return /^(?:callate|calla|silencio|para|detente|deja de hablar|para de hablar|deja de responder|no hables|deja de hablarme)$/.test(clean);
  }

  function isDirectedFollowUp(value) {
    const clean = normalize(value);
    if (!clean || clean.length > 450) return false;
    // Preguntas y solicitudes directas, no segmentos arbitrarios del audio
    // de un video ni menciones incidentales de aplicaciones.
    return /^(?:que|como|cual|cuanto|cuando|donde|por que|para que|explica|explicame|define|ayudame|necesito|quiero|puedes|podes|podrias|abre|abri|abrir|busca|buscame|buscar|investiga|crea|crear|escribe|escribi|redacta|reproduce|pon|pone|sube|baja|pausa|detente|callate|calla|silencio|para|muestra|mostra|lee|leeme|dime|decime|recuerda|recorda|guarda|prepara|hola|buenas|sigue|continua|otra|si|no)(?:\b|$)/.test(clean);
  }

  function shouldAcceptContinuous(value, enabled) {
    const clean = normalize(value);
    return Boolean(clean && (WAKE.test(clean) || (enabled && isDirectedFollowUp(clean))));
  }

  return { normalize, withoutWake, isStopSpeaking, isDirectedFollowUp, shouldAcceptContinuous };
});
