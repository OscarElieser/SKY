package ni.sky.mobileagent

import java.io.OutputStream
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Creación local de paquetes Office Open XML reales (.docx y .pptx).
 * Texto y figuras editables, sin acceso a servicios externos ni macros.
 */
object SkyNativeOfficeExport {
    enum class Format(val label: String, val mime: String, val extension: String) {
        WORD("Word editable · DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
        POWERPOINT("PowerPoint editable · PPTX", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
        EXCEL("Excel editable · XLSX", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx")
    }

    const val CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"
    const val RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
    const val DOCRELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    const val WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    const val DRAW = "http://schemas.openxmlformats.org/drawingml/2006/main"
    const val PRESENT = "http://schemas.openxmlformats.org/presentationml/2006/main"

    fun escapeXml(value: String): String = buildString(value.length) {
        var i = 0
        while (i < value.length) {
            val cp = Character.codePointAt(value, i)
            i += Character.charCount(cp)
            val valid = cp == 9 || cp == 10 || cp == 13 ||
                cp in 0x20..0xD7FF || cp in 0xE000..0xFFFD ||
                cp in 0x10000..0x10FFFF
            if (!valid) continue
            when (cp) {
                38 -> append("&amp;")
                60 -> append("&lt;")
                62 -> append("&gt;")
                34 -> append("&quot;")
                39 -> append("&apos;")
                else -> appendCodePoint(cp)
            }
        }
    }

    fun filename(entry: SkyConversationArchive.Entry, format: Format): String =
        "SKY-" + entry.title.replace(Regex("""[^\p{L}\p{N}._-]+"""), "-")
            .trim('-', '.', '_').take(50).ifBlank { "Documento" } + "." + format.extension

    fun write(output: OutputStream, entry: SkyConversationArchive.Entry, format: Format) {
        require(entry.title.length < 400 && entry.answer.length <= 100_000) {
            "La respuesta es demasiado extensa para exportarse."
        }
        ZipOutputStream(output).use { zip ->
            when (format) {
                Format.WORD -> SkyNativeWord.write(zip, entry)
                Format.POWERPOINT -> SkyNativePowerPoint.write(zip, entry)
                Format.EXCEL -> SkyNativeExcel.write(zip, entry)
            }
        }
    }

    fun zipPut(zip: ZipOutputStream, path: String, xml: String) {
        zip.putNextEntry(ZipEntry(path))
        zip.write(xml.toByteArray(Charsets.UTF_8))
        zip.closeEntry()
    }

    fun core(entry: SkyConversationArchive.Entry): String {
        val title = escapeXml(entry.title)
        val created = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
            .withZone(ZoneOffset.UTC).format(Instant.ofEpochMilli(entry.createdAt.coerceAtLeast(0)))
        return """<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
xmlns:dc="http://purl.org/dc/elements/1.1/"
xmlns:dcterms="http://purl.org/dc/terms/"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>$title</dc:title><dc:creator>SKY IA Android</dc:creator>
<cp:lastModifiedBy>SKY IA Android</cp:lastModifiedBy>
<dcterms:created xsi:type="dcterms:W3CDTF">$created</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">$created</dcterms:modified>
</cp:coreProperties>"""
    }
}
