package ni.sky.mobileagent

/** Offline, escaped Markdown and MathML subset. Input is never executable HTML. */
internal object SkyScientificMarkup {
    private fun escape(s: String): String = buildString {
        for (c in s) append(when (c) {
            '&' -> "&amp;"; '<' -> "&lt;"; '>' -> "&gt;"
            '"' -> "&quot;"; '\'' -> "&#39;"; else -> c.toString()
        })
    }

    private val names = mapOf(
        "alpha" to "α", "beta" to "β", "gamma" to "γ", "delta" to "δ",
        "theta" to "θ", "lambda" to "λ", "mu" to "μ", "pi" to "π",
        "sigma" to "σ", "omega" to "ω", "Delta" to "Δ", "Omega" to "Ω",
        "cdot" to "·", "times" to "×", "pm" to "±", "div" to "÷",
        "neq" to "≠", "leq" to "≤", "geq" to "≥", "approx" to "≈",
        "infty" to "∞", "partial" to "∂", "nabla" to "∇",
        "sum" to "∑", "int" to "∫", "rightarrow" to "→", "to" to "→",
        "leftarrow" to "←", "leftrightarrow" to "↔",
        "rightleftharpoons" to "⇌", "equiv" to "≡", "propto" to "∝",
        "degree" to "°"
    )

    private class Math(private val src: String) {
        private var pos = 0
        private fun spaces() { while (pos < src.length && src[pos].isWhitespace()) pos++ }
        private fun rawGroup(): String {
            spaces()
            if (pos >= src.length || src[pos] != '{') return ""
            pos++
            val begin = pos
            var depth = 1
            while (pos < src.length && depth > 0) {
                if (src[pos] == '{') depth++
                if (src[pos] == '}') depth--
                pos++
            }
            return escape(src.substring(begin, if (depth == 0) pos - 1 else pos))
        }
        private fun group(): String {
            spaces()
            if (pos < src.length && src[pos] == '{') {
                pos++
                val v = seq('}')
                if (pos < src.length && src[pos] == '}') pos++
                return "<mrow>" + v + "</mrow>"
            }
            return atom()
        }
        private fun atom(): String {
            if (pos >= src.length) return ""
            val ch = src[pos++]
            if (ch == '{') {
                val v = seq('}')
                if (pos < src.length && src[pos] == '}') pos++
                return "<mrow>" + v + "</mrow>"
            }
            if (ch == '\\') {
                val start = pos
                while (pos < src.length && src[pos].isLetter()) pos++
                // TeX spacing commands are backslash plus a punctuation character.
                if (start == pos && pos < src.length) {
                    val punctuation = src[pos++]
                    if (punctuation in listOf(',', ';', ':', '!', ' ')) {
                        return "<mspace width=\"0.25em\"/>"
                    }
                    return "<mo>" + escape(punctuation.toString()) + "</mo>"
                }
                val name = src.substring(start, pos)
                return when (name) {
                    "frac", "dfrac", "tfrac" ->
                        "<mfrac><mrow>" + group() + "</mrow><mrow>" + group() + "</mrow></mfrac>"
                    "sqrt" -> "<msqrt>" + group() + "</msqrt>"
                    "text" -> "<mtext>" + rawGroup() + "</mtext>"
                    "mathrm", "operatorname", "mathbf" ->
                        "<mstyle mathvariant=\"" + (if (name == "mathbf") "bold" else "normal") +
                            "\">" + group() + "</mstyle>"
                    "left", "right" -> atom()
                    else -> if (names.containsKey(name)) "<mo>" + escape(names.getValue(name)) + "</mo>"
                        else "<mtext>" + escape("\\" + name) + "</mtext>"
                }
            }
            if (ch.isDigit()) {
                val start = pos - 1
                while (pos < src.length && (src[pos].isDigit() || src[pos] == '.')) pos++
                return "<mn>" + escape(src.substring(start, pos)) + "</mn>"
            }
            if (ch.isLetter()) {
                val start = pos - 1
                while (pos < src.length && src[pos].isLetter()) pos++
                return "<mi>" + escape(src.substring(start, pos)) + "</mi>"
            }
            return "<mo>" + escape(ch.toString()) + "</mo>"
        }
        private fun seq(until: Char? = null): String = buildString {
            while (pos < src.length && (until == null || src[pos] != until)) {
                if (src[pos].isWhitespace()) {
                    pos++; append("<mspace width=\"0.2em\"/>"); continue
                }
                var base = atom()
                var low: String? = null
                var high: String? = null
                while (pos < src.length && (src[pos] == '_' || src[pos] == '^')) {
                    val op = src[pos++]
                    if (op == '_') low = group() else high = group()
                }
                base = when {
                    low != null && high != null -> "<msubsup>" + base + low + high + "</msubsup>"
                    low != null -> "<msub>" + base + low + "</msub>"
                    high != null -> "<msup>" + base + high + "</msup>"
                    else -> base
                }
                append(base)
            }
        }
        fun render(): String = seq()
    }

