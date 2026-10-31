package ni.sky.mobileagent

import android.graphics.Color
import android.graphics.Typeface
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.text.style.RelativeSizeSpan
import android.text.style.StyleSpan
import android.text.style.TypefaceSpan

/**
 * Stable Android-native presentation for the chat timeline.
 *
 * The complete original is NEVER changed, lost or passed to an external renderer.
 * Complex MathML, tables and code remain available in the isolated offline reader.
 * Only a bounded preview is rendered inline to prevent oversized TextViews.
 */
internal object SkyReadableAnswer {
    const val INLINE_ANSWER_CHARS = 12_000
    const val INLINE_QUESTION_CHARS = 3_000
    private const val MAX_PREVIEW_CHARS = 8_500

    data class Preview(val text: String, val needsReader: Boolean,
                       val rich: Boolean, val totalChars: Int)

    fun preview(original: String, mine: Boolean): Preview {
        val bound = if (mine) INLINE_QUESTION_CHARS else INLINE_ANSWER_CHARS
        val needsReader = original.length > bound
        val text = if (needsReader) {
            val proposed = original.take(if (mine) INLINE_QUESTION_CHARS else MAX_PREVIEW_CHARS)
            val lineEnd = proposed.lastIndexOf('\n')
            if (lineEnd > proposed.length / 2) proposed.take(lineEnd).trimEnd()
            else proposed.trimEnd()
        } else original
        val rich = !mine && (
            original.contains("**") || original.contains("\u0060\u0060\u0060") ||
            original.contains("\\(") || original.contains("\\[") ||
            original.contains("$$") || original.contains('|') ||
            original.lineSequence().any { it.trimStart().startsWith("#") }
        )
        return Preview(text, needsReader, rich, original.length)
    }

    /**
     * Native headings, lists, inline code and emphasis. Never interprets HTML,
     * executes scripts, fetches networks or claims Markdown/TeX support it lacks.
     */
    fun styled(preview: String): CharSequence {
        val result = SpannableStringBuilder()
        var codeBlock = false
        preview.replace("\r\n", "\n").replace('\r', '\n')
            .split('\n').forEachIndexed { index, raw ->
                if (index > 0) result.append("\n")
                val line = raw.trimEnd()
                if (line.trimStart().startsWith("\u0060\u0060\u0060")) {
                    codeBlock = !codeBlock
                    val start = result.length
                    result.append(if (codeBlock) "CÓDIGO" else "FIN DEL CÓDIGO")
                    result.setSpan(StyleSpan(Typeface.BOLD), start, result.length,
                        Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    result.setSpan(ForegroundColorSpan(Color.rgb(141, 223, 255)),
                        start, result.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    return@forEachIndexed
                }
                val heading = Regex("""^\s{0,3}(#{1,4})\s+(.+)$""").matchEntire(line)
                val bullet = Regex("""^\s*[-*]\s+(.+)$""").matchEntire(line)
                val rendered = when {
                    heading != null -> heading.groupValues[2]
                    bullet != null -> "•  " + bullet.groupValues[1]
                    else -> line
                }
                val lineStart = result.length
                if (codeBlock) {
                    result.append(rendered)
                    if (result.length > lineStart) {
                        result.setSpan(TypefaceSpan("monospace"), lineStart,
                            result.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                        result.setSpan(ForegroundColorSpan(Color.rgb(185, 227, 249)),
                            lineStart, result.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    }
                } else appendInline(result, rendered)
                if (heading != null && result.length > lineStart) {
                    val length = heading.groupValues[1].length
                    result.setSpan(StyleSpan(Typeface.BOLD), lineStart,
                        result.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    result.setSpan(RelativeSizeSpan(
                        when (length) { 1 -> 1.32f; 2 -> 1.2f; else -> 1.1f }),
                        lineStart, result.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    result.setSpan(ForegroundColorSpan(Color.rgb(156, 235, 255)),
                        lineStart, result.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            }
        return result
    }

    private fun appendInline(output: SpannableStringBuilder, line: String) {
        var i = 0
        while (i < line.length) {
            val marker = when {
                line.startsWith("**", i) -> "**"
                line.startsWith("__", i) -> "__"
                line[i] == '\u0060' -> "\u0060"
                else -> null
            }
            if (marker != null) {
                val end = line.indexOf(marker, i + marker.length)
                if (end > i + marker.length) {
                    val start = output.length
                    output.append(line.substring(i + marker.length, end))
                    if (marker == "\u0060") {
                        output.setSpan(TypefaceSpan("monospace"), start,
                            output.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                        output.setSpan(ForegroundColorSpan(Color.rgb(147, 227, 246)),
                            start, output.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    } else {
                        output.setSpan(StyleSpan(Typeface.BOLD), start,
                            output.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    }
                    i = end + marker.length
                    continue
                }
            }
            output.append(line[i])
            i++
        }
    }
}
