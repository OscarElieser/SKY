package ni.sky.mobileagent

/**
 * Preserve every character of the user's request. Context hints may be
 * shortened to fit the provider's documented client limit, never the request.
 * No network calls or mutable state.
 */
internal object SkyPromptLengthPolicy {
    const val NORMAL_MAX = 4000
    const val DEEP_MAX = 16000

    fun limit(deep: Boolean): Int = if (deep) DEEP_MAX else NORMAL_MAX

    fun allowed(prompt: String, deep: Boolean): Boolean =
        prompt.isNotBlank() && prompt.length <= limit(deep)

    fun compose(userPrompt: String, optionalContext: String, deep: Boolean): String? {
        if (!allowed(userPrompt, deep)) return null
        val remaining = limit(deep) - userPrompt.length
        return optionalContext.take(remaining) + userPrompt
    }
}
