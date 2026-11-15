package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * Solicitud de recordatorio con fecha relativa y hora precisa.
 * El resultado es SOLO un borrador de evento que Calendar debe confirmar.
 * No se afirma que una notificación ya haya quedado programada.
 */
object SkyReminderCommand {
    data class Request(val daysAhead: Int, val hour: Int, val minute: Int, val title: String)

    private fun normalize(raw: String): String = Normalizer.normalize(
        raw.lowercase(Locale.ROOT), Normalizer.Form.NFD
    ).replace(Regex("""\p{M}+"""), "")

    fun parse(raw: String): Request? {
        if (raw.length > 350 || '\n' in raw) return null
        val clean = raw.trim()
            .replace(Regex("""^(?:(?:oye|hey|hola)\s+)?sky[ ,.:!]+""",
                RegexOption.IGNORE_CASE), "")
            .trim().trimStart('¿','¡').trim()
            .trimEnd('.','!','?').trim()
        val match = Regex(
            """^(?:recu[eé]rdame|recordame|crea(?:r)?\s+(?:un\s+)?recordatorio|ponme\s+(?:un\s+)?recordatorio)\s+(hoy|ma[nñ]ana|pasado\s+ma[nñ]ana)\s+(?:a\s+las?\s+)?(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?|de\s+la\s+ma[nñ]ana|de\s+la\s+tarde|de\s+la\s+noche)?\s+(?:(?:para|que|de|sobre)\s+)?(.{3,160})$""",
            RegexOption.IGNORE_CASE
        ).matchEntire(clean) ?: return null
        val days = when (normalize(match.groupValues[1]).replace(Regex("""\s+"""), " ")) {
            "hoy" -> 0
            "manana" -> 1
            "pasado manana" -> 2
            else -> return null
        }
        val rawHour = match.groupValues[2].toIntOrNull() ?: return null
        val minute = match.groupValues[3].ifEmpty { "0" }.toIntOrNull() ?: return null
        if (minute !in 0..59 || rawHour !in 0..23) return null
        val period = normalize(match.groupValues[4]).replace(".", "").trim()
        val morning = period == "am" || period == "de la manana"
        val afternoon = period == "pm" || period == "de la tarde" || period == "de la noche"
        if ((morning || afternoon) && rawHour !in 1..12) return null
        val hour = if (morning || afternoon) (rawHour % 12) + if (afternoon) 12 else 0
            else rawHour
        val title = match.groupValues[5].trim()
        // No aceptar frases encadenadas: calendario y eventos no ejecutan herramientas.
        if (Regex("""\b(?:y luego|y despu[eé]s|borra|elimina|instala|paga)\b""",
                RegexOption.IGNORE_CASE).containsMatchIn(title)) return null
        return Request(days, hour, minute, title)
    }
}
