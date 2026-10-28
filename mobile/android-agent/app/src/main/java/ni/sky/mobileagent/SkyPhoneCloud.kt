package ni.sky.mobileagent

import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL

/**
 * SOLO SKY ANDROID. Modo experimental para una app PERSONAL con una clave
 * introducida por el propio usuario: no se compila ninguna clave en la APK.
 *
 * Para distribuir públicamente, sustituir por backend/AI Logic + App Check;
 * una clave usada desde el cliente sigue siendo recuperable en un teléfono
 * comprometido. No abre herramientas del PC ni ejecuta comandos del modelo.
 */
object SkyPhoneCloud {
    const val MODEL = "gemini-3.5-flash-lite"
    private const val API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"

    /**
     * Remove clipboard whitespace and invisible Unicode formatting before HTTPS.
     * Samsung/Android clipboard can insert them, even inside the pasted value.
     * Remove only whitespace/FORMAT marks; do not alter visible key characters.
     * No key contents should be logged, displayed, or committed.
     */
    fun normalizePersonalKey(raw: String): String = buildString(raw.length) {
        for (character in raw) {
            val invisible = character.isWhitespace() || Character.isSpaceChar(character) ||
                Character.getType(character) == Character.FORMAT.toInt()
            if (!invisible) append(character)
        }
    }

    /** User-facing validation without revealing any part of the credential. */
    fun personalKeyProblem(raw: String): String? {
        val value = normalizePersonalKey(raw)
        // Check wrapper BEFORE removing whitespace; don't mistake "Bearer KEY" for a raw key.
        if (raw.trimStart().startsWith("Bearer ", ignoreCase = true) ||
            raw.trimStart().startsWith("Bearer\\t", ignoreCase = true) ||
            value.startsWith("GEMINI_API_KEY=", ignoreCase = true) ||
            value.startsWith("x-goog-api-key:", ignoreCase = true) ||
            value.startsWith("{") || value.startsWith("[")) {
            return "Pegá únicamente la clave que entrega «Copiar clave», sin prefijos ni configuración."
        }
        if (value.isBlank()) {
            return "No se pegó ninguna clave. En Google AI Studio tocá «Copiar clave»."
        }
        if (value.startsWith("projects/", ignoreCase = true) ||
            value.startsWith("project/", ignoreCase = true) ||
            value.all { it in '0'..'9' }) {
            return "Pegaste el identificador del proyecto, no la API key. Tocá «Copiar clave»."
        }
        // New Google AI Studio auth keys may use different formats from old AIza keys.
        // Only enforce safe HTTP header encoding; Google alone checks validity.
        if (value.length !in 16..2048) {
            return "El texto copiado está vacío, incompleto o es demasiado largo. Copiá solamente la clave."
        }
        if (value.any { it.code !in 33..126 }) {
            return "La clave tiene caracteres que no se pueden enviar de forma segura por HTTPS. Copiala nuevamente."
        }
        return null
    }

    fun validPersonalKey(value: String): Boolean = personalKeyProblem(value) == null

    fun makePayload(message: String, history: JSONArray): JSONObject {
        require(message.isNotBlank() && message.length <= 4000) { "Escribí una consulta de hasta 4000 caracteres." }
        val contents = JSONArray()
        val start = (history.length() - 8).coerceAtLeast(0)
        for (i in start until history.length()) {
            val turn = history.optJSONObject(i) ?: continue
            val role = when (turn.optString("role")) {
                "user" -> "user"
                "assistant" -> "model"
                else -> continue
            }
            val text = turn.optString("content").take(2000).trim()
            if (text.isNotEmpty()) {
                contents.put(JSONObject()
                    .put("role", role)
                    .put("parts", JSONArray().put(JSONObject().put("text", text))))
            }
        }
        contents.put(JSONObject()
            .put("role", "user")
            .put("parts", JSONArray().put(JSONObject().put("text", message))))
        return JSONObject()
            .put("systemInstruction", JSONObject().put("parts",
                JSONArray().put(JSONObject().put("text",
                    "Sos SKY IA, una asistente personal cálida, ingeniosa y divertida de Nicaragua. " +
                    "Conversá en español natural, como en una charla cotidiana, sin repetir " +
                    "tu nombre en cada respuesta, sin saludos mecánicos y sin pedir que la " +
                    "persona repita «SKY». Podés bromear, motivar y ser cercana, " +
                    "adaptando el tono a lo que expresa la persona. No afirmés sentir emociones humanas " +
                    "ni conocer el estado emocional del usuario sin preguntarle. " +
                    "No prometás haber abierto apps, reproducido canciones o enviado mensajes " +
                    "si no fue comprobado por Android. La ejecución de herramientas locales " +
                    "se gestiona fuera de este modelo. No tenés acceso directo a contactos, " +
                    "chats, cámara ni a Windows desde esta respuesta de Gemini."))))
            .put("contents", contents)
            .put("generationConfig", JSONObject()
                .put("maxOutputTokens", 1000)
                .put("temperature", 0.7))
    }

