package ni.sky.mobileagent

/**
 * Personalidad conversacional pequeña, local y original.
 * No finge conciencia, amistad humana, ni activa el micrófono a escondidas.
 */
class SkyCompanionBrain {
    enum class Mode { OFF, GENERAL, WALKING, BUS }
    data class Response(val spoken: String, val whistle: Boolean = false)
    var mode: Mode = Mode.OFF
        private set

    private var jokeIndex = 0
    private var checkIndex = 0
    private val jokes = listOf(
        "¿Por qué la computadora fue al médico? ¡Porque tenía un virus y no era de los que se curan con sopa!",
        "¿Qué le dijo un cero a un ocho? ¡Qué bonito cinturón!",
        "¿Por qué el lápiz estaba feliz? ¡Porque por fin encontró su punto!",
        "¿Qué hace una nube con sueño? ¡Se echa una siestalluvia!",
        "¿Por qué la calculadora estaba tranquila? Porque tenía todos sus problemas resueltos.",
        "¿Qué dijo el teléfono cuando salió a caminar? Hoy sí voy a dar muchos pasos… sin mover las piernas."
    )

    fun answer(raw: String): Response? {
        val q = SkyAppNameMatcher.norm(raw).removePrefix("sky ").trim()
        if (q.isEmpty() || q.length > 160) return null
        if (Regex("^(?:termina|detene|detener|para|desactiva|apaga|cierra) (?:el )?(?:modo )?(?:acompanante|companera|compania|paseo)$")
                .matches(q)) {
            mode = Mode.OFF
            return Response("Modo acompañante desactivado. Aquí voy a estar cuando me llamés.")
        }
        if (q in listOf("voy en bus", "estoy en el bus", "estoy viajando en bus",
                "acompaname en el bus", "acompaniame en el bus")) {
            mode = Mode.BUS
            return Response("¡Vamos de paseo! Podemos conversar, jugar a las adivinanzas o contar chistes. ¿Qué preferís?")
        }
        if (q in listOf("voy caminando", "estoy caminando", "salgo a caminar",
                "acompaname caminando", "acompaniame caminando")) {
            mode = Mode.WALKING
            return Response("¡Qué bien! Te acompaño con la voz. Prestá atención al camino y no necesitás mirar la pantalla.")
        }
        if (q in listOf("acompaname", "acompaniame", "activa modo acompanante",
                "activa el modo acompanante", "quiero que me acompanes",
                "quiero conversar contigo")) {
            mode = Mode.GENERAL
            return Response("¡Aquí estoy! ¿Querés que te cuente un chiste o que conversemos de algo interesante?")
        }
        if (q in listOf("contame un chiste", "cuentame un chiste", "cuenta un chiste",
                "dime un chiste", "conta un chiste", "otro chiste",
                "hazme reir", "haceme reir")) {
            val next = jokes[jokeIndex++ % jokes.size]
            return Response(next)
        }
        if (q in listOf("silba", "silbame", "silba algo", "silba una melodia",
                "hace un silbido", "haz un silbido", "silbido")) {
            return Response("¡Escuchá este silbidito original!", whistle = true)
        }
        if (q in listOf("sorprendeme", "dime algo divertido", "decime algo divertido")) {
            val next = jokes[jokeIndex++ % jokes.size]
            return Response("¡Una sonrisa viene en camino! " + next)
        }
        return null
    }

    /** Sólo se propone en primer plano, si el usuario activó este modo. */
    fun nextCheckIn(): String? {
        if (mode == Mode.OFF) return null
        val choices = when (mode) {
            Mode.BUS -> listOf(
                "¿Cómo va el viaje? Si querés, te cuento algo divertido.",
                "¿Vamos con una adivinanza, un chiste o una conversación?"
            )
            Mode.WALKING -> listOf(
                "Seguí atento al camino. ¿Te gustaría escuchar un chiste?",
                "Aquí sigo acompañándote. ¿De qué te gustaría conversar?"
            )
            else -> listOf(
                "¿Qué te gustaría que hagamos ahora?",
                "¿Querés un chiste, una historia o hablar de tu día?"
            )
        }
        return choices[checkIndex++ % choices.size]
    }
}
