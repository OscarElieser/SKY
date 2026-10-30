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
    const val MODEL = "openai/gpt-oss-20b"
    private const val MODELS_ENDPOINT = "https://api.groq.com/openai/v1/models"
    private val prioritized = listOf(MODEL, "openai/gpt-oss-120b", "qwen/qwen3.8-27b")
    @Volatile private var selectedModel: String? = null
    @Volatile private var selectionKeyHash: Int? = null
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

    fun payload(message: String, history: JSONArray, model: String = MODEL): JSONObject {
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
                "sin fuentes consultadas. Si no sabes algo, dilo. " +
                SkyResponseQuality.INSTRUCTION))
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
            .put("model", model)
            .put("messages", messages)
            .put("temperature", 0.5)
            .put("max_completion_tokens", SkyPhoneCloud.responseTokenLimit(message).coerceIn(300, 3500))
    }

    /**
     * Do not assume the old Llama model exists. Groq removed it from free
     * access in August 2026. Read the active model catalog for this key.
     * HTTP errors never echo authorization headers or secrets.
     */
    fun availableTextModels(key: String): List<String> {
        require(validKey(key)) { "Revisá tu clave Groq." }
        val connection = URL(MODELS_ENDPOINT).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 9000
            connection.readTimeout = 15000
            connection.setRequestProperty("Authorization", "Bearer $key")
            connection.setRequestProperty("Accept", "application/json")
            val status = connection.responseCode
            if (status !in 200..299) {
                throw IllegalStateException(when (status) {
                    401, 403 -> "Groq rechazó la clave. Revisá el proyecto y la API key."
                    429 -> "Groq alcanzó un límite temporal. Reintentá después."
                    else -> "No pude consultar los modelos de Groq (HTTP $status)."
                })
            }
            val buffer = ByteArrayOutputStream()
            connection.inputStream.use { input ->
                val bytes = ByteArray(2048)
                while (true) {
                    val count = input.read(bytes)
                    if (count < 0) break
                    require(buffer.size() + count <= 100000) { "Respuesta de modelos demasiado grande." }
                    buffer.write(bytes, 0, count)
                }
            }
            val models = JSONObject(buffer.toString("UTF-8")).optJSONArray("data")
                ?: throw IllegalStateException("Groq no devolvió modelos disponibles.")
            val available = HashSet<String>()
            for (i in 0 until models.length()) {
                val item = models.optJSONObject(i) ?: continue
                if (item.optBoolean("active", true)) available.add(item.optString("id"))
            }
            val offered = prioritized.filter { it in available }
            if (offered.isEmpty()) {
                throw IllegalStateException(
                    "Groq no ofrece un modelo de texto compatible en este proyecto. " +
                        "Revisá los modelos de tu cuenta en console.groq.com.")
            }
            return offered
        } finally {
            connection.disconnect()
        }
    }

    fun selectModel(available: Collection<String>): String? =
        prioritized.firstOrNull { it in available }

    private class ModelUnavailable : IllegalStateException("Modelo Groq no disponible.")

    fun reply(key: String, message: String, history: JSONArray): String {
        require(validKey(key)) { "Configurá tu clave de Groq en Ajustes." }
        val modelKey = key.hashCode()
        val selected = if (selectionKeyHash == modelKey) selectedModel else null
        val candidates = if (selected != null) listOf(selected) else availableTextModels(key)
        for (model in candidates) {
            try {
                val answer = completeReply(key, message, history, model)
                selectedModel = model
                selectionKeyHash = modelKey
                return answer
            } catch (error: ModelUnavailable) {
                // A model may be listed but not enabled. Recheck the catalog
                // and try a different known-compatible text model once.
                for (alternate in availableTextModels(key).filter { it != model }) {
                    try {
                        val answer = completeReply(key, message, history, alternate)
                        selectedModel = alternate
                        selectionKeyHash = modelKey
                        return answer
                    } catch (_: ModelUnavailable) { /* Try next permitted model. */ }
                }
                throw IllegalStateException(
                    "Ningún modelo Groq disponible aceptó la consulta. Revisá tu proyecto.")
            }
        }
        throw IllegalStateException("No hay modelos Groq disponibles.")
    }

    private data class CompletionChunk(val text: String, val limited: Boolean)

    /**
     * Request additional text only when Groq explicitly reports finish_reason=length.
     * Never silently remove the last part of a document. Respect user quota:
     * two continuations maximum; report a remaining provider limit honestly.
     */
    private fun completeReply(key: String, message: String, history: JSONArray,
                              model: String): String {
        var chunk = send(key, payload(message, history, model).toString())
        val completed = StringBuilder(chunk.text)
        var attempts = 0
        while (chunk.limited && attempts < 2 && completed.length < 65_000) {
            attempts++
            val continuedHistory = JSONArray(history.toString())
            continuedHistory.put(JSONObject().put("role", "user")
                .put("content", message.take(2500)))
            continuedHistory.put(JSONObject().put("role", "assistant")
                .put("content", completed.toString().takeLast(1600)))
            chunk = try {
                send(key, payload(
                    "Continúa el texto pendiente desde la última frase, sin repetir " +
                        "lo anterior. Conserva títulos y secciones. No inventes " +
                        "información ni acciones.",
                    continuedHistory, model).toString())
            } catch (_: Exception) {
                return completed.toString() +
                    "\n\n[La respuesta quedó incompleta por un error o límite del proveedor. " +
                    "Podés solicitar «continuar» para recuperar el resto.]"
            }
            completed.append("\n").append(chunk.text)
        }
        if (chunk.limited) completed.append(
            "\n\n[El proveedor alcanzó su límite de respuesta. " +
                "Podés solicitar «continuar» para completar la información.]")
        return completed.toString()
    }

    private fun send(key: String, payload: String): CompletionChunk {
        val data = payload.toByteArray(Charsets.UTF_8)
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
            if (status == 404) throw ModelUnavailable()
            if (status !in 200..299) {
                val reason = when (status) {
                    400 -> "Groq rechazó la solicitud."
                    401, 403 -> "Groq no autorizó la clave. Revisala en Ajustes."
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
            if (answer.isEmpty()) throw IllegalStateException("Groq no devolvió texto.")
            require(answer.length <= 65_000) { "Groq devolvió demasiado texto." }
            return CompletionChunk(answer,
                response.optJSONArray("choices")?.optJSONObject(0)
                    ?.optString("finish_reason") == "length")
        } finally {
            connection.disconnect()
        }
    }

}
