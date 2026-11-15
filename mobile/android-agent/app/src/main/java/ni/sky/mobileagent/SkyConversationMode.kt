package ni.sky.mobileagent

/**
 * Decisión explícita del propietario sobre LA CONVERSACIÓN, no sobre todo Android.
 *
 * LOCAL_TOOLS no finge disponer de un LLM en el teléfono: permite comandos,
 * memoria, cálculos, voz y respuestas offline que ya están implementados.
 * Cualquier petición que exija inferencia generativa, noticias o investigación
 * debe informar de la limitación y NUNCA cambiar de motor a escondidas.
 *
 * No altera políticas de TLS, permisos del sistema ni otras apps instaladas.
 */
internal object SkyConversationMode {
    const val PREFS = "sky_conversation_mode"
    const val KEY_LOCAL_ONLY = "local_tools_only"

    enum class Mode { LOCAL_TOOLS, HYBRID_CONSENTED }

    fun select(localOnly: Boolean): Mode =
        if (localOnly) Mode.LOCAL_TOOLS else Mode.HYBRID_CONSENTED

    fun mayUseRemoteAi(mode: Mode): Boolean =
        mode == Mode.HYBRID_CONSENTED

    fun offlineMessage(): String =
        "SKY está en modo conversación local. Puedo usar las herramientas " +
            "del teléfono, recordar datos guardados, calcular y responder " +
            "a consultas locales conocidas sin enviar tu conversación a un servidor. " +
            "SKY admite el motor local LiteRT-LM, pero falta importar " +
            "y validar un modelo .litertlm en este teléfono. " +
            "Para esta petición necesito ese motor o que autorices un proveedor " +
            "externo en Ajustes. Conservé tu texto, sin enviarlo ni borrarlo."

    /**
     * Diagnóstico honesto: 'configurado' no significa probado ni con cuota.
     * Claude y Grok no cuentan como disponibles hasta tener adaptadores reales.
     */
    fun engineStatus(
        ownApiPaired: Boolean,
        geminiKeyReady: Boolean,
        groqKeyReady: Boolean,
        localOnDeviceLlmReady: Boolean = false
    ): String = listOf(
        "Herramientas locales Android: disponibles sin servicio de IA externo.",
        "Modelo generativo dentro del teléfono: " +
            if (localOnDeviceLlmReady) "archivo importado; ejecución sin validar."
            else "runtime integrado; falta importar un .litertlm.",
        "SKY API privada / Ollama en servidor: " +
            if (ownApiPaired) "emparejada; verificar servicio y modelo." else "sin emparejar.",
        "Gemini: " + if (geminiKeyReady) "clave configurada; cuota por verificar."
            else "sin configurar.",
        "Groq: " + if (groqKeyReady) "clave configurada; cuota por verificar."
            else "sin configurar.",
        "Claude y Grok: adaptadores Android no integrados todavía.",
        "Las consultas a servicios remotos deben utilizar conexión cifrada " +
            "y respetar credenciales, cuotas y consentimiento."
    ).joinToString("\n")
}
