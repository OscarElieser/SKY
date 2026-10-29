package ni.sky.mobileagent

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import javax.xml.XMLConstants
import javax.xml.parsers.DocumentBuilderFactory

class SkyVectorExportTest {
    private val sample = SkyConversationArchive.Entry(
        4L, "Diseño <SKY> & más", "Prepará una infografía",
        "- Idea <script>alert(1)</script> & seguridad\n- Dos\n- Tres\n- Cuatro\n- Cinco",
        "Gemini", 1780000000000L
    )

    @Test fun generatesEscapedVectorInfographicWithoutScripts() {
        val svg = SkyVectorExport.render(sample)
        assertTrue(svg.contains("<svg"))
        assertTrue(svg.contains("&lt;SKY&gt; &amp; más"))
        assertTrue(svg.contains("&lt;script&gt;"))
        assertFalse(svg.contains("<script>"))
        assertFalse(svg.contains("<image "))
        assertFalse(svg.contains("onload="))
        assertTrue(svg.contains("id=\"bloque-4\""))
        assertFalse(svg.contains("id=\"bloque-5\""))
        val parser = DocumentBuilderFactory.newInstance()
        parser.isNamespaceAware = true
        parser.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true)
        parser.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
        val doc = parser.newDocumentBuilder().parse(
            ByteArrayInputStream(svg.toByteArray(Charsets.UTF_8))
        )
        assertTrue(doc.documentElement.localName == "svg")
    }

    @Test fun fileHasSafeSvgExtension() {
        val name = SkyVectorExport.filename(sample)
        assertTrue(name.endsWith(".svg"))
        assertFalse(name.contains("/"))
        assertFalse(name.contains(".."))
    }
}
