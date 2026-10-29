package ni.sky.mobileagent

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SkyResponseExportTest {
    private val entry = SkyConversationArchive.Entry(
        1L, "Informe de investigación", "¿Qué significa <b>ejemplo</b>?",
        "Texto <script>alert('x')</script> & más", "Gemini", 1720000000000L
    )

    @Test fun htmlEscapesUntrustedMarkup() {
        val html = SkyResponseExport.render(entry, SkyResponseExport.Format.HTML)
        assertTrue(html.contains("&lt;script&gt;"))
        assertFalse(html.contains("<script>"))
        assertTrue(html.contains("&amp; más"))
        assertTrue(html.contains("lang=\"es-NI\""))
    }

    @Test fun markdownContainsQuestionAndAnswer() {
        val md = SkyResponseExport.render(entry, SkyResponseExport.Format.MARKDOWN)
        assertTrue(md.contains("## Consulta"))
        assertTrue(md.contains("## Respuesta de SKY IA"))
        assertTrue(md.contains(entry.answer))
    }

    @Test fun filenameCannotContainPathSeparator() {
        val filename = SkyResponseExport.filename(entry, SkyResponseExport.Format.HTML)
        assertTrue(filename.startsWith("SKY-"))
        assertTrue(filename.endsWith(".html"))
        assertFalse(filename.contains("/"))
    }
}
