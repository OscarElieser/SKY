package ni.sky.mobileagent

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL

/** Canal HTTPS estricto: redirecciones desactivadas y respuestas limitadas. */
object SkyNetwork {
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
                path == "/api/sky/mobile-chat/chat") { "Ruta móvil no permitida" }
        val base = validateServer(server)
        val conn = URL(base + path).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "POST"
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 8000
            conn.readTimeout = if (path.endsWith("/chat")) 90000 else 8000
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
                    429 -> "SKY API aplicó su límite de protección por dispositivo. " +
                        "Reintentá luego; no es la cuota de Gemini."
                    in 500..599 -> "SKY API no pudo responder. " +
                        "Verificá que el servidor esté disponible."
                    else -> "SKY API respondió HTTP $code."
                }
                throw IllegalStateException(reason)
            }
            val output = ByteArrayOutputStream()
            conn.inputStream.use { stream ->
                val bytes = ByteArray(2048)
                while (output.size() <= 32768) {
                    val count = stream.read(bytes)
                    if (count < 0) break
                    output.write(bytes, 0, count)
                }
            }
            require(output.size() <= 32768) { "Respuesta de chat demasiado grande" }
            return JSONObject(output.toString("UTF-8"))
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
            val result = ByteArrayOutputStream()
            conn.inputStream.use { input ->
                val buffer = ByteArray(2048)
                while (result.size() <= 16384) {
                    val n = input.read(buffer)
                    if (n < 0) break
                    result.write(buffer, 0, n)
                }
            }
            require(result.size() <= 16384) { "Respuesta del servidor demasiado grande." }
            return JSONObject(result.toString("UTF-8"))
        } finally {
            conn.disconnect()
        }
    }
}
