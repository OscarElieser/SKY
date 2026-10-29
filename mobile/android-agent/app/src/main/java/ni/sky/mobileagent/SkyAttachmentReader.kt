package ni.sky.mobileagent

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Xml
import org.xmlpull.v1.XmlPullParser
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.Locale
import java.util.zip.ZipInputStream

/**
 * Lectura puntual de archivos elegidos explícitamente con el selector de Android.
 * No requiere acceso general al almacenamiento ni conserva el archivo original.
 */
object SkyAttachmentReader {
    data class Attachment(
        val filename: String,
        val mime: String,
        val text: String? = null,
        val jpeg: ByteArray? = null,
        val media: ByteArray? = null,
        val note: String = ""
    ) {
        val interpretable: Boolean get() = !text.isNullOrBlank() || jpeg != null || media != null
    }

    private const val MAX_FILE = 8 * 1024 * 1024
    // Subida inline temporal. El servicio remoto puede rechazar archivos
    // dependiendo de la cuota o del modelo autorizado por el propietario.
    private const val MAX_CLOUD_MEDIA = 5 * 1024 * 1024
    private const val MAX_TEXT = 3100
    private val textExtensions = setOf(
        "txt", "md", "csv", "tsv", "json", "xml", "html", "htm", "log",
        "kt", "java", "py", "js", "ts", "css", "sql", "yaml", "yml",
        "ini", "cfg", "sh", "ps1", "dart", "svg", "rtf"
    )

