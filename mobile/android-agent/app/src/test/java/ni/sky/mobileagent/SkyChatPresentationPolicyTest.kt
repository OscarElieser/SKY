package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyChatPresentationPolicyTest {
    @Test fun plainMultilineSystemAndUserMessagesNeverNeedWebView() {
        val setupWarning = "Para usar tu SKY API primero autorizá el chat del servidor HTTPS\ndesde Ajustes."
        val longPlain = "Explicación precisa.\n".repeat(50)
        assertFalse(SkyChatPresentationPolicy.requiresScientificRenderer(setupWarning))
        assertFalse(SkyChatPresentationPolicy.requiresScientificRenderer(longPlain))
        assertEquals(setupWarning, SkyChatPresentationPolicy.preview(setupWarning))
        assertFalse(SkyChatPresentationPolicy.hasFullViewer(setupWarning))
    }

    @Test fun structuredAcademicContentUsesOfflineRichRenderer() {
        for (sample in listOf(
            "# Introducción\n\nAnálisis",
            "E = \\(mc^2\\)",
            "La fórmula es \\[x^2 + y^2\\]",
            "**Resumen académico**",
            "|A|B|\n|---|---|",
            "```kotlin\nprintln(1)\n```"
        )) {
            assertTrue(sample, SkyChatPresentationPolicy.requiresScientificRenderer(sample))
        }
    }

    @Test fun longMessagesAreExplicitlyMarkedWhileFullTextIsPreservedInArchive() {
        val original = "Inicio. " + "a".repeat(10_000) + " Final."
        val preview = SkyChatPresentationPolicy.preview(original)
        assertTrue(SkyChatPresentationPolicy.hasFullViewer(original))
        assertTrue(preview.length < original.length)
        assertTrue(preview.contains("Vista previa"))
        assertTrue(preview.contains("Leer mensaje completo"))
        assertTrue(original.endsWith("Final.")) // full viewer receives original, not preview
    }

    @Test fun shortMultilineTextHasNoArtificialPreviewOrTruncation() {
        val original = "Línea uno\nLínea dos\nLínea tres"
        assertEquals(original, SkyChatPresentationPolicy.preview(original))
        assertFalse(SkyChatPresentationPolicy.hasFullViewer(original))
    }
}
