package ni.sky.mobileagent

import android.content.Context
import android.media.MediaMetadataRetriever
import android.util.Base64
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Generación real de video por Interactions API Gemini Omni Flash 1.1.
 * SOLO modalidad pagada, con confirmación del usuario en MainActivity.
 * Ningún fallback a video de texto: errores y cuotas se reportan con honestidad.
 */
object SkyAiVideo {
    const val MODEL = "gemini-omni-1.1-flash"
    const val ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
    private const val MAX_RESPONSE = 44 * 1024 * 1024
    private const val MAX_VIDEO = 30 * 1024 * 1024
    val RATIOS = setOf("16:9", "9:16")

    internal fun payload(prompt: String, ratio: String): JSONObject {
        require(prompt.trim().length in 20..1400) {
            "Escribí una escena de entre 20 y 1400 caracteres."
        }
        require(ratio in RATIOS) { "La proporción solicitada no es válida." }
        return JSONObject().put("model", MODEL)
            .put("input", prompt.trim())
            .put("response_format", JSONObject()
                .put("type", "video")
                .put("aspect_ratio", ratio)
                .put("resolution", "360p"))
    }

    private fun readBounded(conn: HttpURLConnection): JSONObject {
        val status = conn.responseCode
        if (status !in 200..299) throw IllegalStateException(when (status) {
            400 -> "Gemini rechazó la solicitud de video."
            401, 403 -> "La clave no está habilitada para el modelo de video de pago."
            404 -> "El generador de video no está disponible para esta cuenta."
            429 -> "Gemini agotó la cuota de generación de video."
            in 500..599 -> "El generador de video de Google no está disponible."
            else -> "Error HTTP $status al generar video."
        })
        val output = ByteArrayOutputStream()
        conn.inputStream.use { stream ->
            val buffer = ByteArray(8192)
            while (true) {
                val read = stream.read(buffer)
                if (read < 0) break
                require(output.size() + read <= MAX_RESPONSE) {
                    "El video de IA supera el tamaño seguro de respuesta de este teléfono."
                }
                output.write(buffer, 0, read)
            }
        }
        return JSONObject(output.toString(Charsets.UTF_8))
    }

    /** Solo datos del modelo real y cabecera ftyp reconocible; nunca placeholders. */
    internal fun videoBytes(result: JSONObject): ByteArray {
        val interaction = result.optJSONObject("interaction") ?: result
        val video = interaction.optJSONObject("output_video")
            ?: interaction.optJSONObject("outputVideo")
            ?: throw IllegalStateException("El modelo no entregó un video. No hay MP4 para guardar.")
        val encoded = video.optString("data")
        require(encoded.isNotBlank() && encoded.length <= MAX_VIDEO * 2) {
            "El modelo no devolvió un video dentro de los límites."
        }
        val bytes = try { Base64.decode(encoded, Base64.DEFAULT) }
            catch (_: IllegalArgumentException) {
                throw IllegalStateException("Gemini devolvió video con codificación inválida.")
            }
        require(bytes.size in 1025..MAX_VIDEO &&
            bytes.copyOfRange(4, 8).contentEquals(byteArrayOf(102,116,121,112))) {
            "El resultado no es un archivo MP4 verificable."
        }
        return bytes
    }

    fun create(context: Context, key: String, prompt: String, ratio: String): File {
        require(SkyPhoneCloud.validPersonalKey(key)) { "Configurá tu clave Gemini en Ajustes." }
        val body = payload(prompt, ratio).toString().toByteArray(Charsets.UTF_8)
        val connection = URL(ENDPOINT).openConnection() as HttpURLConnection
        val reply: JSONObject
        try {
            connection.requestMethod = "POST"
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 25_000
            connection.readTimeout = 180_000
            connection.setRequestProperty("x-goog-api-key", key)
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.setFixedLengthStreamingMode(body.size)
            connection.doOutput = true
            connection.outputStream.use { it.write(body) }
            reply = readBounded(connection)
        } finally { connection.disconnect() }

        val bytes = videoBytes(reply)
        val temporary = File(context.cacheDir, "sky_ai_video_pending.mp4")
        val finished = File(context.cacheDir, "sky_ai_video_last.mp4")
        temporary.delete()
        try {
            temporary.outputStream().use { it.write(bytes) }
            val metadata = MediaMetadataRetriever()
            try {
                metadata.setDataSource(temporary.absolutePath)
                val duration = metadata.extractMetadata(
                    MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0
                val width = metadata.extractMetadata(
                    MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 0
                require(duration > 0 && width > 0) {
                    "El resultado no contiene una pista de video válida."
                }
            } finally { metadata.release() }
            finished.delete()
            require(temporary.renameTo(finished)) {
                "No fue posible terminar de guardar el video recibido."
            }
            return finished
        } finally { temporary.delete() }
    }
}