    fun mathMl(source: String, block: Boolean = false): String {
        if (source.length > 5000) return "<code>" + escape(source) + "</code>"
        return "<math xmlns=\"http://www.w3.org/1998/Math/MathML\" display=\"" +
            (if (block) "block" else "inline") + "\"><mrow>" +
            Math(source).render() + "</mrow></math>"
    }

    private fun inline(line: String): String = buildString {
        var i = 0
        while (i < line.length) {
            val mathEnd = when {
                line.startsWith("\\(", i) -> "\\)" to 2
                line.startsWith("$$", i) -> "$$" to 2
                line[i] == '$' && i + 1 < line.length && !line[i + 1].isWhitespace() -> "$" to 1
                else -> null
            }
            if (mathEnd != null) {
                val end = line.indexOf(mathEnd.first, i + mathEnd.second)
                if (end > i + mathEnd.second) {
                    append(mathMl(line.substring(i + mathEnd.second, end)))
                    i = end + mathEnd.first.length
                    continue
                }
            }
            val marker = when {
                line.startsWith("**", i) -> "**"
                line.startsWith("__", i) -> "__"
                line[i].code == 96 -> "\u0060"
                line[i] == '*' -> "*"
                else -> null
            }
            if (marker != null) {
                val end = line.indexOf(marker, i + marker.length)
                if (end > i + marker.length) {
                    val tag = if (marker == "**" || marker == "__") "strong" else
                        if (marker == "*") "em" else "code"
                    append("<" + tag + ">" + escape(line.substring(i + marker.length, end)) +
                        "</" + tag + ">")
                    i = end + marker.length
                    continue
                }
            }
            append(escape(line[i].toString()))
            i++
        }
    }

