package ni.sky.mobileagent

import java.util.Locale

/**
 * Previsualización sin efectos laterales. No envía contenido ni ejecuta archivos.
 * La aplicación móvil no dispone de un token de propietario para safe-files/commit.
 */
object SkySafeFileConversation {
    data class Proposal(val operation: String, val filename: String, val detail: String)

    private val filename = "[A-Za-z0-9][A-Za-z0-9_.-]{0,90}\\.(?:txt|md|csv|json|py|html|docx|xlsx|pptx|pdf)"
    private val create = Regex("^(?:crea|crear|genera|generar|prepara|preparar|prepares)\\s+(?:un\\s+|una\\s+)?(?:archivo|documento|informe)\\s+($filename)\\s+con\\s+contenido\\s*:\\s*([\\s\\S]+)$", RegexOption.IGNORE_CASE)
    private val append = Regex("^(?:agrega|agregar|añade|anade|incorpora|incorporar)\\s+(?:texto\\s+)?(?:al\\s+|a\\s+)?(?:archivo\\s+)?($filename)\\s*:\\s*([\\s\\S]+)$", RegexOption.IGNORE_CASE)
    private val replace = Regex("^(?:reemplaza|reemplazar|actualiza|actualizar|actualices)\\s+(?:el\\s+)?(?:contenido\\s+(?:de|del)\\s+)?(?:archivo\\s+)?($filename)\\s+(?:por|con)\\s*:\\s*([\\s\\S]+)$", RegexOption.IGNORE_CASE)
    private val rename = Regex("^(?:renombra|renombrar)\\s+(?:el\\s+)?(?:archivo\\s+)?($filename)\\s+(?:a|por)\\s+($filename)$", RegexOption.IGNORE_CASE)
    private val trash = Regex("^(?:mueve|mover|envia|envía|enviar)\\s+(?:el\\s+)?(?:archivo\\s+)?($filename)\\s+a\\s+(?:la\\s+)?papelera$", RegexOption.IGNORE_CASE)
    private val prefix = Regex("^(?:(?:oye|hey|ok)\\s+)?sky[\\s,.:;!¡-]*", RegexOption.IGNORE_CASE)
    private val polite = Regex("^(?:(?:por favor|podrias|podrías|puedes|podes|necesito que|quiero que)\\s+)+", RegexOption.IGNORE_CASE)

    fun prepare(utterance: String): Proposal? {
        if (utterance.length !in 3..4000) return null
        val clean = utterance.trim().replaceFirst(prefix, "").replaceFirst(polite, "").trim()
        for ((operation, regex) in listOf("crear" to create, "agregar" to append, "reemplazar" to replace)) {
            val match = regex.matchEntire(clean) ?: continue
            val content = match.groupValues[2].trim()
            if (content.isEmpty() || content.toByteArray(Charsets.UTF_8).size > 3000) return null
            val file = match.groupValues[1]
            if (file.lowercase(Locale.ROOT).substringBefore(".") in setOf("con", "nul", "prn", "aux")) return null
            return Proposal(operation, file, content)
        }
        rename.matchEntire(clean)?.let { return Proposal("renombrar", it.groupValues[1], "Nuevo nombre: " + it.groupValues[2]) }
        trash.matchEntire(clean)?.let { return Proposal("papelera", it.groupValues[1], "Mover a papelera; no borrar definitivamente") }
        return null
    }
}
