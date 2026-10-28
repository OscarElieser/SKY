package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * Detecta únicamente órdenes explícitas para abrir/cerrar paneles del móvil.
 * Nunca interpreta un mensaje normal como permiso de ejecución de herramientas.
 */
object SkyMobileIntentRouter {
    data class Action(val kind: Kind, val module: String = "") {
        enum class Kind { OPEN_CHAT, CLOSE_PANEL, OPEN_MODULE }
    }

    private fun normalized(text: String): String = Normalizer
        .normalize(text.lowercase(Locale.ROOT), Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "")
        .replace(Regex("[^a-z0-9 ]+"), " ")
        .replace(Regex("\\s+"), " ")
        .trim()

    private val openVerbs = Regex(
        "(^| )(abre|abrir|abreme|abri|mostrame|muestra|mostrar|muestrame|activa|activar|inicia|iniciar|entra|entrar|quiero abrir|ve a)( |$)"
    )
    private val closeVerbs = Regex("(^| )(cierra|cerrar|oculta|ocultar|esconde|salir|regresa|vuelve)( |$)")

    fun route(text: String): Action? {
        val command = normalized(text).removePrefix("sky ").trim()
        if (command.length > 180 || command.isEmpty()) return null

        if (closeVerbs.containsMatchIn(command) &&
            listOf("panel", "chat", "conversacion", "inicio", "ojitos", "principal", "modulo")
                .any { it in command }) {
            return Action(Action.Kind.CLOSE_PANEL)
        }
        if (!openVerbs.containsMatchIn(command)) return null
        // "Abre una investigación sobre X" es una tarea, no abrir un panel.
        if (" sobre " in command && "panel" !in command && "modulo" !in command) return null

        if (listOf("chat", "conversacion", "platicar", "panel de conversacion")
                .any { it in command }) {
            return Action(Action.Kind.OPEN_CHAT)
        }
        val modules = linkedMapOf(
            "investigacion" to listOf("investigacion", "investigar", "investigadora", "scholar"),
            "documentos" to listOf("documento", "documentos", "word", "office"),
            "codigo" to listOf("codigo", "programacion", "programar", "desarrollo"),
            "docente" to listOf("docente", "clases", "aula", "educacion"),
            "creativo" to listOf("creativo", "creativa", "imagenes", "videos", "creative"),
            "metaverso" to listOf("metaverso", "metaverse"),
            "deportes" to listOf("deporte", "deportes", "futbol")
        )
        val target = modules.entries.firstOrNull { entry ->
            entry.value.any { word -> Regex("(^| )" + Regex.escape(word) + "( |$)").containsMatchIn(command) }
        }?.key
        return target?.let { Action(Action.Kind.OPEN_MODULE, it) }
    }
}
