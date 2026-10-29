package ni.sky.mobileagent

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import java.util.Locale

/** SAF: sólo metadatos. Nunca se leen 100 MB completos en RAM. */
object SkyAttachmentBatch {
    const val MAX_FILES = 5
    const val MAX_PER_FILE = 100L * 1024L * 1024L
    const val MAX_TOTAL = 300L * 1024L * 1024L
    const val PDF_CLOUD_MAX = 50L * 1024L * 1024L
    const val OFFICE_LOCAL_MAX = 8L * 1024L * 1024L

    enum class Kind { CLOUD, OFFICE, UNSUPPORTED }
    data class Item(val uri: Uri, val name: String, val size: Long,
        val mime: String, val kind: Kind) {
        fun sizeMb(): String = String.format(Locale.US, "%.1f", size / 1048576.0)
    }
    private val images = mapOf(
        "png" to "image/png", "jpg" to "image/jpeg", "jpeg" to "image/jpeg",
        "webp" to "image/webp", "heic" to "image/heic", "heif" to "image/heif"
    )
    private val audio = mapOf(
        "mp3" to "audio/mpeg", "wav" to "audio/wav", "m4a" to "audio/mp4",
        "aac" to "audio/aac", "flac" to "audio/flac", "ogg" to "audio/ogg"
    )
    private val video = mapOf(
        "mp4" to "video/mp4", "m4v" to "video/mp4", "mov" to "video/quicktime",
        "webm" to "video/webm", "mpeg" to "video/mpeg", "mpg" to "video/mpeg",
        "3gp" to "video/3gpp"
    )
    private val texts = setOf("txt", "md", "csv", "json", "xml", "html", "htm",
        "py", "kt", "java", "js", "ts", "dart", "css", "sql", "yaml", "yml", "log",
        "sh", "ps1", "ini", "cfg", "rtf", "svg", "tex", "ipynb")
    private val office = setOf("docx", "xlsx", "pptx")

    fun supportedType(filename: String, reportedMime: String): Pair<Kind, String> {
        val extension = filename.substringAfterLast('.', "").lowercase(Locale.ROOT)
        return when {
            extension == "pdf" -> Kind.CLOUD to "application/pdf"
            extension in images -> Kind.CLOUD to images.getValue(extension)
            extension in audio -> Kind.CLOUD to audio.getValue(extension)
            extension in video -> Kind.CLOUD to video.getValue(extension)
            extension in texts -> Kind.CLOUD to
                (if (extension == "csv") "text/csv" else "text/plain")
            extension in office -> Kind.OFFICE to reportedMime
            reportedMime == "application/pdf" -> Kind.CLOUD to reportedMime
            reportedMime.startsWith("image/") && reportedMime != "image/svg+xml" ->
                Kind.CLOUD to reportedMime
            reportedMime in setOf("audio/mpeg", "audio/wav", "audio/ogg",
                "video/mp4", "video/webm", "text/plain", "text/csv") ->
                Kind.CLOUD to reportedMime
            else -> Kind.UNSUPPORTED to reportedMime
        }
    }

    fun readMetadata(resolver: ContentResolver, uri: Uri): Item {
        require(uri.scheme == "content") { "Seleccioná archivos con el explorador de Android." }
        var filename = "archivo"
        var size = -1L
        resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE),
            null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val nameCol = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                val sizeCol = cursor.getColumnIndex(OpenableColumns.SIZE)
                if (nameCol >= 0 && !cursor.isNull(nameCol)) filename = cursor.getString(nameCol)
                if (sizeCol >= 0 && !cursor.isNull(sizeCol)) size = cursor.getLong(sizeCol)
            }
        }
        if (size < 0) {
            size = resolver.openAssetFileDescriptor(uri, "r")
                ?.use { if (it.length >= 0) it.length else -1L } ?: -1L
        }
        require(size > 0) { "Android no informó el tamaño del archivo. Copialo a Descargas." }
        require(size <= MAX_PER_FILE) { "El archivo supera 100 MB: " + filename.take(80) }
        filename = filename.replace(Regex("[\r\n\t]"), " ").take(120)
        val (kind, mime) = supportedType(filename, resolver.getType(uri).orEmpty())
        require(kind != Kind.UNSUPPORTED) {
            "El formato de " + filename.take(80) + " aún no tiene un lector verificable."
        }
        require(!(mime == "application/pdf" && size > PDF_CLOUD_MAX)) {
            "Gemini limita los documentos PDF a 50 MB. Otros archivos admiten hasta 100 MB."
        }
        return Item(uri, filename, size, mime, kind)
    }

    fun validate(current: List<Item>, added: List<Item>): List<Item> {
        val distinct = (current + added).distinctBy { it.uri.toString() }
        require(distinct.size <= MAX_FILES) { "Máximo 5 archivos en una consulta." }
        require(distinct.sumOf { it.size } <= MAX_TOTAL) {
            "Máximo 300 MB combinados. Separá la consulta en dos grupos."
        }
        return distinct
    }
}
