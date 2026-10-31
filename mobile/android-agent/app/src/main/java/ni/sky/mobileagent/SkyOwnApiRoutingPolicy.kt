package ni.sky.mobileagent

/**
 * Own-hosted, authenticated SKY API (text-only) is an explicit preference.
 * It never contacts local Android loopback, opens a LAN port, or sends a
 * prompt to a third-party provider without that provider's separate consent.
 *
 * The existing SKY Home API accepts at most 4,000 characters per turn and
 * can select Ollama on the server only when it has the chosen model loaded.
 */
internal object SkyOwnApiRoutingPolicy {
    const val SERVER_PROMPT_LIMIT = 4_000

    fun usePrivateApi(
        optedIn: Boolean,
        pairedChatToken: Boolean,
        explicitGeminiMode: Boolean,
        verifiedWebRequired: Boolean,
        promptChars: Int
    ): Boolean = optedIn && pairedChatToken &&
        !explicitGeminiMode && !verifiedWebRequired &&
        promptChars in 1..SERVER_PROMPT_LIMIT

    /** Local-first is default. Cloud adapters are selected by owner only. */
    val SERVER_PROVIDERS = listOf("sky_auto", "ollama", "gemini",
        "openrouter", "mistral", "groq", "cloudflare")

    fun chosenProvider(raw: String?): String =
        raw?.takeIf { it in SERVER_PROVIDERS } ?: "sky_auto"

    fun useAutomaticViaSkyApi(
        optedIn: Boolean,
        pairedChatToken: Boolean,
        explicitGeminiMode: Boolean,
        verifiedWebRequired: Boolean,
        promptChars: Int
    ): Boolean = usePrivateApi(optedIn, pairedChatToken,
        explicitGeminiMode, verifiedWebRequired, promptChars)

    /** Consent controls transfer; router choice remains automatic. */
    fun authorizedAutomaticCloud(
        perTurnCloud: Boolean,
        perTurnPrivate: Boolean,
        standingConsent: Boolean
    ): Boolean = standingConsent || (perTurnCloud && perTurnPrivate)

    fun useExternalViaSkyApi(
        optedIn: Boolean,
        pairedChatToken: Boolean,
        selectedProvider: String,
        explicitGeminiMode: Boolean,
        verifiedWebRequired: Boolean,
        cloudConsent: Boolean,
        privateDataConsent: Boolean,
        promptChars: Int
    ): Boolean = optedIn && pairedChatToken &&
        selectedProvider in SERVER_PROVIDERS && selectedProvider != "ollama" &&
        cloudConsent && privateDataConsent &&
        !explicitGeminiMode && !verifiedWebRequired &&
        promptChars in 1..SERVER_PROMPT_LIMIT

    fun canPromptForSetup(optedIn: Boolean, pairedChatToken: Boolean): Boolean =
        optedIn && !pairedChatToken
}
