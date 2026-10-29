package ni.sky.mobileagent

import android.content.ContentResolver
import android.os.SystemClock
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

/**
 * Gemini Files API por fragmentos de 4 MiB. No carga 100 MB en memoria.
 * Los archivos remotos creados se eliminan después de la respuesta.
 */
object SkyGeminiFiles {
    data class Uploaded(val name: String, val uri: String, val mime: String)
    private const val BASE = "https://generativelanguage.googleapis.com"
    private const val CHUNK = 4 * 1024 * 1024
    private val safeName = Regex("""files/[a-z0-9][a-z0-9-]{0,78}""")

    private fun connection(address: String): HttpURLConnection {
        val target = URL(address)
        require(target.protocol == "https" &&
            target.host.lowercase(Locale.ROOT) == "generativelanguage.googleapis.com" &&
            target.port == -1 && target.userInfo == null) {
            "El servidor de carga no coincide con Google."
        }
        return (target.openConnection() as HttpURLConnection).apply {
            instanceFollowRedirects = false
            connectTimeout = 20_000
            readTimeout = 95_000
        }
    }

    private fun readResponse(conn: HttpURLConnection): JSONObject {
        val status = conn.responseCode
        require(status in 200..299) {
            when (status) {
                400 -> "Gemini rechazó el formato o el archivo."
                401, 403 -> "Clave Gemini no autorizada para archivos."
                413 -> "Gemini rechazó el tamaño del archivo."
                429 -> "Cuota de Gemini agotada temporalmente."
                else -> "Servidor Gemini respondió HTTP " + status
            }
        }
        val bytes = conn.inputStream.use { input ->
            val output = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(4096)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                require(output.size() + read <= 131072) { "Respuesta del servicio demasiado grande." }
                output.write(buffer, 0, read)
            }
            output.toByteArray()
        }
        return if (bytes.isEmpty()) JSONObject() else JSONObject(bytes.toString(Charsets.UTF_8))
    }

    fun upload(resolver: ContentResolver, apiKey: String, item: SkyAttachmentBatch.Item): Uploaded {
        require(SkyPhoneCloud.validPersonalKey(apiKey)) { "Configurá Gemini en Ajustes." }
        require(item.kind == SkyAttachmentBatch.Kind.CLOUD)
        val start = connection(BASE + "/upload/v1beta/files").apply {
            requestMethod = "POST"
            setRequestProperty("x-goog-api-key", apiKey)
            setRequestProperty("X-Goog-Upload-Protocol", "resumable")
            setRequestProperty("X-Goog-Upload-Command", "start")
            setRequestProperty("X-Goog-Upload-Header-Content-Length", item.size.toString())
            setRequestProperty("X-Goog-Upload-Header-Content-Type", item.mime)
            setRequestProperty("Content-Type", "application/json")
            doOutput = true
        }
        val sessionUrl: String
        try {
            val body = JSONObject().put("file", JSONObject().put("display_name", item.name))
                .toString().toByteArray(Charsets.UTF_8)
            start.setFixedLengthStreamingMode(body.size)
            start.outputStream.use { it.write(body) }
            readResponse(start)
            sessionUrl = start.getHeaderField("X-Goog-Upload-URL")
                ?: throw IllegalStateException("Gemini no devolvió una sesión de carga.")
        } finally { start.disconnect() }
        // No se envían archivos a hosts redirigidos ni direcciones externas.
        val url = URL(sessionUrl)
        require(url.protocol == "https" && url.host == "generativelanguage.googleapis.com" &&
            url.userInfo == null && url.port == -1) {
            "URL de carga de archivos no verificada."
        }

        var offset = 0L
        var result = JSONObject()
        resolver.openInputStream(item.uri)?.use { input ->
            val buffer = ByteArray(CHUNK)
            while (offset < item.size) {
                val length = minOf(CHUNK.toLong(), item.size - offset).toInt()
                var filled = 0
                while (filled < length) {
                    val n = input.read(buffer, filled, length - filled)
                    require(n > 0) { "El archivo cambió o terminó antes de la carga." }
                    filled += n
                }
                val last = offset + filled == item.size
                val part = connection(sessionUrl).apply {
                    requestMethod = "POST"
                    setRequestProperty("X-Goog-Upload-Offset", offset.toString())
                    setRequestProperty("X-Goog-Upload-Command", if (last) "upload, finalize" else "upload")
                    setRequestProperty("Content-Type", "application/octet-stream")
                    setFixedLengthStreamingMode(filled)
                    doOutput = true
                }
                try {
                    part.outputStream.use { it.write(buffer, 0, filled) }
                    result = readResponse(part)
                    offset += filled
                } finally { part.disconnect() }
            }
        } ?: throw IllegalArgumentException("No se pudo abrir el archivo seleccionado.")
        require(offset == item.size) { "El archivo no se envió completamente." }
        val info = result.optJSONObject("file")
            ?: throw IllegalStateException("Gemini no confirmó la carga final.")
        val name = info.optString("name")
        val uri = info.optString("uri")
        require(safeName.matches(name) && uri.startsWith("https://")) {
            "Gemini devolvió un identificador de archivo inválido."
        }
        return Uploaded(name, uri, item.mime)
    }

    fun awaitReady(apiKey: String, file: Uploaded) {
        require(safeName.matches(file.name))
        val start = SystemClock.elapsedRealtime()
        while (SystemClock.elapsedRealtime() - start < 150_000) {
            val conn = connection(BASE + "/v1beta/" + file.name).apply {
                requestMethod = "GET"
                setRequestProperty("x-goog-api-key", apiKey)
            }
            val state = try {
                val obj = readResponse(conn)
                obj.optString("state", "ACTIVE")
            } finally { conn.disconnect() }
            when (state) {
                "ACTIVE" -> return
                "FAILED" -> throw IllegalStateException("Gemini no pudo procesar el archivo.")
                "PROCESSING", "STATE_UNSPECIFIED" -> Thread.sleep(4000)
                else -> throw IllegalStateException("Gemini devolvió un estado de archivo desconocido.")
            }
        }
        throw IllegalStateException("El archivo sigue procesándose. Probá con uno más pequeño.")
    }

    fun delete(apiKey: String, file: Uploaded) {
        require(safeName.matches(file.name))
        val conn = connection(BASE + "/v1beta/" + file.name).apply {
            requestMethod = "DELETE"
            setRequestProperty("x-goog-api-key", apiKey)
        }
        try {
            val code = conn.responseCode
            require(code in 200..299 || code == 404) {
                "No se confirmó el borrado del archivo de Gemini."
            }
        } finally { conn.disconnect() }
    }

    fun analyze(context: android.content.Context, apiKey: String,
                items: List<SkyAttachmentBatch.Item>, question: String): String {
        require(items.isNotEmpty() && items.size <= SkyAttachmentBatch.MAX_FILES)
        val uploaded = mutableListOf<Uploaded>()
        val extracted = mutableListOf<String>()
        try {
            for (item in items) {
                if (item.kind == SkyAttachmentBatch.Kind.OFFICE) {
                    require(item.size <= SkyAttachmentBatch.OFFICE_LOCAL_MAX) {
                        "Este archivo Office supera 8 MB. Su análisis completo todavía necesita " +
                            "un lector especializado: " + item.name
                    }
                    val content = SkyAttachmentReader.read(context, item.uri)
                    require(!content.text.isNullOrBlank()) {
                        "No encontré texto legible en " + item.name
                    }
                    extracted.add("Documento " + item.name + " (extracto):\n" + content.text)
                } else {
                    val file = upload(context.contentResolver, apiKey, item)
                    uploaded.add(file)
                    awaitReady(apiKey, file)
                }
            }
            return SkyPhoneCloud.analyzeFileReferences(apiKey, uploaded, extracted, question)
        } finally {
            for (file in uploaded) {
                runCatching { delete(apiKey, file) }
            }
        }
    }
}
