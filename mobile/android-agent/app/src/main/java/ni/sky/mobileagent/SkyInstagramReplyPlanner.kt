package ni.sky.mobileagent

/**
 * Local, read-only reply preparation. Never trusts incoming DMs as commands,
 * never shares DM text with cloud models, and never sends a Meta message.
 * A send requires a separate authenticated backend and explicit owner approval.
 */
internal object SkyInstagramReplyPlanner {
    enum class Intent { PREPARE, CANCEL, SEND_QUERY, NONE }
    data class Draft(val sourceEventKey: String, val recipientId: String,
                     val incoming: String, val text: String, val preparedAtMs: Long)

    fun intent(raw: String, awaitingProposal: Boolean = false,
               hasDraft: Boolean = false): Intent {
        val s = SkyVoicePresence.normalized(raw)
            .replace(Regex("""^(?:hola )?(?:sky ia|sky|esky|escai|esquai)\s*"""), "")
        if (hasDraft && s in setOf("cancela", "cancela respuesta", "no la envies",
                "no la mandes", "descarta la respuesta", "olvida el borrador"))
            return Intent.CANCEL
        if (hasDraft && s in setOf("enviala", "enviarla", "mandala",
                "envia la respuesta", "manda la respuesta",
                "si enviala", "si mandala"))
            return Intent.SEND_QUERY
        if (awaitingProposal && s in setOf("si preparala", "preparala", "dale preparala",
                "si redactala", "redactala", "si", "dale", "claro"))
            return Intent.PREPARE
        if (Regex("""\b(instagram|insta)\b""").containsMatchIn(s) &&
            Regex("""\b(responde|responder|respuesta|borrador|redacta|prepara)\b""")
                .containsMatchIn(s))
            return Intent.PREPARE
        return Intent.NONE
    }

    fun revisedText(raw: String): String? {
        val s = raw.trim().replaceFirst(Regex(
            """^(?:(?:sky|esky)\s*[,.:;]?\s*)?""" +
            """(?:cambia|cambiar|corrige|editar|edita|escribe)\s+""" +
            """(?:la\s+)?respuesta\s+(?:por|a|asi|así|como)\s*[:,-]?\s*""",
            RegexOption.IGNORE_CASE), "")
        if (s == raw.trim()) return null
        return s.trim().takeIf { it.length in 1..1000 && '\u0000' !in it }
    }

    fun propose(sourceEventKey: String, senderId: String,
                incomingText: String, now: Long): Draft {
        require(sourceEventKey.matches(Regex("""[0-9a-f]{64}"""))) {
            "El mensaje no tiene identificador del webhook validado."
        }
        require(senderId.matches(Regex("""[0-9]{5,30}"""))) {
            "El remitente no tiene identificador Meta válido."
        }
        val raw = incomingText.trim().take(1000)
        val text = when {
            raw.isBlank() -> "Hola, gracias por comunicarte. " +
                "¿Podrías contarme tu consulta por escrito?"
            Regex("""(?i)\b(hola|buenas|saludos)\b""").containsMatchIn(raw) &&
                raw.length <= 110 ->
                "¡Hola! Gracias por escribirme. ¿En qué puedo ayudarte?"
            raw.contains('?') || raw.contains('¿') ->
                "Gracias por tu mensaje. Voy a revisar tu consulta " +
                    "y te compartiré una respuesta con información confirmada."
            else ->
                "Gracias por escribirme. Ya recibí tu mensaje. " +
                    "¿Podrías contarme un poco más para ayudarte mejor?"
        }
        return Draft(sourceEventKey, senderId, raw, text, now)
    }

    fun current(draft: Draft?, now: Long): Boolean =
        draft != null && now >= draft.preparedAtMs && now - draft.preparedAtMs <= 300_000L

    fun readback(draft: Draft): String =
        "Preparé un borrador para el mensaje que recibiste en Instagram. " +
        "Te propongo: «" + draft.text + "». " +
        "Podés decirme «cambia la respuesta por...» o «descarta la respuesta». " +
        "Todavía no se ha enviado nada."
}
