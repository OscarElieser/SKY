/* Prepara únicamente el texto hablado; nunca modifica el chat ni el historial.
   UMD: se puede verificar sin navegador con node --test. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SKYSpokenText = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  function prepare(input) {
    return String(input || '')
      .replace(/```[\s\S]*?```/g, ' Código disponible en pantalla. ')
      .replace(/\[([^\]\n]{1,150})\]\(https?:\/\/[^)\s]+\)/g, '$1')
      .replace(/https?:\/\/\S+/g, ' un enlace ')
      .replace(/^\s{0,3}#{1,6}\s+/gm, '')
      .replace(/^\s*(?:[-*•]|\d+[.)])\s+/gm, '')
      .replace(/\n\s*\n+/g, '. ')
      .replace(/\n/g, '. ')
      .replace(/\*\*|__|~~|[`#*_>|~{}\[\]<>«»]/g, ' ')
      .replace(/[¿¡]/g, '')
      .replace(/[\p{So}\p{Sk}]/gu, ' ')
      .replace(/\s+([,.!?;:])/g, '$1')
      .replace(/\s+/g, ' ')
      .replace(/(?:\.\s*){2,}/g, '. ')
      .trim();
  }
  return { prepare };
});
