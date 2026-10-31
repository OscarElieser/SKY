package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/** Small, explicit offline replies. Never claims to perform external actions. */
object SkyLocalConversation {
    fun handles(raw: String): Boolean =
        SkyExpressionCatalog.requested(raw) != null ||
            replyTimeOrDate(raw, evaluate = false) != null

    fun reply(raw: String): String? {
        SkyExpressionCatalog.requested(raw)?.let {
            return SkyExpressionCatalog.next(it)
        }
        return replyTimeOrDate(raw, evaluate = true)
    }

    private fun replyTimeOrDate(raw: String, evaluate: Boolean): String? {
        val normalized = Normalizer.normalize(
            raw.lowercase(Locale.ROOT), Normalizer.Form.NFD
        ).replace(Regex("\\p{M}+"), "")
            .replace(Regex("[^a-z0-9 ]"), " ")
            .replace(Regex("\\s+"), " ").trim()
        val clean = normalized.replace(Regex("^sky\\s+"), "")
            .replace(Regex("\\s+sky$"), "").trim()
        return when (clean) {
            "que hora es", "que hora es ahora", "dime la hora", "decime la hora",
            "hora actual", "hora de hoy", "me das la hora" -> {
                if (!evaluate) "hora" else {
                    val now = java.time.ZonedDateTime.now()
                    val time = now.format(java.time.format.DateTimeFormatter.ofPattern("HH:mm"))
                    "Son las $time, según la hora configurada en tu teléfono."
                }
            }
            "que dia es hoy", "que fecha es hoy", "dime la fecha", "decime la fecha",
            "fecha actual", "fecha de hoy" -> {
                if (!evaluate) "fecha" else {
                    val now = java.time.ZonedDateTime.now()
                    val date = now.format(java.time.format.DateTimeFormatter
                        .ofPattern("EEEE d 'de' MMMM 'de' yyyy", Locale("es", "NI")))
                    "Hoy es $date, según la fecha de tu teléfono."
                }
            }
             "estas ahi", "sigues ahi", "me escuchas" ->
                "¡Aquí estoy! Te escucho. ¿Qué necesitas?"
            else -> null
        }
    }
}
