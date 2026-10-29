package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/** Explicit requests to animate SKY's fictional facial expressions, offline. */
object SkyExpressionCommand {
    fun parse(raw: String): String? {
        val text = Normalizer.normalize(raw.lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("""\p{M}+"""), "")
            .replace(Regex("""[^a-z0-9 ]"""), " ")
            .replace(Regex("""\s+"""), " ").trim()
            .replace(Regex("""^sky\s+"""), "")
        if (!Regex("""^(?:ponte|pon|muestra|haz|hace|actua|expresa|quiero que|puedes|podes|sonrie|llora|sonri|llor)\b""")
                .containsMatchIn(text)) return null
        return when {
            Regex("""\b(?:llora|llorar|llorando|llanto|lagrimas)\b""").containsMatchIn(text) -> "llora"
            Regex("""\b(?:triste|tristeza|pena)\b""").containsMatchIn(text) -> "triste"
            Regex("""\b(?:enojada|enojado|enojo|furiosa)\b""").containsMatchIn(text) -> "enojada"
            Regex("""\b(?:sonri|sonrie|sonreir|feliz|alegre|alegria)\b""").containsMatchIn(text) -> "feliz"
            Regex("""\b(?:emocionada|emoción|entusiasmada)\b""").containsMatchIn(text) -> "emocionada"
            Regex("""\b(?:timida|verguenza)\b""").containsMatchIn(text) -> "timida"
            Regex("""\b(?:sorpresa|sorprendida)\b""").containsMatchIn(text) -> "sorpresa"
            Regex("""\b(?:dormida|dormir|sueno)\b""").containsMatchIn(text) -> "sueno"
            else -> null
        }
    }
}
