package ni.sky.mobileagent

import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL

/**
 * GroqCloud Free-tier integration for private, user-provided keys.
 * No credentials are bundled with the APK or shared with SKY Windows.
 * This provider does NOT verify facts in real time or control Android apps.
 */
object SkyGroqCloud {
    const val MODEL = "llama-3.1-8b-instant"
    private const val ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    fun keyProblem(raw: String): String? {
        val trimmed = raw.trim()
        if (trimmed.startsWith("Bearer ", true) ||
            trimmed.startsWith("GROQ_API_KEY=", true) ||
            trimmed.startsWith("Authorization:", true)) {
            return "Pegá solo la clave de Groq, sin prefijos."
        }
        val key = SkyPhoneCloud.normalizePersonalKey(trimmed)
        if (key.isEmpty()) return "Copiá primero tu clave desde GroqCloud."
        if (key.length !in 24..512 || key.any { it.code !in 33..126 }) {
            return "La clave Groq está incompleta o tiene caracteres no válidos."
        }
        return null
    }

    fun validKey(raw: String) = keyProblem(raw) == null

    fun payload(message: String, history: JSONArray): JSONObject {
        require(message.isNotBlank() && message.length <= 4000) {
            "Escribí una consulta de hasta 4000 caracteres."
        }
        val messages = JSONArray().put(JSONObject()
            .put("role", "system")
            .put("content",
                "Eres SKY IA, asistente personal nicaragüense. Trata de tú, " +
                "con tono cercano, claro, natural y conciso. No pronuncies signos. " +
                "No inventes acciones sobre el teléfono, búsquedas ni fuentes. " +
                "La app SKY posee acciones Android locales, pero tú solo respondes texto. " +
                "No tienes búsqueda web ni acceso a datos actuales verificados. " +
                "Nunca asegures conocer resultados, clima, precios o noticias de hoy " +
                "sin fuentes consultadas. Si no sabes algo, dilo."))
        for (index in (history.length() - 6).coerceAtLeast(0) until history.length()) {
            val turn = history.optJSONObject(index) ?: continue
            val role = when (turn.optString("role")) {
                "user" -> "user"
                "assistant" -> "assistant"
                else -> continue
            }
            val text = turn.optString("content").trim().take(1600)
            if (text.isNotEmpty()) {
                messages.put(JSONObject().put("role", role).put("content", text))
            }
        }
        messages.put(JSONObject().put("role", "user").put("content", message))
        return JSONObject()
            .put("model", MODEL)
            .put("messages", messages)
            .put("temperature", 0.5)
            .put("max_completion_tokens", SkyPhoneCloud.responseTokenLimit(message).coerceAtMost(800))
    }

    fun reply(key: String, message: String, history: JSONArray): String {
        require(validKey(key)) { "Configurá tu clave gratuita de Groq en Ajustes." }
        val data = payload(message, history).toString().toByteArray(Charsets.UTF_8)
        require(data.size < 100_000) { "El historial es demasiado largo." }
        val connection = URL(ENDPOINT).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 9000
            connection.readTimeout = 30000
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Authorization", "Bearer $key")
            connection.doOutput = true
            connection.outputStream.use { it.write(data) }
            val status = connection.responseCode
            if (status !in 200..299) {
                // Do not log raw provider responses because they could include private data.
                val reason = when (status) {
                    400 -> "Groq rechazó la solicitud."
                    401, 403 -> "Groq no autorizó la clave. Revisala en Ajustes."
                    404 -> "El modelo de Groq no está disponible en esta cuenta."
                    429 -> "Límite gratuito de Groq alcanzado."
                    in 500..599 -> "Groq está temporalmente fuera de servicio."
                    else -> "Groq no respondió correctamente (HTTP $status)."
                }
                throw IllegalStateException(reason)
            }
            val buffer = ByteArrayOutputStream()
            connection.inputStream.use { input ->
                val bytes = ByteArray(2048)
                while (true) {
                    val count = input.read(bytes)
                    if (count < 0) break
                    require(buffer.size() + count < 64000) { "Respuesta excesivamente larga de Groq." }
                    buffer.write(bytes, 0, count)
                }
            }
            val response = JSONObject(buffer.toString("UTF-8"))
            val answer = response.optJSONArray("choices")?.optJSONObject(0)
                ?.optJSONObject("message")?.optString("content").orEmpty().trim()
            if (answer.isEmpty()) throw IllegalStateException("Groq no devolvió una respuesta de texto.")
            return answer.take(5000)
        } finally {
            connection.disconnect()
        }
    }
}