    fun read(context: Context, uri: Uri): Attachment {
        val resolver = context.contentResolver
        val mime = resolver.getType(uri) ?: "application/octet-stream"
        var name = "archivo"
        resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) name = cursor.getString(0) ?: name
        }
        name = name.take(120).replace(Regex("[\\r\\n\\t]"), " ")
        val suffix = name.substringAfterLast('.', "").lowercase(Locale.ROOT)
        val bytes = resolver.openInputStream(uri)?.use { stream ->
            val buffer = ByteArrayOutputStream()
            val part = ByteArray(8192)
            while (true) {
                val n = stream.read(part)
                if (n < 0) break
                require(buffer.size() + n <= MAX_FILE) {
                    "El archivo supera 8 MB. Seleccioná uno más pequeño."
                }
                buffer.write(part, 0, n)
            }
            buffer.toByteArray()
        } ?: throw IllegalArgumentException("Android no permitió leer el archivo.")

        if (bytes.isEmpty()) throw IllegalArgumentException("El archivo está vacío.")
        if (mime.startsWith("image/") && suffix != "svg" ||
            suffix in setOf("png", "jpg", "jpeg", "webp")) {
            // Limitar memoria incluso si una imagen pequeña está descomprimida a gran resolución.
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
            val longest = maxOf(bounds.outWidth, bounds.outHeight)
            if (longest <= 0) return Attachment(name, mime,
                note = "Formato de imagen no decodificable.")
            var sample = 1
            while (longest / sample > 1600) sample *= 2
            val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size,
                BitmapFactory.Options().apply { inSampleSize = sample })
                ?: return Attachment(name, mime, note = "Formato de imagen no decodificable.")
            val jpeg = jpegForModel(bitmap)
            bitmap.recycle()
            return Attachment(name, mime, jpeg = jpeg,
                note = if (jpeg == null) "Imagen demasiado grande para analizar." else "Imagen lista para analizar.")
        }
        if (suffix == "pdf" || mime == "application/pdf") {
            if (bytes.size <= MAX_CLOUD_MEDIA) {
                return Attachment(name, "application/pdf", media = bytes,
                    note = "Gemini podrá analizar el PDF completo, sujeto a los límites del modelo.")
            }
            val jpeg = renderFirstPdfPage(context, uri)
            return Attachment(name, mime, jpeg = jpeg,
                note = if (jpeg == null) "PDF mayor de 5 MB: no pude leer su primera página." else
                    "PDF mayor de 5 MB: se analizará visualmente solo la primera página.")
        }
        val mediaMime = when (suffix) {
            "mp3" -> "audio/mpeg"
            "wav" -> "audio/wav"
            "m4a" -> "audio/m4a"
            "aac" -> "audio/aac"
            "flac" -> "audio/flac"
            "ogg", "oga" -> "audio/ogg"
            "mp4", "m4v" -> "video/mp4"
            "mov" -> "video/mov"
            "webm" -> if (mime.startsWith("audio/")) "audio/webm" else "video/webm"
            "mpeg", "mpg" -> "video/mpeg"
            "avi" -> "video/avi"
            "3gp" -> "video/3gpp"
            else -> when {
                mime in setOf("audio/mpeg", "audio/wav", "audio/aac", "audio/ogg",
                    "audio/flac", "audio/webm", "video/mp4", "video/webm", "video/mpeg") -> mime
                else -> null
            }
        }
        if (mediaMime != null) {
            return if (bytes.size <= MAX_CLOUD_MEDIA)
                Attachment(name, mediaMime, media = bytes,
                    note = "Audio o video listo para analizar con Gemini, previa autorización.")
            else Attachment(name, mediaMime, note =
                "Audio o video mayor de 5 MB: requiere carga segura de archivos grandes, aún pendiente.")
        }
        if (suffix in setOf("docx", "xlsx", "pptx")) {
            val text = officeText(bytes, suffix)
            return Attachment(name, mime, text = text?.take(MAX_TEXT),
                note = if (text.isNullOrBlank()) "No se encontró texto legible en este archivo." else
                    "Documento Office: texto extraído; gráficos y formatos no incluidos.")
        }
        if (suffix in textExtensions || mime.startsWith("text/")) {
            return Attachment(name, mime,
                text = bytes.toString(Charsets.UTF_8).take(MAX_TEXT),
                note = "Texto extraído; se limita a los primeros $MAX_TEXT caracteres.")
        }
        return Attachment(name, mime, note =
            "Archivo adjuntado, pero este formato aún necesita un lector específico. " +
                "SKY no inventará su contenido.")
    }

    private fun officeText(data: ByteArray, ext: String): String? {
        val output = StringBuilder()
        var decompressed = 0
        var accepted = 0
        ZipInputStream(ByteArrayInputStream(data)).use { archive ->
            while (true) {
                val entry = archive.nextEntry ?: break
                val file = entry.name
                val allowed = when (ext) {
                    "docx" -> file == "word/document.xml"
                    "pptx" -> Regex("ppt/slides/slide[0-9]+\\.xml").matches(file)
                    else -> file == "xl/sharedStrings.xml" ||
                        Regex("xl/worksheets/sheet[0-9]+\\.xml").matches(file)
                }
                if (!allowed) {
                    archive.closeEntry()
                    continue
                }
                if (++accepted > 30) break
                val buf = ByteArrayOutputStream()
                val chunk = ByteArray(4096)
                while (true) {
                    val n = archive.read(chunk)
                    if (n < 0) break
                    decompressed += n
                    require(decompressed <= 2_000_000) {
                        "Documento Office demasiado grande para extraer texto con seguridad."
                    }
                    buf.write(chunk, 0, n)
                }
                if (output.isNotEmpty()) output.append("\n")
                output.append(readOfficeXml(buf.toByteArray(), ext))
                archive.closeEntry()
                if (output.length > MAX_TEXT + 500) break
            }
        }
        return output.toString().trim().takeIf { it.isNotEmpty() }
    }

    private fun readOfficeXml(xml: ByteArray, ext: String): String {
        val parser = Xml.newPullParser()
        parser.setInput(ByteArrayInputStream(xml), "UTF-8")
        val output = StringBuilder()
        var event = parser.eventType
        while (event != XmlPullParser.END_DOCUMENT && output.length < MAX_TEXT + 500) {
            if (event == XmlPullParser.START_TAG) {
                val name = parser.name.substringAfter(':')
                val interested = if (ext == "xlsx") name == "t" || name == "v"
                    else name == "t"
                if (interested) {
                    val value = parser.nextText().trim()
                    if (value.isNotEmpty()) output.append(value).append(' ')
                }
                if (name == "p" || name == "row") output.append("\n")
            }
            event = parser.next()
        }
        return output.toString().trim()
    }

    private fun renderFirstPdfPage(context: Context, uri: Uri): ByteArray? {
        val fd = context.contentResolver.openFileDescriptor(uri, "r") ?: return null
        fd.use { descriptor ->
            PdfRenderer(descriptor).use { pdf ->
                if (pdf.pageCount < 1) return null
                pdf.openPage(0).use { page ->
                    val scale = minOf(1024f / page.width, 1300f / page.height, 2f)
                    val width = (page.width * scale).toInt().coerceAtLeast(1)
                    val height = (page.height * scale).toInt().coerceAtLeast(1)
                    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                    Canvas(bitmap).drawColor(Color.WHITE)
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    val jpeg = jpegForModel(bitmap)
                    bitmap.recycle()
                    return jpeg
                }
            }
        }
    }

    private fun jpegForModel(bitmap: Bitmap): ByteArray? {
        val ratio = minOf(1f, 1100f / maxOf(bitmap.width, bitmap.height))
        val source = if (ratio < 1f)
            Bitmap.createScaledBitmap(bitmap,
                (bitmap.width * ratio).toInt().coerceAtLeast(1),
                (bitmap.height * ratio).toInt().coerceAtLeast(1), true) else bitmap
        try {
            for (quality in listOf(78, 62, 45, 30)) {
                val output = ByteArrayOutputStream()
                source.compress(Bitmap.CompressFormat.JPEG, quality, output)
                if (output.size() <= 350_000) return output.toByteArray()
            }
            return null
        } finally {
            if (source !== bitmap) source.recycle()
        }
    }
}
