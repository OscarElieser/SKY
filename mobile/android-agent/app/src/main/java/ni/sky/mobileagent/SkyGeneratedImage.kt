package ni.sky.mobileagent

import android.graphics.BitmapFactory
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL

/**
 * Generación de imágenes auténtica mediante el modelo Gemini de imágenes.
 * NO devuelve una plantilla si la API falla. No incorpora ninguna clave en código.
 */
object SkyGeneratedImage {
    const val MODEL = "gemini-nano-banana-2.1"
    const val ENDPOINT = "https://generativelanguage.googleapis.com/v1/models/$MODEL:generateContent"
    private const val MAX_REPLY = 20 * 1024 * 1024
    private const val MAX_IMAGE = 12 * 1024 * 1024
    val RATIOS = setOf("1:1", "16:9", "9:16", "4:3", "3:4")

    data class Result(val bytes: ByteArray, val mime: String, val model: String)

    internal fun requestPayload(prompt: String, ratio: String): JSONObject {
        require(prompt.trim().length in 12..1500) { "Escribí una descripción de 12 a 1500 caracteres." }
        require(ratio in RATIOS) { "Proporción de imagen no compatible." }
        val user = JSONObject().put("parts", JSONArray().put(JSONObject()
            .put("text", prompt.trim())))
        return JSONObject()
            .put("contents", JSONArray().put(user))
            .put("generationConfig", JSONObject()
                .put("responseModalities", JSONArray().put("IMAGE"))
                .put("imageConfig", JSONObject().put("aspectRatio", ratio)))
    }

    /** Explicitly reject text-only, empty and oversized replies instead of inventing output. */
    internal fun parse(response: JSONObject): Result {
        val candidates = response.optJSONArray("candidates")
        val parts = candidates?.optJSONObject(0)?.optJSONObject("content")
            ?.optJSONArray("parts")
        if (parts != null) for (i in 0 until parts.length()) {
            val part = parts.optJSONObject(i) ?: continue
            val inline = part.optJSONObject("inlineData") ?: continue
            val mime = inline.optString("mimeType")
            if (mime !in setOf("image/png", "image/jpeg", "image/webp")) continue
            val encoded = inline.optString("data")
            require(encoded.isNotBlank() && encoded.length <= MAX_IMAGE * 2) {
                "El modelo no devolvió una imagen válida dentro del límite."
            }
            val bytes = try { Base64.decode(encoded, Base64.DEFAULT) }
                catch (_: IllegalArgumentException) { throw IllegalStateException("Imagen devuelta en formato inválido.") }
            require(bytes.isNotEmpty() && bytes.size <= MAX_IMAGE) {
                "La imagen generada supera el tamaño admitido."
            }
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
            require(bounds.outWidth in 1..8192 && bounds.outHeight in 1..8192) {
                "Los datos recibidos no representan una imagen decodificable."
            }
            return Result(bytes, mime, MODEL)
        }
        val reason = response.optJSONObject("error")?.optString("message").orEmpty()
        throw IllegalStateException(if (reason.isNotBlank())
            "Gemini no generó la imagen: " + reason.take(180)
        else "Gemini no devolvió una imagen; no se creó un archivo falso.")
    }

    fun generate(key: String, prompt: String, ratio: String = "1:1"): Result {
        require(SkyPhoneCloud.validPersonalKey(key)) { "Configurá tu clave de Gemini en Ajustes." }
        val body = requestPayload(prompt, ratio).toString().toByteArray(Charsets.UTF_8)
        val conn = URL(ENDPOINT).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "POST"
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 20_000
            conn.readTimeout = 120_000
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            conn.setRequestProperty("x-goog-api-key", key)
            conn.setFixedLengthStreamingMode(body.size)
            conn.doOutput = true
            conn.outputStream.use { it.write(body) }
            val status = conn.responseCode
            if (status !in 200..299) throw IllegalStateException(
                when (status) {
                    400 -> "El modelo de imágenes rechazó la solicitud."
                    401,403 -> "Gemini no autorizó la clave para generación de imágenes."
                    404 -> "El modelo de imágenes no está disponible en tu proyecto."
                    429 -> "Se agotó la cuota de imágenes de Gemini."
                    in 500..599 -> "El servicio de imágenes no está disponible."
                    else -> "Error HTTP $status al generar imagen."
                }
            )
            val bytes = ByteArrayOutputStream()
            conn.inputStream.use { input ->
                val block = ByteArray(8192)
                while (true) {
                    val len = input.read(block)
                    if (len < 0) break
                    require(bytes.size() + len <= MAX_REPLY) {
                        "El servidor devolvió una imagen demasiado grande."
                    }
                    bytes.write(block, 0, len)
                }
            }
            return parse(JSONObject(bytes.toString(Charsets.UTF_8)))
        } finally { conn.disconnect() }
    }
}
