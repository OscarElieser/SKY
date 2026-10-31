package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * Intent only: never interprets a cloud answer as authority to save files.
 * Native DOCX creation stays in the Activity through Android's document picker.
 */
object SkyWordExportIntent {
    private fun normalize(value: String): String = Normalizer.normalize(
        value.lowercase(Locale.ROOT), Normalizer.Form.NFD
    ).replace(Regex("""\p{M}+"""), "").replace(Regex("""\s+"""), " ").trim()

    private val word = Regex("""\b(?:word|docx)\b""")
    private val existing = Regex(
        """\b(?:descarg\w*|export\w*|guard\w*|entreg\w*|brind\w*|pasame|dame|mandame)\b"""
    )
    private val generate = Regex(
        """\b(?:crea\w*|gener\w*|elabor\w*|redact\w*|prepara\w*|haz|hace|hacer)\b"""
    )
    private val howTo = Regex("""\b(?:como|tutorial|instrucciones|pasos)\b""")

    /** "Necesito descargar el archivo Word" or "bríndame el Word". */
    fun wantsExistingWord(raw: String): Boolean {
        val s = normalize(raw)
        return s.length in 7..16000 && word.containsMatchIn(s) &&
            existing.containsMatchIn(s) && !howTo.containsMatchIn(s)
    }

    /** "Crea un documento Word sobre..." with new content to generate first. */
    fun wantsNewWord(raw: String): Boolean {
        val s = normalize(raw)
        return s.length in 7..16000 && word.containsMatchIn(s) &&
            generate.containsMatchIn(s) && !existing.containsMatchIn(s) &&
            !howTo.containsMatchIn(s)
    }
}
