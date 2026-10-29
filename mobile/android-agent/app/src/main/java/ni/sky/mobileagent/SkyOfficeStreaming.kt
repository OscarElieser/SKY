package ni.sky.mobileagent

import android.content.ContentResolver
import android.net.Uri
import android.util.Xml
import org.xmlpull.v1.XmlPullParser
import java.io.FilterInputStream
import java.io.InputStream
import java.util.Locale
import java.util.zip.ZipInputStream

/**
 * DOCX/XLSX/PPTX grandes: lectura XML por flujo sin descomprimir en RAM.
 * Es una extracción parcial (texto/valores), no interpretación de objetos gráficos.
 */
object SkyOfficeStreaming {
    private const val MAX_CHARS = 14000
    private const val MAX_XML_UNCOMPRESSED = 15L * 1024L * 1024L

    private class Metered(input: InputStream, private val max: Long) : FilterInputStream(input) {
        private var bytesRead = 0L
        fun count(): Long = bytesRead
        override fun read(): Int {
            val value = super.read()
            if (value >= 0) bytesRead++
            require(bytesRead <= max) { "Documento Office con XML demasiado extenso." }
            return value
        }
        override fun read(b: ByteArray, off: Int, len: Int): Int {
            // FilterInputStream.read(byte[],off,len) ya delega directamente.
            val n = super.read(b, off, len)
            if (n > 0) bytesRead += n
            require(bytesRead <= max) { "Documento Office con XML demasiado extenso." }
            return n
        }
        override fun close() {} // ZipInputStream debe continuar con el siguiente XML.
    }

    fun preview(resolver: ContentResolver, item: SkyAttachmentBatch.Item): String {
        require(item.kind == SkyAttachmentBatch.Kind.OFFICE)
        val suffix = item.name.substringAfterLast('.', "").lowercase(Locale.ROOT)
        val out = StringBuilder()
        var entries = 0
        var scanned = 0L
        resolver.openInputStream(item.uri)?.use { stream ->
            ZipInputStream(stream).use { zip ->
                while (true) {
                    val entry = zip.nextEntry ?: break
                    val filename = entry.name
                    val selected = when (suffix) {
                        "docx" -> filename == "word/document.xml"
                        "xlsx" -> filename == "xl/sharedStrings.xml" ||
                            Regex("""xl/worksheets/sheet[0-9]+\.xml""").matches(filename)
                        "pptx" -> Regex("""ppt/slides/slide[0-9]+\.xml""").matches(filename)
                        else -> false
                    }
                    if (selected) {
                        entries++
                        // Limitar el tamaño expandido para prevenir ZIP bombs.
                        val remaining = MAX_XML_UNCOMPRESSED - scanned
                        if (remaining <= 0 || entries > 40) break
                        val counting = Metered(zip, remaining)
                        val parser = Xml.newPullParser().apply {
                            setInput(counting, "UTF-8")
                        }
                        var event = parser.eventType
                        out.append("\n[").append(filename.take(85)).append("]\n")
                        while (event != XmlPullParser.END_DOCUMENT && out.length < MAX_CHARS) {
                            if (event == XmlPullParser.START_TAG) {
                                val tag = parser.name.substringAfter(':')
                                if (tag == "t" || (suffix == "xlsx" && tag == "v")) {
                                    val value = parser.nextText().trim()
                                    if (value.isNotEmpty()) out.append(value).append(' ')
                                } else if (tag == "p" || tag == "row") out.append('\n')
                            }
                            event = parser.next()
                        }
                        if (out.length >= MAX_CHARS) break
                        scanned += counting.count()
                    }
                    zip.closeEntry()
                }
            }
        } ?: throw IllegalStateException("No se pudo leer el documento Office.")
        require(out.isNotBlank()) { "El documento no contiene texto Office legible." }
        return out.toString().take(MAX_CHARS)
    }
}
