package ni.sky.mobileagent

import java.util.zip.ZipOutputStream

/** Native, editable .xlsx: typed numeric cells, tables and Excel SUM formulas. */
object SkyNativeExcel {
    private const val X = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    private const val R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    internal fun dataRows(answer: String): List<List<String>> {
        val lines = answer.lines().map { it.trim() }.filter { it.isNotBlank() }
        val candidates = lines.filter { it.count { ch -> ch == '|' } >= 2 }
            .map { line -> line.trim('|').split('|').map { it.trim() }.take(12) }
            .filterNot { it.all { cell -> cell.matches(Regex(":?-{3,}:?")) } }
        if (candidates.size >= 2 && candidates[0].size > 1) {
            return candidates.filter { it.size == candidates[0].size }.take(500)
        }
        val tabs = lines.filter { '\t' in it }.map { it.split('\t').map(String::trim).take(12) }
        if (tabs.size >= 2 && tabs[0].size > 1) {
            return tabs.filter { it.size == tabs[0].size }.take(500)
        }
        val result = mutableListOf(listOf("N.º", "Contenido"))
        lines.take(499).forEachIndexed { i, line ->
            result.add(listOf((i + 1).toString(), line.trimStart('-', '*', '#', ' ').take(950)))
        }
        if (result.size == 1) result.add(listOf("1", "Sin información"))
        return result
    }

    private fun col(index: Int): String {
        var i = index + 1
        var name = ""
        while (i > 0) {
            name = ('A'.code + (i - 1) % 26).toChar() + name
            i = (i - 1) / 26
        }
        return name
    }

    internal fun number(raw: String): String? {
        val normalized = raw.trim().replace(',', '.')
        if (!normalized.matches(Regex("[+-]?[0-9]{1,12}([.][0-9]{1,6})?"))) return null
        return normalized.toDoubleOrNull()?.takeIf { it.isFinite() }?.let { normalized }
    }

    private fun cell(address: String, text: String, header: Boolean): String {
        if (!header) {
            val numeric = number(text)
            if (numeric != null) return """<c r="$address" s="2"><v>$numeric</v></c>"""
        }
        return """<c r="$address" s="${if (header) 1 else 0}" t="inlineStr"><is>
<t xml:space="preserve">${SkyNativeOfficeExport.escapeXml(text.take(1100))}</t>
</is></c>"""
    }

    private fun sheet(rows: List<List<String>>, totals: Boolean): String {
        val ncols = (rows.maxOfOrNull { it.size } ?: 1).coerceIn(1, 12)
        val endRow = rows.size
        val lastCol = col(ncols - 1)
        val content = StringBuilder()
        rows.forEachIndexed { index, row ->
            content.append("""<row r="${index + 1}">""")
            row.take(ncols).forEachIndexed { j, value ->
                content.append(cell(col(j) + (index + 1), value, index == 0))
            }
            content.append("</row>")
        }
        if (totals && rows.size > 2) {
            val numericCols = (1 until ncols).filter { j ->
                rows.drop(1).all { row -> number(row.getOrNull(j).orEmpty()) != null }
            }
            if (numericCols.isNotEmpty()) {
                content.append("""<row r="${endRow + 1}">""")
                content.append(cell("A" + (endRow + 1), "TOTAL", true))
                numericCols.forEach { j ->
                    val letter = col(j)
                    content.append("""<c r="$letter${endRow + 1}" s="2"><f>SUM(${letter}2:$letter$endRow)</f><v>0</v></c>""")
                }
                content.append("</row>")
            }
        }
        val widths = (0 until ncols).joinToString("") { i ->
            """<col min="${i + 1}" max="${i + 1}" width="${if (i == 0) 19 else 41}" customWidth="1"/>"""
        }
        val filter = if (totals && rows.size > 1)
            """<autoFilter ref="A1:$lastCol$endRow"/>""" else ""
        return """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="$X">
<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2"
activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
<sheetFormatPr defaultRowHeight="20"/>
<cols>$widths</cols><sheetData>$content</sheetData>$filter
<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>
</worksheet>"""
    }

    fun write(zip: ZipOutputStream, entry: SkyConversationArchive.Entry) {
        val h = SkyNativeOfficeExport
        val data = dataRows(entry.answer)
        val summary = listOf(listOf("Campo", "Valor"),
            listOf("Tema", entry.title), listOf("Consulta", entry.question.take(950)),
            listOf("Motor", entry.engine), listOf("Fecha", entry.localTime()),
            listOf("Registros", (data.size - 1).toString()))
        h.zipPut(zip, "[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="${h.CONTENT}">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>""")
        h.zipPut(zip, "_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="${h.RELS}">
<Relationship Id="rId1" Type="${h.DOCRELS}/officeDocument" Target="xl/workbook.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>""")
        h.zipPut(zip, "docProps/core.xml", h.core(entry))
        h.zipPut(zip, "xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="$X" xmlns:r="$R">
<bookViews><workbookView activeTab="0"/></bookViews>
<sheets><sheet name="Datos" sheetId="1" r:id="rId1"/>
<sheet name="Resumen" sheetId="2" r:id="rId2"/></sheets>
<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>
</workbook>""")
        h.zipPut(zip, "xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="${h.RELS}">
<Relationship Id="rId1" Type="$R/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="$R/worksheet" Target="worksheets/sheet2.xml"/>
<Relationship Id="rId3" Type="$R/styles" Target="styles.xml"/>
</Relationships>""")
        h.zipPut(zip, "xl/styles.xml", """<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="$X">
<fonts count="2"><font><sz val="11"/><name val="Aptos"/></font>
<font><b/><sz val="11"/><name val="Aptos"/><color rgb="FFFFFFFF"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF104777"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
<xf numFmtId="2" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>""")
        h.zipPut(zip, "xl/worksheets/sheet1.xml", sheet(data, true))
        h.zipPut(zip, "xl/worksheets/sheet2.xml", sheet(summary, false))
    }
}
