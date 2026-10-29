package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * Owner-requested listening policy, separate from Android microphone lifecycle.
 * This parser recognizes commands, NOT the speaker's biometric identity.
 * Sleep lock survives Activity reopening; it only permits explicit wake requests.
 */
object SkyVoicePresence {
    enum class Mode { WAKE_ONLY, ATTENTIVE, SLEEP_LOCKED }
    enum class Request { SLEEP, ATTEND, WAKE, CONFIRM, CANCEL, NONE }

    fun normalized(raw: String): String = Normalizer.normalize(
        raw.lowercase(Locale.ROOT), Normalizer.Form.NFD
    ).replace(Regex("""\p{M}+"""), "").replace(Regex("""[^a-z0-9 ]"""), " ")
        .replace(Regex("""\s+"""), " ").trim()

    fun request(raw: String): Request {
        val s = normalized(raw)
        val cmd = s.replace(Regex("""^(?:hola )?(?:sky ia|sky|esky|escai|esquai|es kai)\s*"""), "")
        if (cmd == s || cmd.isBlank()) return Request.NONE
        return when {
            cmd in setOf("duerme", "duermete", "dormi", "anda a dormir",
                "a dormir", "descansa", "buenas noches",
                "dormi hasta que yo te despierte", "duerme hasta que te despierte") ->
                Request.SLEEP
            cmd in setOf("confirmo", "confirmar", "confirma", "si confirmo") ->
                Request.CONFIRM
            cmd in setOf("cancela", "cancelar", "no confirmo", "olvidalo") ->
                Request.CANCEL
            cmd in setOf("despierta", "desperta", "levantate",
                "volver a activarte", "activarte", "volvete a activar") ->
                Request.WAKE
            cmd in setOf("estate pendiente", "estate atenta",
                "quedate pendiente", "quedate atenta",
                "escucha y ejecuta", "escucha mis orientaciones",
                "estate pendiente a mis orientaciones",
                "estate pendiente de mis orientaciones",
                "escucha y ejecuta mis orientaciones",
                "mantenete atenta a mis orientaciones") ->
                Request.ATTEND
            else -> Request.NONE
        }
    }

    /** A generic wake-word is not authorization to leave an explicit sleep lock. */
    fun permits(mode: Mode, heard: String): Boolean =
        mode != Mode.SLEEP_LOCKED || request(heard) == Request.WAKE
}
