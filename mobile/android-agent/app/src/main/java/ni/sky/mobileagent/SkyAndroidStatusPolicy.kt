package ni.sky.mobileagent

/**
 * Human-readable Android-only status. Configuration is not proof of a network
 * connection, local generative inference, audible TTS, or an active microphone.
 * Pure functions allow regression checks without device permissions.
 */
internal object SkyAndroidStatusPolicy {
    fun engineStatus(privateApiSelected: Boolean, privateChatConfigured: Boolean,
                     externalModelConfigured: Boolean): String = when {
        privateApiSelected && privateChatConfigured ->
            "API privada configurada · conexión sin verificar"
        privateApiSelected ->
            "API privada pendiente · autorización necesaria"
        externalModelConfigured ->
            "IA externa configurada · conexión sin verificar"
        else -> "Funciones locales disponibles · IA generativa sin configurar"
    }

    fun voiceCaption(serviceActive: Boolean, requestedPresence: String?): String = when {
        !serviceActive -> "SKY LISTA · TOCÁ LOS OJOS O ACTIVÁ MANOS LIBRES"
        requestedPresence == "SLEEP_LOCKED" -> "SKY DORMIDA · DECÍ SKY DESPIERTA"
        requestedPresence == "ATTENTIVE" -> "SKY ATENTA · SERVICIO ACTIVO"
        else -> "SKY EN ESPERA · DECÍ SKY"
    }

    /**
     * startListening() returning is not proof: only RecognitionListener
     * onReadyForSpeech confirms that the engine entered its ready callback.
     * Even this does not prove a person's voice was successfully recognized.
     */
    fun recognizerPrepared(active: Boolean, startRequested: Boolean,
                           readyCallback: Boolean, speechSuspended: Boolean): Boolean =
        active && startRequested && readyCallback && !speechSuspended
}
