package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.w3c.dom.Document
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.zip.ZipInputStream
import javax.xml.XMLConstants
import javax.xml.parsers.DocumentBuilderFactory

class SkyNativeOfficeExportTest {
    private val entry = SkyConversationArchive.Entry(
        9L, "Proyecto SKY & Nicaragua", "Explica <scripts> & conceptos",
        """
        # Objetivos
        - Crear documento editable.
        - Proteger <script> & caracteres especiales.
        ## Plan de trabajo
        Primera actividad: análisis de un documento.
        Segunda actividad: revisión de resultados.
        """.trimIndent(),
        "Gemini", 1780000000000L
    )

    private fun parts(format: SkyNativeOfficeExport.Format): Map<String, String> {
        val buffer = ByteArrayOutputStream()
        SkyNativeOfficeExport.write(buffer, entry, format)
        val result = linkedMapOf<String, String>()
        ZipInputStream(ByteArrayInputStream(buffer.toByteArray())).use { zip ->
            while (true) {
                val item = zip.nextEntry ?: break
                result[item.name] = zip.readBytes().toString(Charsets.UTF_8)
                zip.closeEntry()
            }
        }
        return result
    }

    private fun parseXml(xml: String): Document {
        val factory = DocumentBuilderFactory.newInstance()
        factory.isNamespaceAware = true
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true)
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
        return factory.newDocumentBuilder().parse(ByteArrayInputStream(xml.toByteArray()))
    }

    @Test fun docxContainsEditableWordPartsAndEscapesXml() {
        val entries = parts(SkyNativeOfficeExport.Format.WORD)
        assertTrue(entries.containsKey("[Content_Types].xml"))
        assertTrue(entries.containsKey("_rels/.rels"))
        assertTrue(entries.containsKey("word/document.xml"))
        assertTrue(entries.containsKey("word/styles.xml"))
        assertTrue(entries.containsKey("docProps/core.xml"))
        val doc = entries.getValue("word/document.xml")
        assertTrue(doc.contains("Proyecto SKY &amp; Nicaragua"))
        assertTrue(doc.contains("&lt;script&gt; &amp; caracteres"))
        assertTrue(doc.contains("w:styleId=\"Heading1\"").not())
        assertTrue(entries.getValue("word/styles.xml").contains("w:styleId=\"Heading1\""))
        assertTrue(doc.contains("w:t"))
        entries.filterKeys { it.endsWith(".xml") || it.endsWith(".rels") }
            .values.forEach { parseXml(it) }
    }

    @Test fun pptxContainsSlidesMasterLayoutThemeAndShapes() {
        val entries = parts(SkyNativeOfficeExport.Format.POWERPOINT)
        assertTrue(entries.containsKey("ppt/presentation.xml"))
        assertTrue(entries.containsKey("ppt/slideMasters/slideMaster1.xml"))
        assertTrue(entries.containsKey("ppt/slideLayouts/slideLayout1.xml"))
        assertTrue(entries.containsKey("ppt/theme/theme1.xml"))
        assertTrue(entries.containsKey("ppt/slides/slide1.xml"))
        assertTrue(entries.containsKey("ppt/slides/slide2.xml"))
        assertTrue(entries.containsKey("ppt/slides/_rels/slide2.xml.rels"))
        assertTrue(entries.getValue("ppt/presentation.xml").contains("screen16x9"))
        assertTrue(entries.getValue("ppt/slides/slide2.xml").contains("p:sp"))
        assertTrue(entries.getValue("ppt/slides/slide2.xml").contains("a:t"))
        assertTrue(entries.getValue("ppt/slides/slide2.xml").contains("103F73"))
        entries.filterKeys { it.endsWith(".xml") || it.endsWith(".rels") }
            .forEach { (_, xml) -> parseXml(xml) }
    }

    @Test fun controlsInvalidXmlAndFilenameTraversal() {
        val cleaned = SkyNativeOfficeExport.escapeXml("Hola <b>& \u0000 fin")
        assertEquals("Hola &lt;b&gt;&amp;  fin", cleaned)
        val file = SkyNativeOfficeExport.filename(entry, SkyNativeOfficeExport.Format.POWERPOINT)
        assertTrue(file.endsWith(".pptx"))
        assertFalse(file.contains("/"))
        assertFalse(file.contains(".."))
    }

    @Test fun splitsSlidesBySectionsWithBoundedCount() {
        val slides = SkyNativePowerPoint.outline(entry)
        assertTrue(slides.size >= 3)
        assertTrue(slides.size <= 25)
        assertTrue(slides.all { it.bullets.size <= 5 })
        assertTrue(slides.any { it.title == "Objetivos" })
    }
}
