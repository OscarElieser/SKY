package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/** Buscador local de nombres de apps, sin red, sin modelos y sin listas fijas. */
object SkyAppNameMatcher {
    data class Entry(val label: String, val packageName: String)
    fun norm(value: String): String = Normalizer
        .normalize(value.lowercase(Locale.ROOT), Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "")
        .replace(Regex("[^a-z0-9]+"), " ")
        .trim().replace(Regex("\\s+"), " ")

    private val synonyms = mapOf(
        "twitter" to "x",
        "geminis" to "gemini",
        "microsoft word" to "word",
        "microsoft excel" to "excel",
        "microsoft powerpoint" to "powerpoint",
        "microsoft copilot" to "copilot",
        "chat gpt" to "chatgpt"
    )

    /** Exactas primero. Si más de una coincide, corresponde elegir, no adivinar. */
    fun matches(request: String, choices: List<Entry>): List<Entry> {
        val query = synonyms[norm(request)] ?: norm(request)
        if (query.isBlank() || query.length > 100) return emptyList()
        val exact = choices.filter {
            val name = norm(it.label)
            name == query || (query == "x" && name == "twitter")
        }
        if (exact.isNotEmpty()) return exact.sortedBy { it.label }
        // Se aceptan nombres comerciales prefijados: "Microsoft Word", etc.
        val words = choices.filter { entry ->
            val label = norm(entry.label)
            label.split(" ").contains(query) ||
                label.startsWith("$query ") ||
                label.endsWith(" $query") ||
                label.contains(" $query ")
        }
        return words.sortedBy { it.label }
    }
}
