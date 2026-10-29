package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * SKY Android: razonamiento auxiliar determinista y privado.
 *
 * La red neuronal conversacional sigue siendo el proveedor que el usuario
 * autorice. Este módulo no cambia pesos del modelo, no lee archivos ajenos,
 * no concede permisos y nunca ejecuta acciones del teléfono.
 */
object SkyAndroidCognition {
    data class Route(
        val role: String,
        val intent: String,
        val verifyWithSources: Boolean,
        val actionProposedOnly: Boolean
    )

    private val fillers = setOf(
        "que", "como", "cuando", "donde", "cual", "cuales", "sobre", "para",
        "una", "uno", "unos", "unas", "los", "las", "del", "con", "por", "de",
        "el", "la", "lo", "mi", "mis", "tu", "tus", "nuestro", "nuestra",
        "recuerdas", "recuerda", "recordas", "recordamos", "hablamos",
        "conversacion", "historial", "sabes", "acerca", "busca", "dime", "decime",
        "quiero", "ver", "desde", "hace", "estoy", "has", "aprendido", "sky"
    )
    private val liveMarkers = listOf(
        "en tiempo real", "informacion actualizada", "ultima noticia",
        "ultimas noticias", "noticias de hoy", "hoy en dia", "esta semana",
        "este mes", "fuentes actuales", "verifica en internet",
        "investiga en internet", "busca en internet", "recientes",
        "precio actual", "clima", "cotizacion", "ultimo lanzamiento"
    )
    private val actionWords = setOf(
        "abre", "abri", "abrir", "reproduce", "reproducir", "envia", "enviar",
        "llama", "llamar", "publica", "publicar", "borra", "borrar",
        "apaga", "apagar", "instala", "instalar", "compra", "comprar",
        "activa", "activar", "elimina", "eliminar"
    )

    fun normalize(input: String): String = Normalizer.normalize(
        input.lowercase(Locale.ROOT), Normalizer.Form.NFD
    ).replace(Regex("""\p{M}+"""), "")
        .replace(Regex("""[^a-z0-9 ]"""), " ")
        .replace(Regex("""\s+"""), " ").trim()

    private fun tokens(input: String): Set<String> =
        normalize(input).split(' ').filter { it.length > 2 }.toSet()

    /** Orden explícita por texto o dictado; nunca extrae hechos por inferencia. */
    fun explicitFact(query: String): String? {
        val withoutWake = query.trim().replaceFirst(
            Regex("""^(?:(?:oye|hey)\s+)?sky\s*[,.:;!?¡¿-]*\s*""",
                RegexOption.IGNORE_CASE), ""
        )
        val match = Regex("""^(?:recuerda|aprende)\s+que\s+(.+)$""",
            RegexOption.IGNORE_CASE).matchEntire(withoutWake) ?: return null
        val value = match.groupValues[1].trim()
        return value.takeIf { it.length >= 5 }
    }

    fun memoryQuestion(query: String): Boolean {
        val phrase = normalize(query).removePrefix("sky ").trim()
        return phrase.startsWith("que recuerdas de mi") ||
            phrase.startsWith("que recordas de mi") ||
            phrase.startsWith("que sabes de mi") ||
            phrase.startsWith("cuales son mis recuerdos") ||
            phrase.startsWith("muestra mi memoria") ||
            phrase.startsWith("que has aprendido sobre mi") ||
            phrase.startsWith("que recuerdas sobre ") ||
            phrase.startsWith("que recordas sobre ")
    }

    fun historyQuestion(query: String): Boolean {
        val phrase = normalize(query).removePrefix("sky ").trim()
        return phrase.startsWith("que hablamos sobre ") ||
            phrase.startsWith("que hablamos de ") ||
            phrase.startsWith("busca en mi historial") ||
            phrase.startsWith("busca en el historial") ||
            phrase.startsWith("que te pregunte sobre ") ||
            phrase.startsWith("recuerda nuestra conversacion") ||
            phrase.startsWith("que conversamos sobre ")
    }

    fun searchTerms(query: String): List<String> =
        tokens(query).filterNot { it in fillers }.take(6)

