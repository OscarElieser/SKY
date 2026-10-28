package ni.sky.mobileagent

/**
 * Limpieza exclusiva de la copia enviada al motor TextToSpeech.
 * Nunca cambia la respuesta del chat, el historial ni las órdenes Android.
 */
object SkySpokenText {
    fun prepare(raw: String): String {
        if (raw.isBlank()) return ""
        return raw
            .replace(Regex("""```[\s\S]*?```"""), " Código disponible en pantalla. ")
            .replace(Regex("""\[([^\]\n]{1,150})\]\(https?://[^)\s]+\)"""), "$1")
            .replace(Regex("""https?://\S+"""), " un enlace ")
            .replace(Regex("""(?m)^\s{0,3}#{1,6}\s+"""), "")
            .replace(Regex("""(?m)^\s*(?:[-*•]|\d+[.)])\s+"""), "")
            .replace(Regex("""\n\s*\n+"""), ". ")
            .replace("\n", ". ")
            .replace(Regex("""\*\*|__|~~|[`#*_>|~{}\[\]<>«»]"""), " ")
            .replace(Regex("""[¿¡]"""), "")
            .replace(Regex("""[\p{So}\p{Sk}]"""), " ")
            .replace(Regex("""\s+([,.!?;:])"""), "$1")
            .replace(Regex("""\s+"""), " ")
            .replace(Regex("""(?:\.\s*){2,}"""), ". ")
            .trim()
    }
}
