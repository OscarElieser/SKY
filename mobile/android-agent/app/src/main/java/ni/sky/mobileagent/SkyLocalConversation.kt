package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/** Small, explicit offline replies. Never claims to perform external actions. */
object SkyLocalConversation {
    fun reply(raw: String): String? {
        val normalized = Normalizer.normalize(
            raw.lowercase(Locale.ROOT), Normalizer.Form.NFD
        ).replace(Regex("\\p{M}+"), "")
            .replace(Regex("[^a-z0-9 ]"), " ")
            .replace(Regex("\\s+"), " ").trim()
        val clean = normalized.replace(Regex("^sky\\s+"), "")
            .replace(Regex("\\s+sky$"), "").trim()
        return when (clean) {
            "hola", "holi", "buenas", "que onda", "que ondas", "hey",
            "buenos dias", "buenas tardes", "buenas noches" ->
                "¡Qué onda! Aquí estoy, lista para ayudarte. ¿Qué hacemos?"
            "gracias", "muchas gracias" ->
                "¡Con mucho gusto! ¿En qué más te ayudo?"
            "estas ahi", "sigues ahi", "me escuchas" ->
                "¡Aquí estoy! Te escucho. ¿Qué necesitas?"
            else -> null
        }
    }
}
