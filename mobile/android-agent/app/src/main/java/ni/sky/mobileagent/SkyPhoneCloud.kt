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

    fun validPersonalKey(value: String): Boolean =
        value.length in 20..200 && value.all { it.isLetterOrDigit() || it == '_' || it == '-' }

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
                    "Sos SKY IA, compañera virtual amable y útil de Nicaragua. " +
                    "Respondé con naturalidad en español, de forma clara y breve. " +
                    "No afirmés haber abierto aplicaciones, realizado tareas ni consultado " +
                    "información en tiempo real si no lo verificaste. No tenés acceso " +
                    "a Windows, a datos privados del celular ni a herramientas del dispositivo."))))
            .put("contents", contents)
            .put("generationConfig", JSONObject()
                .put("maxOutputTokens", 1000)
                .put("temperature", 0.7))
    }

    fun reply(personalKey: String, message: String, history: JSONArray): String {
        require(validPersonalKey(personalKey)) { "Configurá una clave válida de Gemini en Ajustes." }
        val payload = makePayload(message, history).toString()
        require(payload.toByteArray(Charsets.UTF_8).size < 36000) {
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
