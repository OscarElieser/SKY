package ni.sky.mobileagent

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL

/** Canal HTTPS estricto: redirecciones desactivadas y respuestas limitadas. */
object SkyNetwork {
    // A 6K-token model response can contain UTF-8 or JSON-escaped content.
    // Keep a hard byte budget, but do not reject a valid long document at 128 KiB.
    internal const val CHAT_RESPONSE_MAX_BYTES = 512_000
    internal const val CONTROL_RESPONSE_MAX_BYTES = 16_384

    internal fun readBoundedBytes(input: InputStream, limit: Int): ByteArray {
        require(limit in 1..CHAT_RESPONSE_MAX_BYTES)
        val out = ByteArrayOutputStream()
        val buffer = ByteArray(4096)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            if (count == 0) continue
            if (out.size() + count > limit) {
                throw IllegalStateException("La respuesta de SKY supera el tamaño seguro; " +
                    "no se mostrará información incompleta.")
            }
            out.write(buffer, 0, count)
        }
        return out.toByteArray()
    }

    fun validateServer(raw: String): String {
        val value = raw.trim().trimEnd('/')
        val uri = URI(value)
        require(uri.scheme?.lowercase() == "https" &&
            !uri.host.isNullOrEmpty() && uri.userInfo == null &&
            uri.query == null && uri.fragment == null &&
            (uri.path.isNullOrEmpty() || uri.path == "/")) {
            "Indicá la dirección HTTPS privada de SKY, sin rutas."
        }
        return value
    }
    /** Chat endpoints are strictly allowlisted and never accept the owner API key. */
    fun requestChat(server: String, path: String, token: String,
                    data: JSONObject): JSONObject {
        require(path == "/api/sky/mobile-chat/pair" ||
                path == "/api/sky/mobile-chat/chat" ||
                path == "/api/sky/mobile-chat/status") { "Ruta móvil no permitida" }
        val base = validateServer(server)
        val conn = URL(base + path).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "POST"
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 8000
            conn.readTimeout = if (path.endsWith("/chat")) 360000 else 8000
            conn.setRequestProperty("Accept", "application/json")
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            val header = if (path.endsWith("/pair")) "X-SKY-MOBILE-TOKEN" else "X-SKY-CHAT-TOKEN"
            conn.setRequestProperty(header, token)
            conn.doOutput = true
            conn.outputStream.use { it.write(data.toString().toByteArray(Charsets.UTF_8)) }
            val code = conn.responseCode
            if (code !in 200..299) {
                val reason = when (code) {
                    401, 403 -> "SKY API rechazó la sesión. Renovala desde Ajustes."
                    409 -> "SKY API no tiene disponible el modelo Ollama seleccionado. " +
                        "Revisá el servidor y el modelo instalado. No se envió a Gemini."
                    429 -> "SKY API o el proveedor externo alcanzó un límite " +
                        "de solicitudes. No se reintentará ni se cambiará de modelo " +
                        "automáticamente. Conservá el mensaje para más tarde."
                    422 -> "El texto o el historial supera el límite del modelo. " +
                        "SKY conservó tu consulta; intentá un tramo más corto."
                    in 500..599 -> "SKY API no pudo responder. " +
                        "Verificá que el servidor esté disponible."
                    else -> "SKY API respondió HTTP $code."
                }
                throw IllegalStateException(reason)
            }
            val output = conn.inputStream.use { stream ->
                readBoundedBytes(stream, CHAT_RESPONSE_MAX_BYTES)
            }
            return JSONObject(String(output, Charsets.UTF_8))
        } finally {
            conn.disconnect()
        }
    }

    fun request(server: String, path: String, method: String,
                token: String? = null, data: JSONObject? = null): JSONObject {
        val base = validateServer(server)
        require(path.startsWith("/api/sky/mobile-agent/") &&
            !path.contains("..") && !path.contains("?") &&
            method in listOf("GET", "POST")) { "Solicitud no permitida." }
        val conn = URL(base + path).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = method
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 6000
            conn.readTimeout = 6000
            conn.setRequestProperty("Accept", "application/json")
            if (token != null) conn.setRequestProperty("X-SKY-MOBILE-TOKEN", token)
            if (data != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                conn.outputStream.use { it.write(data.toString().toByteArray(Charsets.UTF_8)) }
            }
            val code = conn.responseCode
            if (code !in 200..299) throw IllegalStateException("SKY respondió HTTP " + code)
            val result = conn.inputStream.use { input ->
                readBoundedBytes(input, CONTROL_RESPONSE_MAX_BYTES)
            }
            return JSONObject(String(result, Charsets.UTF_8))
        } finally {
            conn.disconnect()
        }
    }
}