    fun toHtml(raw: String): String {
        val lines = raw.replace("\r\n", "\n").replace('\r', '\n').lines()
        val content = StringBuilder()
        var code = false
        var i = 0
        while (i < lines.size) {
            val line = lines[i].trim()
            if (line.startsWith("\u0060\u0060\u0060")) {
                content.append(if (code) "</code></pre>" else "<pre><code>")
                code = !code; i++; continue
            }
            if (code) { content.append(escape(lines[i])).append('\n'); i++; continue }
            val open = when {
                line.startsWith("\\[") -> "\\["
                line.startsWith("$$") -> "$$"
                else -> null
            }
            if (open != null) {
                val close = if (open == "$$") "$$" else "\\]"
                val expression = StringBuilder(line.removePrefix(open))
                while (!expression.contains(close) && i + 1 < lines.size) {
                    i++
                    expression.append(' ').append(lines[i].trim())
                }
                if (expression.contains(close)) {
                    content.append("<div class=\"formula\">")
                        .append(mathMl(expression.toString().substringBefore(close), true))
                        .append("</div>")
                } else content.append("<p>").append(escape(open + expression)).append("</p>")
                i++; continue
            }
            // Markdown pipe tables: keep each cell as escaped data, never HTML.
            if (line.startsWith("|") && line.count { it == '|' } >= 2) {
                val rows = mutableListOf<List<String>>()
                var headerRow = false
                while (i < lines.size && lines[i].trim().startsWith("|")) {
                    val cells = lines[i].trim().trim('|').split('|').map { it.trim() }
                    val divider = cells.isNotEmpty() && cells.all {
                        it.matches(Regex("^:?-{3,}:?$"))
                    }
                    if (divider) {
                        if (rows.size == 1) headerRow = true
                    } else rows.add(cells)
                    i++
                }
                content.append("<div class=\"table-scroll\"><table>")
                rows.forEachIndexed { row, cells ->
                    content.append("<tr>")
                    cells.forEach { cell ->
                        val tag = if (headerRow && row == 0) "th" else "td"
                        content.append("<").append(tag).append(">")
                            .append(inline(cell)).append("</").append(tag).append(">")
                    }
                    content.append("</tr>")
                }
                content.append("</table></div>")
                continue
            }
            val heading = Regex("^(#{1,6})\\s+(.+)$").find(line)
            when {
                line.isBlank() -> content.append("<div class=\"space\"></div>")
                Regex("^[-*_]{3,}$").matches(line) -> content.append("<hr/>")
                heading != null -> {
                    val h = heading.groupValues[1].length.coerceAtMost(4)
                    content.append("<h").append(h).append(">")
                        .append(inline(heading.groupValues[2]))
                        .append("</h").append(h).append(">")
                }
                line.startsWith("- ") || line.startsWith("* ") ||
                    Regex("^\\d+[.)]\\s+").containsMatchIn(line) ->
                    content.append("<div class=\"bullet\">• ")
                        .append(inline(line.replaceFirst(Regex("^(?:[-*]|\\d+[.)])\\s+"), "")))
                        .append("</div>")
                line.startsWith("> ") -> content.append("<blockquote>")
                    .append(inline(line.drop(2))).append("</blockquote>")
                else -> content.append("<p>").append(inline(line)).append("</p>")
            }
            i++
        }
        if (code) content.append("</code></pre>")
        return """<!doctype html><html lang="es"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>:root{color-scheme:dark}*{box-sizing:border-box}
html,body{padding:0;margin:0;background:transparent;color:#f3f7ff}
body{font:16px/1.65 system-ui,Roboto,sans-serif;padding:13px 15px;overflow-wrap:anywhere}
p{margin:0 0 10px}p:last-child{margin-bottom:0}
h1,h2,h3,h4{line-height:1.35;color:#b2edff;margin:13px 0 7px;font-weight:750}
h1{font-size:22px}h2{font-size:20px}h3{font-size:18px}h4{font-size:16px}
strong{font-weight:750;color:#fff}.bullet{padding-left:14px;text-indent:-10px;margin:5px 0}
.space{height:7px}.formula{background:#162842;border:1px solid #4a7093;border-radius:12px;
padding:12px;margin:10px 0;overflow-x:auto;text-align:center}
math{color:#fff;font-size:1.13em}math[display=block]{font-size:1.25em}
pre{padding:12px;background:#101d35;border:1px solid #365273;border-radius:10px;
white-space:pre;overflow-x:auto}
code{font:0.93em ui-monospace,monospace;color:#95e8ff}
blockquote{border-left:3px solid #80cbff;padding:6px 10px;color:#dceaff;margin:8px 0}
hr{border:0;border-top:1px solid #4b6080;margin:12px 0}
.table-scroll{overflow-x:auto;margin:12px 0;border:1px solid #426080;border-radius:10px}
table{border-collapse:collapse;min-width:100%;font-size:14px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #34516c}
th{background:#203c59;color:#acecff;font-weight:700}
</style></head><body>""" + content + "</body></html>"
    }
}
