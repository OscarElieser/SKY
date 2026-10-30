package ni.sky.mobileagent

/**
 * Local, owner-confirmed personal identity. Never infers a real name from
 * public accounts, Android device metadata, a model or a third party.
 */
internal object SkyOwnerIdentity {
    fun isQuestion(raw: String): Boolean {
        val normalized = SkyAndroidCognition.normalize(raw)
            .replace(Regex("^(?:hola )?(?:sky ia|sky)\\s*"), "")
        return normalized in setOf(
            "quien soy", "quien soy yo", "que sabes de mi",
            "como me llamo", "cual es mi nombre", "a que me dedico",
            "que trabajo tengo", "cuales son mis proyectos",
            "recuerdas quien soy", "sabes quien soy", "que conoces de mi")
    }

    fun isExplicitPersonalFact(fact: String): Boolean {
        val normalized = SkyAndroidCognition.normalize(fact)
        return Regex("^(?:me llamo|mi nombre es|soy |trabajo |trabajo en |me dedico |mi proyecto |mis proyectos |estudio |vivo en |prefiero |me gusta )")
            .containsMatchIn(normalized)
    }

    fun summarize(localProfile: String): String {
        val details = localProfile.lines().map { it.trim().trimStart('-', '•', ' ') }
            .filter { it.isNotBlank() }.take(8)
        if (details.isEmpty()) return "Todavía no tengo guardada tu identidad en este teléfono. " +
            "Podés decirme «SKY, recuerda que me llamo ...» y «SKY, recuerda que soy ...». " +
            "Así podré conocerte con información que me autorizaste a recordar."
        return "Esto sé de vos porque lo guardaste en tu perfil privado del teléfono: " +
            details.joinToString(". ") { it.take(190).trimEnd('.', ' ') } +
            ". Si hay algo que cambió, decime qué dato debo actualizar."
    }
}
