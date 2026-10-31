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
    // "Entrega" in a thesis schedule is not an instruction to export an
    // existing DOCX. A download/export verb must relate directly to Word.
    private val existingWord = Regex(
        """\b(?:descarg\w*|export\w*|guard\w*|entreg\w*|brind\w*|pasame|dame|mandame)""" +
            """(?:\s+[^\s]+){0,9}\s+(?:word|docx)\b"""
    )
    private val generate = Regex(
        """\b(?:crea\w*|gener\w*|elabor\w*|redact\w*|prepara\w*|haz|hace|hacer)\b"""
    )
    // A "como" inside research instructions is not a Word tutorial request.
    private val howToWord = Regex(
        """^[¿?\s]*(?:sky\s+)?(?:como|explicame como|dime como|tutorial|instrucciones|pasos)\b.*\b(?:word|docx)\b"""
    )

    /** "Necesito descargar el archivo Word" or "bríndame el Word". */
    fun wantsExistingWord(raw: String): Boolean {
        val s = normalize(raw)
        return s.length in 7..16000 && word.containsMatchIn(s) &&
            existingWord.containsMatchIn(s) && !howToWord.containsMatchIn(s)
    }

    /** "Crea un documento Word sobre..." with new content to generate first. */
    fun wantsNewWord(raw: String): Boolean {
        val s = normalize(raw)
        return s.length in 7..16000 && word.containsMatchIn(s) &&
            generate.containsMatchIn(s) && !existingWord.containsMatchIn(s) &&
            !howToWord.containsMatchIn(s)
    }
}
