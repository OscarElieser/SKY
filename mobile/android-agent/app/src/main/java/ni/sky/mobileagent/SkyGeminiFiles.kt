package ni.sky.mobileagent

import android.content.ContentResolver
import android.os.SystemClock
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.concurrent.CancellationException
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Gemini Files API por fragmentos de 4 MiB. No carga 100 MB en memoria.
 * Los archivos remotos creados se eliminan después de la respuesta.
 */
object SkyGeminiFiles {
    data class Uploaded(val name: String, val uri: String, val mime: String)

    /** Cancelación cooperativa entre fragmentos, sondeos y etapas de análisis. */
    class CancelToken {
        private val cancelled = AtomicBoolean(false)
        fun cancel() { cancelled.set(true) }
        fun isCancelled(): Boolean = cancelled.get()
        fun check() { if (cancelled.get()) throw CancellationException("Carga cancelada por vos.") }
    }

    private fun percent(done: Long, total: Long): Int =
        if (total <= 0L) 0 else ((done.coerceIn(0L, total) * 100L) / total).toInt()
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

    fun upload(resolver: ContentResolver, apiKey: String, item: SkyAttachmentBatch.Item,
               cancel: CancelToken = CancelToken(),
               onProgress: (Int) -> Unit = {}): Uploaded {
        cancel.check()
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
                cancel.check()
                val length = minOf(CHUNK.toLong(), item.size - offset).toInt()
                var filled = 0
                while (filled < length) {
                    cancel.check()
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
                    onProgress(percent(offset, item.size))
                } finally { part.disconnect() }
            }
        } ?: throw IllegalArgumentException("No se pudo abrir el archivo seleccionado.")
        cancel.check()
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

    fun awaitReady(apiKey: String, file: Uploaded,
                   cancel: CancelToken = CancelToken()) {
        cancel.check()
        require(safeName.matches(file.name))
        val start = SystemClock.elapsedRealtime()
        while (SystemClock.elapsedRealtime() - start < 150_000) {
            cancel.check()
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
                items: List<SkyAttachmentBatch.Item>, question: String,
                cancel: CancelToken = CancelToken(),
                onProgress: (String) -> Unit = {}): String {
        require(items.isNotEmpty() && items.size <= SkyAttachmentBatch.MAX_FILES)
        val uploaded = mutableListOf<Uploaded>()
        val extracted = mutableListOf<String>()
        val receipts = mutableListOf<String>()
        var response: String? = null
        var cleanupFailures = 0
        try {
            for ((index, item) in items.withIndex()) {
                cancel.check()
                val itemLabel = "Archivo " + (index + 1) + "/" + items.size +
                    " · " + item.name.take(35)
                onProgress(itemLabel + " · preparando...")
                if (item.kind == SkyAttachmentBatch.Kind.OFFICE) {
                    val text = SkyOfficeStreaming.preview(context.contentResolver, item)
                    cancel.check()
                    onProgress(itemLabel + " · texto extraído")
                    extracted.add("Documento " + item.name +
                        " (extracción parcial de texto y valores, sin gráficos ni diseño):\n" + text)
                    receipts.add(item.name.take(100) + ": texto parcial leído localmente")
                } else {
                    val file = upload(context.contentResolver, apiKey, item, cancel) { value ->
                        onProgress(itemLabel + " · enviado " + value + "%")
                    }
                    uploaded.add(file)
                    onProgress(itemLabel + " · procesando en Gemini...")
                    awaitReady(apiKey, file, cancel)
                    receipts.add(item.name.take(100) + ": archivo aceptado y preparado por Gemini")
                }
            }
            cancel.check()
            onProgress("Gemini está analizando " + items.size + " archivo(s)...")
            response = SkyPhoneCloud.analyzeFileReferences(apiKey, uploaded, extracted, question)
            cancel.check()
        } finally {
            if (uploaded.isNotEmpty()) onProgress("Solicitando eliminación de archivos temporales...")
            for (file in uploaded) {
                if (runCatching { delete(apiKey, file) }.isFailure) cleanupFailures++
            }
        }
        val evidence = if (response.isNullOrBlank()) "" else
            "\n\nTrazabilidad: " + receipts.size + "/" + items.size +
                " archivos preparados. " + receipts.joinToString("; ").take(800) +
                ". Esta traza comprueba la preparación, no la exactitud de cada conclusión."
        return response.orEmpty() + evidence + if (cleanupFailures > 0)
            "\nAviso: Gemini no confirmó el borrado de " + cleanupFailures +
                " archivo(s) temporal(es). Revisá tu cuenta; la retención puede ser de hasta 48 horas."
            else ""
    }
}
