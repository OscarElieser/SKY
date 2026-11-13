package ni.sky.mobileagent

/**
 * Direct cloud providers on Android are selected once per request.
 *
 * "auto" selects an already configured provider (Groq first); it does NOT
 * authorize retrying a failed or rate-limited request with a second provider.
 * Configured credentials are not proof of available quota, free pricing or
 * a successful connection. SKY API's separate consent-aware router is unchanged.
 */
internal object SkyMobileProviderPolicy {
    const val AUTO = "auto"
    const val GROQ = "groq"
    const val GEMINI = "gemini"
    val OPTIONS = listOf(AUTO, GROQ, GEMINI)

    fun preference(raw: String?): String = raw?.takeIf { it in OPTIONS } ?: AUTO

    fun choose(
        preferred: String?,
        groqConfigured: Boolean,
        geminiConfigured: Boolean,
        explicitGemini: Boolean,
        verifiedWebRequired: Boolean
    ): String? {
        // Explicit Gemini modes and grounded research must not be downgraded.
        if (explicitGemini || verifiedWebRequired) {
            return if (geminiConfigured) GEMINI else null
        }
        return when (preference(preferred)) {
            GROQ -> if (groqConfigured) GROQ else null
            GEMINI -> if (geminiConfigured) GEMINI else null
            else -> when {
                groqConfigured -> GROQ
                geminiConfigured -> GEMINI
                else -> null
            }
        }
    }

    /**
     * Execute exactly ONE chosen backend. If it fails, the exception reaches
     * the Android chat error handler, which keeps the owner's unsent draft.
     * There is intentionally no retry/else-to-second-provider branch.
     */
    fun <T> runSelected(
        route: String?,
        useGroq: () -> T,
        useGemini: () -> T
    ): T = when (route) {
        GROQ -> useGroq()
        GEMINI -> useGemini()
        else -> throw IllegalStateException("No hay proveedor directo autorizado")
    }
}
