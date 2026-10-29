package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertFalse
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.zip.ZipInputStream
import javax.xml.XMLConstants
import javax.xml.parsers.DocumentBuilderFactory

class SkyNativeExcelTest {
    private val row = SkyConversationArchive.Entry(1L, "Ventas del mes",
        "Crear tabla de ventas", """| Producto | Cantidad | Precio |
| --- | --- | --- |
| Producto A | 2 | 120.50 |
| Producto B | 3 | 80 |
""".trimIndent(), "SKY IA", 1780000000000L)

    @Test fun parsesMarkdownTableWithNumericValues() {
        val grid = SkyNativeExcel.dataRows(row.answer)
        assertEquals(3, grid.size)
        assertEquals(listOf("Producto", "Cantidad", "Precio"), grid[0])
        assertEquals("120.50", SkyNativeExcel.number(grid[1][2]))
        assertEquals(null, SkyNativeExcel.number("=IMPORTXML('malicioso')"))
        assertEquals(null, SkyNativeExcel.number("+HYPERLINK(1)"))
    }

    @Test fun realWorkbookContainsWorksheetsStylesAndCalculation() {
        val bytes = ByteArrayOutputStream().apply {
            SkyNativeOfficeExport.write(this, row, SkyNativeOfficeExport.Format.EXCEL)
        }.toByteArray()
        assertTrue(bytes.size > 500)
        val entries = mutableMapOf<String, String>()
        ZipInputStream(ByteArrayInputStream(bytes)).use { zip ->
            while (true) {
                val e = zip.nextEntry ?: break
                entries[e.name] = zip.readBytes().toString(Charsets.UTF_8)
                zip.closeEntry()
            }
        }
        for (p in listOf("[Content_Types].xml", "xl/workbook.xml",
                "xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml",
                "xl/styles.xml", "xl/_rels/workbook.xml.rels")) {
            assertTrue("Falta $p", p in entries)
        }
        val sheet = entries.getValue("xl/worksheets/sheet1.xml")
        assertTrue(sheet.contains("t=\"inlineStr\""))
        assertTrue(sheet.contains("<v>120.50</v>"))
        assertTrue(sheet.contains("SUM(B2:B3)"))
        assertTrue(sheet.contains("SUM(C2:C3)"))
        assertFalse(sheet.contains("IMPORTXML"))
        val parser = DocumentBuilderFactory.newInstance().apply {
            isNamespaceAware = true
            setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true)
            setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
        }
        entries.filterKeys { it.endsWith(".xml") || it.endsWith(".rels") }
            .values.forEach { xml ->
                parser.newDocumentBuilder().parse(ByteArrayInputStream(xml.toByteArray()))
            }
    }

    @Test fun fallsBackToEditiableRowsWithoutInventingADataTable() {
        val fallback = SkyNativeExcel.dataRows("Informe\nResultado positivo\nPendiente")
        assertEquals(listOf("N.º", "Contenido"), fallback[0])
        assertEquals(4, fallback.size)
        assertTrue(SkyNativeOfficeExport.filename(row, SkyNativeOfficeExport.Format.EXCEL)
            .endsWith(".xlsx"))
    }
}
