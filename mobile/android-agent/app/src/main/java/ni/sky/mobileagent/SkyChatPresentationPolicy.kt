package ni.sky.mobileagent

/**
 * Native chat presentation rules shared by user and SKY message cards.
 * No network, permissions, private content logging or background work.
 */
internal object SkyChatPresentationPolicy {
    const val PREVIEW_CHARS = 9000
    const val PREVIEW_HEAD_CHARS = 6800

    /** Newlines alone must NEVER create a WebView with a fixed 56dp height. */
    fun requiresScientificRenderer(text: String): Boolean =
        text.contains("\\[") || text.contains("\\(") ||
            text.contains("$$") || text.contains("**") ||
            text.contains("```") ||
            text.lineSequence().any { line ->
                val trimmed = line.trimStart()
                trimmed.startsWith("# ") || trimmed.startsWith("## ") ||
                    (trimmed.startsWith("|") && trimmed.count { it == '|' } >= 2)
            }

    fun preview(text: String): String = if (text.length > PREVIEW_CHARS)
        text.take(PREVIEW_HEAD_CHARS) +
            "\n\nVista previa. Elegí «Leer mensaje completo» para consultar todo el texto."
    else text

    fun hasFullViewer(text: String) = text.length > PREVIEW_CHARS
}
