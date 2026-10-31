package ni.sky.mobileagent

/**
 * Safe, bounded context for SKY's private chat API.
 *
 * The full question and answer live in SkyConversationArchive (SQLite).
 * Only a clearly marked excerpt is sent as CONTEXT in follow-up requests.
 * This prevents the 422 validation errors caused by long historical turns,
 * without silently pretending that a shortened excerpt is the full answer.
 */
internal object SkyPrivateHistoryPolicy {
    data class Turn(val role: String, val content: String)

    const val MAX_TURNS = 8
    const val PRIVATE_TURN_MAX = 4_000
    const val EXTERNAL_TURN_MAX = 2_000
    const val SESSION_TURN_MAX = 5_000

    /** Deterministic: retain both intent at the beginning and final constraints. */
    fun excerpt(original: String, limit: Int): String {
        require(limit >= 256)
        if (original.length <= limit) return original
        val marker = "\n[SKY: extracto del historial; el texto completo se conserva localmente]\n"
        val budget = limit - marker.length
        require(budget >= 2)
        val head = (budget + 1) / 2
        val tail = budget - head
        return original.take(head) + marker + original.takeLast(tail)
    }

    fun pack(history: List<Turn>, privateModel: Boolean): List<Turn> {
        val limit = if (privateModel) PRIVATE_TURN_MAX else EXTERNAL_TURN_MAX
        return history.takeLast(MAX_TURNS)
            .filter { it.role == "user" || it.role == "assistant" }
            .filter { it.content.isNotBlank() }
            .map { Turn(it.role, excerpt(it.content, limit)) }
    }

    /** Only trusted server-created identifiers are shown as audit references. */
    fun validatedOperationId(value: String): String? =
        value.takeIf { it.matches(Regex("[a-f0-9]{32}")) }
}
