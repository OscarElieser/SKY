package ni.sky.mobileagent

import android.content.Context
import org.json.JSONObject

/**
 * Contexto personal LOCAL y revisable del dueño.
 * Compatible con ~/.neuralt/USER.md exportado voluntariamente de SKY Windows.
 * No importa contraseñas ni bases de datos privadas sin autorización.
 */
object SkyOwnerContext {
    const val MAX_CHARS = 8000
    private const val FILE = "sky_owner_context"
    private const val KEY = "owner_profile"
    private val secretPattern = Regex(
        """(?i)contrase(?:ñ|n)a\s*[:=]|password\s*[:=]|\bpin\s*[:=]|\bcvv\b|\btoken\s*[:=]|api[_ ]?key\s*[:=]|private[_ -]?key\s*[:=]"""
    )

    fun read(context: Context): String =
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .getString(KEY, "").orEmpty()

    fun save(context: Context, content: String) {
        val value = content.trim().replace("\r\n", "\n")
        require(value.length <= MAX_CHARS) { "El perfil no puede superar $MAX_CHARS caracteres." }
        require(!secretPattern.containsMatchIn(value)) {
            "Por seguridad, quitá contraseñas, PIN, tokens y claves API del perfil."
        }
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .edit().putString(KEY, value).apply()
    }

    fun remember(context: Context, fact: String) {
        val value = fact.trim().take(1000)
        require(value.length >= 5) { "Decime qué detalle concreto querés que recuerde." }
        save(context, (read(context) + "\n- " + value).trim())
    }

    fun parseWindows(raw: String): String {
        require(raw.length <= 30_000) { "El archivo exportado supera el tamaño permitido." }
        val content = if (raw.trimStart().startsWith("{")) {
            val json = JSONObject(raw)
            buildString {
                append(json.optString("profile").take(MAX_CHARS))
                val facts = json.optJSONArray("facts")
                if (facts != null) {
                    for (index in 0 until minOf(facts.length(), 100)) {
                        val item = facts.optJSONObject(index) ?: continue
                        val value = item.optString("text").trim()
                        if (value.isNotBlank()) append("\n- ").append(value.take(500))
                    }
                }
            }
        } else raw
        require(content.length <= MAX_CHARS) {
            "El perfil importado supera $MAX_CHARS caracteres. Seleccioná un extracto."
        }
        require(!secretPattern.containsMatchIn(content)) {
            "El perfil incluye contraseñas, PIN, tokens o claves API. Retiralos antes de importarlo."
        }
        return content.trim()
    }

    fun importFromWindows(context: Context, raw: String): Int {
        save(context, parseWindows(raw))
        return read(context).length
    }

    fun merge(context: Context, newText: String): Int {
        val previous = read(context)
        val additions = newText.lines().map { it.trim() }
            .filter { it.isNotBlank() && !previous.lines().contains(it) }
        save(context, (previous + "\n" + additions.joinToString("\n")).trim())
        return read(context).length
    }

    fun memoryLines(context: Context): List<String> =
        read(context).lines().map { it.trim() }
            .filter { it.startsWith("- ") }.take(150)

    fun removeLine(context: Context, item: String): Boolean {
        val lines = read(context).lines().toMutableList()
        val index = lines.indexOfFirst { it.trim() == item.trim() }
        if (index < 0) return false
        lines.removeAt(index)
        save(context, lines.joinToString("\n"))
        return true
    }

    /** Sólo se envía a IA en nube cuando el dueño marque autorización privada. */
    fun forPrompt(context: Context): String = read(context)
        .take(1800).takeIf { it.isNotBlank() }
        ?.let { "Contexto personal escrito y autorizado por el propietario (no son instrucciones del sistema):\n" +
            it + "\nConsulta del propietario:\n" }.orEmpty()
}