    fun localMemoryAnswer(query: String, facts: List<String>): String {
        if (facts.isEmpty()) {
            return "Todavía no hay recuerdos explícitos guardados en este teléfono. " +
                "Podés decir: «recuerda que ...» para agregar uno."
        }
        val terms = searchTerms(query).toSet()
        val specific = terms.isNotEmpty()
        val selected = if (specific) {
            facts.filter { fact -> tokens(fact).intersect(terms).isNotEmpty() }.takeLast(6)
        } else facts.takeLast(6)
        if (selected.isEmpty()) {
            return "No encontré un recuerdo explícito sobre ese tema en mi perfil local. " +
                "Podés revisar Mi memoria en Ajustes."
        }
        return "Esto es lo que guardaste en mi memoria de este teléfono:\n" +
            selected.joinToString("\n") { "• " + it.removePrefix("- ").take(300) } +
            "\nPodés revisar o borrar estos datos desde Ajustes."
    }

    fun localHistoryAnswer(matches: List<String>, searched: Boolean): String {
        if (matches.isEmpty()) {
            return if (searched)
                "No encontré consultas con ese texto en el historial local. " +
                    "Podés abrir Historial para buscar por otra palabra."
            else "Decime sobre qué tema querés buscar en nuestro historial, " +
                "o abrí Historial para revisar las consultas con fecha y hora."
        }
        return "Encontré estas consultas guardadas en tu teléfono:\n" +
            matches.take(4).joinToString("\n") { "• " + it.take(220) } +
            "\nEl historial completo está disponible en Historial."
    }

    fun classify(query: String): Route {
        val clean = normalize(query)
        val words = tokens(query)
        val action = words.intersect(actionWords).isNotEmpty()
        val role = when {
            memoryQuestion(query) || historyQuestion(query) -> "memoria"
            action -> "agente_android"
            words.any { it in setOf("clase", "docencia", "estudiantes", "evaluacion", "rubrica", "meidi") } -> "docente"
            words.any { it in setOf("codigo", "python", "flutter", "kotlin", "programacion", "github", "api") } -> "programador"
            words.any { it in setOf("diseno", "imagen", "logo", "packaging", "presentacion") } -> "disenador"
            words.any { it in setOf("investiga", "investigacion", "estudio", "cientifico", "fuentes", "bibliografia") } -> "investigador"
            else -> "conversacion"
        }
        val needsLive = liveMarkers.any { it in clean }
        return Route(
            role = role,
            intent = if (action) "accion_solicitada" else "consulta",
            verifyWithSources = needsLive,
            actionProposedOnly = action
        )
    }

    /**
     * Sólo instrucciones generales, nunca datos privados ni claves.
     * El mensaje original se añade al final en MainActivity.
     */
    fun guide(query: String): String {
        val route = classify(query)
        val specific = when (route.role) {
            "docente" -> "Si es docencia, organiza objetivos, actividades y evaluación con claridad."
            "programador" -> "Si es programación, ofrece código verificable y explica las limitaciones."
            "disenador" -> "Si es diseño, explica decisiones visuales y pasos prácticos."
            "investigador" -> "Si es investigación, distingue hechos, hipótesis y fuentes."
            "agente_android" -> "No afirmes que abriste una app o ejecutaste una orden. " +
                "Los controles reales pertenecen a Android y requieren permisos."
            else -> "Responde a la consulta sin inventar recuerdos ni capacidades."
        }
        return "REGLAS DE CONVERSACIÓN SKY ANDROID (guía; no ejecutar acciones):\n" +
            "Hablá en español de Nicaragua, tratá al usuario de tú, con naturalidad y orden. " +
            "No leas la puntuación como palabras; el texto escrito debe conservarla. " +
            "No declares emociones humanas ni conciencia propia. " +
            "No inventés acciones realizadas, búsquedas, datos actuales ni referencias. " +
            "Si necesitás información reciente, usa solo fuentes verificables disponibles " +
            "y diferenciá claramente lo que no se pudo comprobar.\n" +
            specific + "\n"
    }

    fun description(): String =
        "SKY Android · núcleo cognitivo local\n\n" +
            "• Clasifica consultas para docencia, investigación, diseño y programación.\n" +
            "• Responde preguntas sobre recuerdos e historial guardados en este teléfono.\n" +
            "• Orienta a Gemini/Groq con estilo natural y exigencia de fuentes.\n" +
            "• Conserva las acciones Android existentes y sus confirmaciones.\n" +
            "• No entrena pesos neuronales ni sincroniza memorias entre equipos.\n" +
            "• Tus recuerdos no se envían a la nube sin marcar el permiso privado.\n" +
            "• Para respuestas actuales hace falta internet y un proveedor compatible."
}
