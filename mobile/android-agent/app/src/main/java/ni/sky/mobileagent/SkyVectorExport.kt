package ni.sky.mobileagent

import java.io.OutputStream

/**
 * Infografía vectorial SVG, con texto y objetos editables (no imagen raster).
 * No ejecuta scripts, no usa recursos externos, no suplanta a Canva.
 */
object SkyVectorExport {
    const val MIME = "image/svg+xml"
    const val EXTENSION = "svg"

    fun filename(entry: SkyConversationArchive.Entry): String =
        "SKY-Visual-" + entry.title.replace(Regex("""[^\p{L}\p{N}._-]+"""), "-")
            .trim('-', '.', '_').take(46).ifBlank { "Resumen" } + ".svg"

    private fun wrap(text: String, max: Int, rows: Int): List<String> {
        val lines = mutableListOf<String>()
        var current = StringBuilder()
        text.replace(Regex("""\s+"""), " ").trim().split(" ").forEach { word ->
            if (current.isNotEmpty() && current.length + word.length + 1 > max) {
                lines.add(current.toString())
                current = StringBuilder()
            }
            if (current.isNotEmpty()) current.append(' ')
            current.append(word.take(max))
        }
        if (current.isNotEmpty()) lines.add(current.toString())
        return lines.take(rows)
    }

    private fun textLines(text: String, x: Int, y: Int, size: Int, max: Int,
                          rows: Int, color: String, weight: Int = 400): String =
        buildString {
            val list = wrap(text, max, rows)
            append("<text x=\"").append(x).append("\" y=\"").append(y)
                .append("\" fill=\"").append(color).append("\" font-family=\"Arial, sans-serif\"")
                .append(" font-size=\"").append(size).append("\" font-weight=\"")
                .append(weight).append("\">")
            list.forEachIndexed { index, value ->
                append("<tspan x=\"").append(x).append("\" dy=\"")
                    .append(if (index == 0) 0 else size + 9).append("\">")
                    .append(SkyNativeOfficeExport.escapeXml(value)).append("</tspan>")
            }
            append("</text>")
        }

    fun render(entry: SkyConversationArchive.Entry): String {
        val snippets = entry.answer.lines().map { it.trim() }
            .filter { it.isNotBlank() && !it.startsWith("#") }
            .map { it.removePrefix("- ").removePrefix("* ").trim() }
            .take(4).ifEmpty { listOf("Sin ideas suficientes para una infografía.") }
        return buildString {
            append("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900"
viewBox="0 0 1600 900" role="img" aria-label="Resumen visual creado por SKY IA">
<defs>
<linearGradient id="sky-bg" x1="0" x2="1" y1="0" y2="1">
<stop offset="0%" stop-color="#07152D"/>
<stop offset="100%" stop-color="#173B60"/>
</linearGradient>
</defs>
<rect width="1600" height="900" fill="url(#sky-bg)"/>
<circle cx="1478" cy="70" r="230" fill="#114C73" opacity="0.20"/>
<circle cx="1350" cy="115" r="120" fill="none" stroke="#37CFF6" opacity="0.35" stroke-width="3"/>
<circle cx="1480" cy="85" r="12" fill="#37CFF6" opacity="0.75"/>
<line x1="1340" y1="110" x2="1480" y2="85" stroke="#37CFF6" opacity="0.35" stroke-width="3"/>
<text x="80" y="85" fill="#80E6FF" font-family="Arial, sans-serif" font-size="28"
font-weight="700" letter-spacing="5">SKY IA  /  RESUMEN VISUAL</text>
<rect x="80" y="109" width="148" height="7" rx="4" fill="#34CFF1"/>
""")
            append(textLines(entry.title, 80, 192, 61, 38, 2, "#F4FAFF", 700))
            append("""<text x="82" y="332" fill="#A6CCE2" font-family="Arial, sans-serif"
font-size="23">Contenido organizado a partir de una respuesta de SKY IA</text>""")
            snippets.forEachIndexed { index, item ->
                val x = 80 + (index % 2) * 755
                val y = 375 + (index / 2) * 218
                append("<g id=\"bloque-").append(index + 1).append("\">")
                append("<rect x=\"").append(x).append("\" y=\"").append(y)
                    .append("\" width=\"690\" height=\"190\" rx=\"23\" fill=\"#122947\"")
                append(" stroke=\"#2C5776\" stroke-width=\"2\"/>")
                append("<rect x=\"").append(x + 27).append("\" y=\"").append(y + 28)
                    .append("\" width=\"60\" height=\"48\" rx=\"12\" fill=\"#155779\"/>")
                append(textLines((index + 1).toString().padStart(2, '0'),
                    x + 38, y + 63, 24, 3, 1, "#7CE3FA", 700))
                append(textLines(item, x + 104, y + 56, 27, 42, 3, "#F2F8FF"))
                append("</g>")
            }
            append("""<line x1="80" y1="840" x2="1520" y2="840"
stroke="#376584" stroke-width="2"/>
""")
            append(textLines("SKY IA · " + entry.localTime() +
                " · Formas y texto vectoriales editables", 82, 873, 20, 125, 1, "#AAC4D8"))
            append("</svg>")
        }
    }

    fun write(output: OutputStream, entry: SkyConversationArchive.Entry): Int {
        val bytes = render(entry).toByteArray(Charsets.UTF_8)
        output.write(bytes)
        return bytes.size
    }
}
