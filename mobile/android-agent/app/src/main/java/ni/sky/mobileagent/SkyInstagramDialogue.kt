package ni.sky.mobileagent

/**
 * A conversational answer is accepted only if a live notification offer exists
 * in MainActivity. This object never authorizes sending or deleting anything.
 */
internal object SkyInstagramDialogue {
    enum class Answer { YES, NO, NONE }

    fun answer(raw: String): Answer {
        val normalized = SkyVoicePresence.normalized(raw)
            .replace(Regex("^(?:hola )?(?:sky ia|sky|esky|escai|esquai)\\s*"), "")
            .trim()
        if (normalized.isBlank()) return Answer.NONE
        val positive = setOf("si", "si revisa", "si revisalo", "si revisalos",
            "claro", "claro revisalo", "claro revisalos", "revisalo",
            "revisalos", "revisa", "dale", "dale revisalos", "de acuerdo",
            "si por favor", "si decime", "si decime que llego", "si leelos",
            "si leelo", "si leeme", "leelos", "leelo", "leeme los mensajes")
        val negative = setOf("no", "ahora no", "no ahorita", "despues",
            "mejor despues", "no gracias", "dejalo para luego",
            "no revises nada", "todavia no", "luego")
        return when (normalized) {
            in positive -> Answer.YES
            in negative -> Answer.NO
            else -> Answer.NONE
        }
    }
}
