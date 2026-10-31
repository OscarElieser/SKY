package ni.sky.mobileagent

import android.text.Spanned
import android.text.style.StyleSpan
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Checks actual Android typography instead of relying only on plain JVM logic. */
@RunWith(AndroidJUnit4::class)
class SkyReadableAnswerRuntimeTest {
    @Test fun nativeScientificAnswerShowsFullTextAndReadableHeadings() {
        val original = "# Resultados\n\n**Objetivo:** enseñar química.\n\n" +
            "- Reactivo uno\n- Reactivo dos"
        val displayed = SkyReadableAnswer.styled(original)
        assertTrue(displayed.toString().contains("Resultados"))
        assertTrue(displayed.toString().contains("Objetivo: enseñar química"))
        assertTrue(displayed.toString().contains("•  Reactivo uno"))
        assertFalse(displayed.toString().contains("**Objetivo:**"))
        val spans = displayed as Spanned
        assertTrue(spans.getSpans(0, spans.length, StyleSpan::class.java).isNotEmpty())
    }

    @Test fun longerAnswersKeepOriginalBytesForReaderAndCopying() {
        val answer = "Capítulo con caracteres áéíóú y fórmulas.\n".repeat(450)
        val preview = SkyReadableAnswer.preview(answer, mine = false)
        assertTrue(preview.needsReader)
        assertTrue(answer.length > preview.text.length)
        assertTrue(answer.endsWith("fórmulas.\n"))
    }
}
