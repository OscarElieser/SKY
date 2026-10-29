package ni.sky.mobileagent

import java.io.OutputStream

/**
 * Exportación local de texto editable; no simula un archivo DOCX ni una
 * integración oficial con Canva, Gamma, Copilot o Microsoft Office.
 */
object SkyResponseExport {
    enum class Format(val label: String, val mime: String, val extension: String) {
        MARKDOWN("Markdown editable", "text/markdown", "md"),
        HTML("Documento HTML editable", "text/html", "html")
    }

    fun filename(entry: SkyConversationArchive.Entry, format: Format): String {
        val base = entry.title.replace(Regex("""[^\p{L}\p{N}._-]+"""), "-")
            .trim('-', '.', '_').take(48).ifBlank { "Respuesta-SKY" }
        return "SKY-" + base + "." + format.extension
    }

    fun escapeHtml(text: String): String = buildString(text.length) {
        text.forEach { c ->
            append(when (c) {
                '&' -> "&amp;"
                '<' -> "&lt;"
                '>' -> "&gt;"
                '"' -> "&quot;"
                '\'' -> "&#39;"
                else -> c.toString()
            })
        }
    }

    fun render(entry: SkyConversationArchive.Entry, format: Format): String {
        val time = entry.localTime()
        return when (format) {
            Format.MARKDOWN -> buildString {
                append("# ").append(entry.title.replace("\n", " ")).append("\n\n")
                append("**Fecha:** ").append(time).append("  \n")
                append("**Motor:** ").append(entry.engine).append("\n\n")
                append("## Consulta\n\n").append(entry.question).append("\n\n")
                append("## Respuesta de SKY IA\n\n").append(entry.answer).append("\n")
            }
            Format.HTML -> {
                val title = escapeHtml(entry.title)
                val question = escapeHtml(entry.question)
                val answer = escapeHtml(entry.answer)
                val engine = escapeHtml(entry.engine)
                """<!doctype html>
<html lang="es-NI"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title · SKY IA</title>
<style>
body{font-family:Arial,Helvetica,sans-serif;background:#f4f7fa;color:#16253c;
margin:0 auto;max-width:880px;padding:30px;line-height:1.65}
article{background:white;padding:36px;border:1px solid #dde4ef;border-radius:12px}
h1,h2{color:#104c87}small{color:#52637e}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}
@media print{body{background:white;padding:0}article{border:0;padding:0}}
</style></head>
<body><article><h1>$title</h1><small>SKY IA · $time · $engine</small>
<h2>Consulta</h2><pre>$question</pre>
<h2>Respuesta</h2><pre>$answer</pre>
</article></body></html>"""
            }
        }
    }

    fun write(output: OutputStream, entry: SkyConversationArchive.Entry, format: Format): Int {
        val bytes = render(entry, format).toByteArray(Charsets.UTF_8)
        output.write(bytes)
        return bytes.size
    }
}
