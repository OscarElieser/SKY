package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/** Pure, testable wake/sleep routing; never dispatch unrelated ambient speech. */
object SkyWakePhrase {
    enum class Kind { IGNORE, WAKE, COMMAND, SLEEP }
    data class Decision(val kind: Kind, val command: String = "")
    private val wakeNames = listOf("sky ia", "es kai", "esquai", "esquay", "escai", "esky", "sky")
    private val sleepPhrases = setOf("dormi", "duermete", "anda a dormir", "buenas noches", "descansa", "a dormir")
    private val wakeOnly = setOf("", "desperta", "despierta", "estas ahi", "hola", "escuchame")

    private fun normalized(text: String): String =
        Normalizer.normalize(text.lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "")
            .replace(Regex("[^a-z0-9 ]"), " ")
            .replace(Regex("\\s+"), " ").trim()

    fun decide(heard: String, awake: Boolean): Decision {
        val text = normalized(heard)
        if (text.isBlank()) return Decision(Kind.IGNORE)
        val withoutWake = wakeNames.firstNotNullOfOrNull { wake ->
            when {
                text == wake -> ""
                text.startsWith(wake + " ") -> text.removePrefix(wake).trim()
                // A sentence merely ending in "sky" is ambient speech,
                // never permission to execute. Suffix is wake-only.
                text.endsWith(" " + wake) &&
                    text.removeSuffix(wake).trim() in wakeOnly ->
                    text.removeSuffix(wake).trim()
                else -> null
            }
        }
        val stripped = withoutWake ?: text
        if ((awake || withoutWake != null) && stripped in sleepPhrases) {
            return Decision(Kind.SLEEP)
        }
        if (withoutWake != null) {
            return if (stripped in wakeOnly) Decision(Kind.WAKE)
            else Decision(Kind.COMMAND, heard.trim()
                .replace(Regex("(?i)^\\s*(sky ia|sky|esky|esquai|esquay|escai|es kai)[,.:! ?]*"), "")
                .trim().ifBlank { stripped })
        }
        return if (awake) Decision(Kind.COMMAND, heard.trim()) else Decision(Kind.IGNORE)
    }
}
