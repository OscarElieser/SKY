package ni.sky.mobileagent

/**
 * Deterministic intent router for original social content.
 * No scraping, automated engagement, posting or account permissions.
 */
object SkySocialCommand {
    enum class Kind { POST, WEEKLY_PLAN }
    data class Request(val platform: String, val topic: String, val kind: Kind, val faceless: Boolean = true)

    val platforms = listOf(
        "TikTok", "Instagram", "Facebook", "YouTube", "X", "Threads",
        "Snapchat", "Pinterest", "LinkedIn"
    )

    private val platformPattern = Regex(
        """\b(tiktok|instagram|facebook|youtube|twitter|threads|snapchat|pinterest|linkedin)\b|(?<!\w)\bX\b(?!\w)""",
        RegexOption.IGNORE_CASE
    )
    private val creative = Regex(
        """\b(crea|creame|créame|creá|prepara|prepará|hace|haceme|haz|""" +
        """ideas|plan|calendario|estrategia|publicación|publicacion|""" +
        """post|reel|short|viral|contenido|seguidores|vistas|likes|crecer)\b""",
        RegexOption.IGNORE_CASE
    )
    private val planning = Regex(
        """\b(plan|calendario|estrategia|semana|semanal|7\s+d[ií]as|ideas)\b""",
        RegexOption.IGNORE_CASE
    )
    private val topicPattern = Regex("""\b(?:sobre|acerca de|del tema)\s+(.+)$""", RegexOption.IGNORE_CASE)

    fun parse(input: String): Request? {
        val raw = input.trim().replace(Regex("""(?i)^sky\s*[,.:!]+\s*"""), "")
        if (raw.length !in 7..550 || '\n' in raw) return null
        val platformMatch = platformPattern.find(raw)
        val generalSocial = Regex("""\b(mis redes|redes sociales|estudio creativo)\b""",
            RegexOption.IGNORE_CASE).containsMatchIn(raw)
        if (platformMatch == null && !generalSocial) return null
        if (!creative.containsMatchIn(raw) &&
            !Regex("""\b(estudio creativo|creador de contenido)\b""",
                RegexOption.IGNORE_CASE).containsMatchIn(raw)) return null

        val name = when (platformMatch?.value?.lowercase(java.util.Locale.ROOT)) {
            "tiktok" -> "TikTok"
            "instagram" -> "Instagram"
            "facebook" -> "Facebook"
            "youtube" -> "YouTube"
            "twitter", "x" -> "X"
            "threads" -> "Threads"
            "snapchat" -> "Snapchat"
            "pinterest" -> "Pinterest"
            "linkedin" -> "LinkedIn"
            else -> "TikTok"
        }
        val weekly = planning.containsMatchIn(raw)
        val topic = topicPattern.find(raw)?.groupValues?.get(1)
            ?.trim(' ', '.', '!', '?', '¿')
            ?.take(220)
            ?.ifBlank { null }
            ?: "marca personal, creatividad y experiencias cotidianas"
        val faceless = !Regex("""\b(salir en cámara|mostrar mi cara|mostrarme en cámara)\b""",
            RegexOption.IGNORE_CASE).containsMatchIn(raw)
        return Request(name, topic, if (weekly) Kind.WEEKLY_PLAN else Kind.POST, faceless)
    }

    fun prompt(request: Request): String {
        val audience = request.platform
        val topic = request.topic.take(220)
        val format = if (request.kind == Kind.WEEKLY_PLAN) {
            "Construí un calendario REALISTA de 7 días. Por cada día: idea, gancho de " +
                "2 segundos, visual sin rostro, subtítulos, llamado a la acción y métrica a revisar. " +
                "Añadí una pequeña rutina de evaluación semanal basada en datos que el usuario " +
                "pueda leer manualmente en sus estadísticas oficiales."
        } else {
            "Creá UNA publicación original lista para adaptar: objetivo, gancho en 2 segundos, " +
                "guion de 20–35 segundos dividido en escenas, texto sobre pantalla, descripción " +
                "copiable, 5 hashtags específicos y una pregunta auténtica que invite a comentar. " +
                "Ofrecé 2 ganchos alternativos y una sugerencia de portada."
        }
        return "Sos SKY Estudio Creativo, un asistente profesional de crecimiento orgánico " +
            "para redes sociales. Plataforma: " + audience + ". Tema: " + topic + ". " +
            "Preferencia de privacidad: " +
            (if (request.faceless) "no mostrar el rostro ni exigir que el usuario hable a cámara. " +
                "Usar tomas propias, grabación de pantalla, subtítulos, imágenes propias o " +
                "voz en off opcional. " else "permitir aparecer ante cámara solo si el usuario quiere. ") +
            format + " Todo en español natural, con contenido original para Nicaragua y " +
            "audiencia hispanohablante. Evitá afirmaciones inventadas, derechos de autor ajenos, " +
            "tendencias supuestamente verificadas sin navegación, seguidores falsos, " +
            "bots, compra de likes y promesas de viralidad. No afirmés conocer sus métricas " +
            "ni que ya publicaste o ejecutaste acciones. Texto máximo 3000 caracteres."
    }
}