    fun reply(personalKey: String, message: String, history: JSONArray): String {
        require(validPersonalKey(personalKey)) { "Configurá una clave de Gemini para probar con Google." }
        val payload = makePayload(message, history).toString()
        return send(personalKey, payload)
    }

    /**
     * A ONE-TIME photo chosen by the user. No ongoing camera access,
     * no biometric identification and no emotional/medical diagnosis.
     */
    fun reflectOnPhoto(personalKey: String, jpeg: ByteArray): String {
        require(jpeg.isNotEmpty() && jpeg.size <= 360_000) {
            "La fotografía es demasiado grande. Tomá otra foto."
        }
        val instruction = "Sos SKY, una amiga virtual cercana de Nicaragua. " +
            "Describí con mucho cuidado uno o dos detalles VISIBLES de la expresión " +
            "de la persona, sin identificarla. NO deduzcas su emoción real, " +
            "su salud mental, personalidad ni enfermedades a partir de la cara. " +
            "Preguntale directamente cómo se siente y ofrecé escucharla, " +
            "con tono cálido y natural. Máximo tres frases."
        val parts = JSONArray()
            .put(JSONObject().put("text", instruction))
            .put(JSONObject().put("inlineData", JSONObject()
                .put("mimeType", "image/jpeg")
                .put("data", android.util.Base64.encodeToString(jpeg, android.util.Base64.NO_WRAP))))
        val payload = JSONObject()
            .put("contents", JSONArray().put(JSONObject().put("role", "user").put("parts", parts)))
            .put("generationConfig", JSONObject().put("maxOutputTokens", 350))
            .toString()
        return send(personalKey, payload)
    }

    private fun send(personalKey: String, payload: String): String {
        require(validPersonalKey(personalKey)) { "Revisá la clave Gemini en Ajustes." }
        require(payload.toByteArray(Charsets.UTF_8).size < 600_000) {
            "La conversación es demasiado larga; iniciá una sesión nueva."
        }
        val connection = URL(API).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 9000
            connection.readTimeout = 45000
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("x-goog-api-key", personalKey)
            connection.doOutput = true
            connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val status = connection.responseCode
            if (status !in 200..299) {
                val reason = when (status) {
                    400 -> "Solicitud no aceptada por Gemini."
                    401, 403 -> "Clave sin autorización. Revisá la clave de Gemini en Ajustes."
                    404 -> "Modelo no disponible en tu proyecto de Gemini."
                    429 -> "Límite de uso de Gemini alcanzado. Intentá más tarde."
                    in 500..599 -> "Gemini no está disponible temporalmente."
                    else -> "Gemini devolvió HTTP $status."
                }
                throw IllegalStateException(reason)
            }
            val raw = ByteArrayOutputStream()
            connection.inputStream.use { input ->
                val buffer = ByteArray(2048)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    require(raw.size() + count <= 65536) { "Respuesta excesivamente larga de Gemini." }
                    raw.write(buffer, 0, count)
                }
            }
            val response = JSONObject(raw.toString("UTF-8"))
            val content = response.optJSONArray("candidates")
                ?.optJSONObject(0)?.optJSONObject("content")
                ?.optJSONArray("parts")
            val parts = ArrayList<String>()
            if (content != null) {
                for (i in 0 until content.length()) {
                    val text = content.optJSONObject(i)?.optString("text")?.trim().orEmpty()
                    if (text.isNotEmpty()) parts.add(text)
                }
            }
            val answer = parts.joinToString("\n").take(5000)
            if (answer.isBlank()) {
                throw IllegalStateException("Gemini no devolvió texto. Revisá tu solicitud.")
            }
            return answer
        } finally {
            connection.disconnect()
        }
    }
}
