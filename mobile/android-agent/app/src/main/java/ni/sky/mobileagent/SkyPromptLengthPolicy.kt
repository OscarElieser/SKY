package ni.sky.mobileagent

/**
 * Preserve every character of the user's request. Context hints may be
 * shortened to fit the provider's documented client limit, never the request.
 * No network calls or mutable state.
 */
internal object SkyPromptLengthPolicy {
    const val NORMAL_MAX = 4000
    const val DEEP_MAX = 16000
    const val OWN_API_MAX = 32000

    // Own-hosted Ollama and SKY Automatic alone use the expanded budget.
    // Other providers keep their former limits and never inherit this setting.
    fun limit(deep: Boolean, ownApi: Boolean = false): Int =
        if (ownApi) OWN_API_MAX else if (deep) DEEP_MAX else NORMAL_MAX

    fun allowed(prompt: String, deep: Boolean, ownApi: Boolean = false): Boolean =
        prompt.isNotBlank() && prompt.length <= limit(deep, ownApi)

    fun compose(userPrompt: String, optionalContext: String, deep: Boolean,
                ownApi: Boolean = false): String? {
        if (!allowed(userPrompt, deep, ownApi)) return null
        val remaining = limit(deep, ownApi) - userPrompt.length
        return optionalContext.take(remaining) + userPrompt
    }
}
