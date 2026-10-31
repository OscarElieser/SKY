package ni.sky.mobileagent

/**
 * Gemini quota (HTTP 429) may allow a consensual text-only fallback.
 * Never silently downgrade a user-requested Gemini mode, substitute an
 * unverified response for grounded research, or bypass a provider's quota.
 */
internal object SkyProviderFallbackPolicy {
    fun canUseGroq(
        groqAuthorized: Boolean,
        explicitGemini: Boolean,
        needsVerifiedWeb: Boolean,
        promptLength: Int
    ): Boolean = groqAuthorized && !explicitGemini && !needsVerifiedWeb &&
        promptLength in 1..SkyPromptLengthPolicy.NORMAL_MAX
}
