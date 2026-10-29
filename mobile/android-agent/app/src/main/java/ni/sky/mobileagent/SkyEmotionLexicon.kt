package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * Las emociones de SKY son expresiones visuales de un personaje, nunca
 * inferencias clínicas ni afirmaciones sobre sentimientos reales.
 *
 * Esta capa no requiere red, sensores, permisos ni modelos externos.
 */
object SkyEmotionLexicon {
    enum class Mood {
        CALM, HAPPY, CURIOUS, SURPRISED, LOVING, SLEEPY,
        SAD, CRYING, ANGRY, EXCITED, SHY
    }

    private fun normalize(source: String): String = Normalizer.normalize(
        source.lowercase(Locale.ROOT), Normalizer.Form.NFD
    ).replace(Regex("""\p{M}+"""), "")
        .replace(Regex("""\s+"""), " ")
        .trim()

    /** Una orden explícita siempre prevalece sobre una reacción espontánea. */
    fun requested(raw: String): Mood {
        val value = normalize(raw)
        return when {
            contains(value, "llora", "llorar", "llanto", "lagrima") -> Mood.CRYING
            contains(value, "triste", "pena", "melancol") -> Mood.SAD
            contains(value, "enoj", "molest", "furios", "rabia") -> Mood.ANGRY
            contains(value, "timid", "verguenza", "sonroja") -> Mood.SHY
            contains(value, "sorprend", "sorpresa", "asombr") -> Mood.SURPRISED
            contains(value, "emocion", "entusiasm", "eufor") -> Mood.EXCITED
            contains(value, "amor", "carino", "abrazo", "quiero") -> Mood.LOVING
            contains(value, "feliz", "alegr", "sonri", "risa") -> Mood.HAPPY
            contains(value, "sueno", "dormi", "descansa", "duerme") -> Mood.SLEEPY
            contains(value, "calma", "tranquil") -> Mood.CALM
            else -> Mood.CURIOUS
        }
    }

    /**
     * Solo reacciona ante vocabulario reconocible; no analiza identidades,
     * rostros de personas ni diagnostica sus emociones.
     */
    fun dialogue(raw: String): Mood? {
        val value = normalize(raw)
        if (value.isEmpty()) return null
        return when {
            contains(value, "llora", "llanto", "lagrimas") -> Mood.CRYING
            contains(value, "triste", "lo siento", "pena") -> Mood.SAD
            contains(value, "enoj", "furios", "que rabia") -> Mood.ANGRY
            contains(value, "me da verguenza", "timid") -> Mood.SHY
            contains(value, "sorpresa", "sorprend", "increible") -> Mood.SURPRISED
            contains(value, "emocionad", "entusiasm") -> Mood.EXCITED
            contains(value, "te quiero", "un abrazo", "con carino") -> Mood.LOVING
            contains(value, "jajaja", "feliz", "alegr", "que bien", "gracias", "hola") -> Mood.HAPPY
            else -> null
        }
    }

    private fun contains(value: String, vararg fragments: String): Boolean =
        fragments.any { it in value }

    fun message(mood: Mood): String = when (mood) {
        Mood.HAPPY -> "¡Qué alegría verte! 😊"
        Mood.CURIOUS -> "¡Contame más! 🤔"
        Mood.SURPRISED -> "¡Guau! ¡Qué sorpresa! ✨"
        Mood.LOVING -> "¡Un abrazo virtual! 💜"
        Mood.SLEEPY -> "Mis ojitos descansan un momento… 😴"
        Mood.CALM -> "Aquí estoy para vos. 💙"
        Mood.SAD -> "SKY pone una expresión de tristeza. 💙"
        Mood.CRYING -> "SKY muestra lagrimitas animadas. 💧"
        Mood.ANGRY -> "SKY pone carita de enojo. 😠"
        Mood.EXCITED -> "¡Qué emoción! ✨"
        Mood.SHY -> "Una sonrisa tímida. 🌸"
    }
}
