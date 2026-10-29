package ni.sky.mobileagent

/** Selección explícita por consulta: conserva el modelo económico predeterminado. */
internal object SkyGeminiModes {
    const val ECONOMY_MODEL = "gemini-3.5-flash-lite"
    const val FLASH_MODEL = "gemini-3.8-flash"
    const val DEEP_MODEL = "gemini-3.1-pro-preview"

    enum class Tier { ECONOMY, FLASH, DEEP }

    data class Selection(val tier: Tier, val model: String, val prompt: String,
                         val explicit: Boolean = false) {
        val historyTurns: Int get() = when (tier) {
            Tier.ECONOMY -> 8
            Tier.FLASH -> 14
            Tier.DEEP -> 30
        }
        val historyCharsPerTurn: Int get() = when (tier) {
            Tier.ECONOMY -> 2000
            Tier.FLASH -> 3000
            Tier.DEEP -> 5000
        }
        val maxResponseTokens: Int get() = when (tier) {
            Tier.ECONOMY -> 1000
            Tier.FLASH -> 2400
            Tier.DEEP -> 5200
        }
        val answerChars: Int get() = when (tier) {
            Tier.ECONOMY -> 5000
            Tier.FLASH -> 9000
            Tier.DEEP -> 16000
        }
    }

    private val deep = Regex(
        """^(?:modo\s+profundo|razonamiento\s+profundo)\s*[:：-]\s*(.+)$""",
        setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL)
    )
    private val flash = Regex(
        """^(?:modo\s+equilibrado|modo\s+flash)\s*[:：-]\s*(.+)$""",
        setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL)
    )
    private val economy = Regex(
        """^(?:modo\s+economico|modo\s+económico)\s*[:：-]\s*(.+)$""",
        setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL)
    )
    private val wake = Regex("""^sky\s*[,.:!¿?¡-]+\s*""", RegexOption.IGNORE_CASE)

    fun select(message: String): Selection {
        val original = message.trim()
        val withoutWake = original.replaceFirst(wake, "").trim()
        val matched = listOf(
            Triple(deep, Tier.DEEP, DEEP_MODEL),
            Triple(flash, Tier.FLASH, FLASH_MODEL),
            Triple(economy, Tier.ECONOMY, ECONOMY_MODEL)
        ).firstNotNullOfOrNull { (regex, tier, model) ->
            regex.matchEntire(withoutWake)?.groupValues?.get(1)?.trim()
                ?.takeIf { it.isNotEmpty() }?.let { Selection(tier, model, it, explicit = true) }
        }
        return matched ?: Selection(Tier.ECONOMY, ECONOMY_MODEL, original)
    }

    /** Ningún texto de usuario puede elegir una URL o identificador arbitrario. */
    fun endpointFor(model: String): String {
        require(model in setOf(ECONOMY_MODEL, FLASH_MODEL, DEEP_MODEL)) {
            "Modelo Gemini no autorizado por SKY."
        }
        return "https://generativelanguage.googleapis.com/v1beta/models/$model:generateContent"
    }
}
