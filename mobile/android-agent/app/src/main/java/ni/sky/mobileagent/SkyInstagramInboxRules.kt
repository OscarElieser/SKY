package ni.sky.mobileagent

/**
 * Presentation-only rules. No OAuth token or message body is persisted locally.
 * Profiles must be compared by Meta's exact numeric ID, not a public handle.
 */
internal object SkyInstagramInboxRules {
    fun belongsToProfile(expectedId: String, eventAccountId: String): Boolean =
        expectedId.matches(Regex("[0-9]{5,30}")) && expectedId == eventAccountId

    fun isIncoming(expectedId: String, senderId: String): Boolean =
        senderId.isNotBlank() && senderId != expectedId

    fun senderLabel(senderId: String): String {
        val digits = senderId.filter { it.isDigit() }
        return if (digits.length >= 5 && digits.length <= 30)
            "Remitente ···" + digits.takeLast(5)
        else "Remitente no identificado"
    }

    fun preview(value: String?, maxCharacters: Int = 140): String {
        val cleaned = (value ?: "").replace(Regex("[\\p{Cntrl}&&[^\\n\\t]]"), "")
            .trim().replace(Regex("\\s+"), " ")
        if (cleaned.isEmpty()) return "Mensaje sin texto o contenido multimedia"
        val max = maxCharacters.coerceIn(20, 2000)
        return if (cleaned.length > max) cleaned.take(max - 1) + "…" else cleaned
    }
}
