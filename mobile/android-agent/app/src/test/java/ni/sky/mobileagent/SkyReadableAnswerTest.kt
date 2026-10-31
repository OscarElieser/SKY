package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyReadableAnswerTest {
    @Test fun normalAcademicAnswerIsNeverVisuallyTruncated() {
        val answer = "# Resultados\n\n**Objetivo:** " + "Explicación científica. ".repeat(150)
        val preview = SkyReadableAnswer.preview(answer, mine = false)
        assertEquals(answer, preview.text)
        assertFalse(preview.needsReader)
        assertTrue(preview.rich)
        assertEquals(answer.length, preview.totalChars)
    }

    @Test fun shortPlainTextNeedsNoExtraReader() {
        val preview = SkyReadableAnswer.preview("Hola, ¿cómo estás?", mine = false)
        assertEquals("Hola, ¿cómo estás?", preview.text)
        assertFalse(preview.needsReader)
        assertFalse(preview.rich)
    }

    @Test fun longThesisProvidesHonestPreviewAndAlwaysKeepsOriginalUntouched() {
        val thesis = "# Investigación\n" + "Capítulo académico completo.\n".repeat(3500)
        val preview = SkyReadableAnswer.preview(thesis, mine = false)
        assertTrue(preview.needsReader)
        assertTrue(preview.text.length <= 8_500)
        assertTrue(preview.text.startsWith("# Investigación"))
        assertTrue(preview.totalChars > 60_000)
        assertTrue(thesis.endsWith("Capítulo académico completo.\n"))
        assertEquals(thesis.length, preview.totalChars)
    }

    @Test fun veryLongUserPromptHasItsOwnReaderWithoutChangingTheSubmission() {
        val question = "Mi instrucción " + "contexto ".repeat(4200)
        val preview = SkyReadableAnswer.preview(question, mine = true)
        assertTrue(preview.needsReader)
        assertTrue(preview.text.length <= SkyReadableAnswer.INLINE_QUESTION_CHARS)
        assertEquals(question.length, preview.totalChars)
        assertTrue(question.endsWith("contexto "))
    }

    @Test fun scientificFormattingActivatesFullOfflineReader() {
        val examples = listOf(
            "Ecuación: \\[x^2+1=0\\]",
            "Tabla:\n| Variable | Unidad |\n|---|---|\n| a | m/s |",
            "```kotlin\nval x = 1\n```"
        )
        examples.forEach {
            val preview = SkyReadableAnswer.preview(it, mine = false)
            assertTrue("Debe ofrecer lectura de fórmulas y tablas: $it", preview.rich)
            assertFalse(preview.needsReader)
        }
    }
}
