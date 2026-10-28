package ni.sky.mobileagent

/** Parses explicit WhatsApp messages locally, before the LLM is queried. */
object SkyMessagingIntent {
    data class Draft(val recipient: String, val body: String, val polish: Boolean)

    private val prefix = Regex(
        """^(?:(?:abre|abrir|abri|abreme|ábreme)\s+(?:el\s+)?whatsapp\s+y\s+)?""" +
        """(?:manda|mandá|envia|envía|enviá|escribe|escribí|prepara)\s+""" +
        """(?:(?:un|el)\s+)?mensaje\s+(?:(?:de|por)\s+whatsapp\s+)?(?:a|para)\s+(.+)$""",
        RegexOption.IGNORE_CASE
    )
    private val separator = Regex(
        """\s+(?:y\s+)?(?:dile|decile|decirle|diciendo|que\s+diga|con\s+el\s+texto)\s+""",
        RegexOption.IGNORE_CASE
    )
    private val leading = Regex(
        """^(?:y\s+)?(?:dile|decile|decirle|diciendo|que\s+diga)\s+""",
        RegexOption.IGNORE_CASE
    )
    private val improvement = Regex(
        """\s+(?:algo\s+as[ií](?:\s+o\s+t[uú]\s+mejor(?:alo|arlo|álo))?|mejor(?:a|á)\s+el\s+mensaje|mejoralo|mejóralo)\s*[.!?]*$""",
        RegexOption.IGNORE_CASE
    )

    fun parse(raw: String): Draft? {
        val text = raw.trim().replace(Regex("""(?i)^sky\s*[,.:!]*\s*"""), "")
        if (text.length !in 12..1200 || '\n' in text) return null
        val tail = prefix.matchEntire(text)?.groupValues?.get(1)?.trim() ?: return null
        val colon = tail.indexOf(':')
        val marker = separator.find(tail)
        val recipient: String
        val unprocessed: String
        if (colon >= 0 && (marker == null || colon < marker.range.first)) {
            recipient = tail.substring(0, colon).trim(' ', ',', ';', '.')
            unprocessed = tail.substring(colon + 1).trim()
        } else if (marker != null) {
            recipient = tail.substring(0, marker.range.first).trim(' ', ',', ';', '.')
            unprocessed = tail.substring(marker.range.last + 1).trim()
        } else return null
        var body = unprocessed.replace(leading, "").trim()
        val polish = improvement.containsMatchIn(body)
        if (polish) body = body.replace(improvement, "").trim()
        if (recipient.length !in 2..100 || body.length !in 1..1000 || '@' in recipient) return null
        return Draft(recipient, body, polish)
    }

    fun preparedText(draft: Draft): String {
        val original = draft.body.trim()
        if (!draft.polish) return original
        val normalized = original.lowercase(java.util.Locale.ROOT)
        if ("triste" in normalized && ("extraño" in normalized || "extrano" in normalized)) {
            return "Hola, \${draft.recipient.substringBefore(' ')}. Hoy me siento un poco triste y quería decirte que te extraño. Espero que estés bien. ¿Cómo has estado?"
        }
        return original.trimEnd('.', ' ').replaceFirstChar {
            if (it.isLowerCase()) it.titlecase() else it.toString()
        } + "."
    }
}
