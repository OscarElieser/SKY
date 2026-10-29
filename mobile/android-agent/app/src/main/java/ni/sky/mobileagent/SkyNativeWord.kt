package ni.sky.mobileagent

import java.util.zip.ZipOutputStream

/** Documento Word real: títulos, secciones y párrafos editables. */
object SkyNativeWord {
    fun write(zip: ZipOutputStream, entry: SkyConversationArchive.Entry) {
        val h = SkyNativeOfficeExport
        val w = h.WORD
        val rel = h.RELS
        val office = h.DOCRELS
        val types = h.CONTENT
        h.zipPut(zip, "[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="$types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>""")
        h.zipPut(zip, "_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="$rel">
<Relationship Id="rId1" Type="$office/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>""")
        h.zipPut(zip, "word/_rels/document.xml.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="$rel"><Relationship Id="rId1" Type="$office/styles" Target="styles.xml"/></Relationships>""")
        h.zipPut(zip, "docProps/core.xml", h.core(entry))
        h.zipPut(zip, "word/styles.xml", """<?xml version="1.0" encoding="UTF-8"?>
<w:styles xmlns:w="$w">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/>
<w:sz w:val="22"/><w:color w:val="182948"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal">
<w:name w:val="Normal"/><w:pPr><w:spacing w:after="155" w:line="290" w:lineRule="auto"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>
<w:rPr><w:b/><w:sz w:val="39"/><w:color w:val="103F73"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/>
<w:rPr><w:sz w:val="19"/><w:color w:val="58708F"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>
<w:basedOn w:val="Normal"/><w:pPr><w:keepNext/></w:pPr>
<w:rPr><w:b/><w:sz w:val="28"/><w:color w:val="136493"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/>
<w:basedOn w:val="Normal"/><w:pPr><w:keepNext/></w:pPr>
<w:rPr><w:b/><w:sz w:val="24"/><w:color w:val="136493"/></w:rPr></w:style>
</w:styles>""")
        fun paragraph(text: String, style: String = "Normal"): String {
            val styleTag = if (style == "Normal") "" else
                """<w:pPr><w:pStyle w:val="$style"/></w:pPr>"""
            return """<w:p>$styleTag<w:r><w:t xml:space="preserve">${h.escapeXml(text)}</w:t></w:r></w:p>"""
        }
        val body = buildString {
            append(paragraph(entry.title.take(220), "Title"))
            append(paragraph("SKY IA · " + entry.localTime() + " · " + entry.engine, "Subtitle"))
            append(paragraph("Consulta", "Heading1"))
            entry.question.lines().take(200).forEach { append(paragraph(it)) }
            append(paragraph("Respuesta de SKY IA", "Heading1"))
            entry.answer.lines().take(3000).forEach { original ->
                val line = original.trim()
                when {
                    line.startsWith("### ") -> append(paragraph(line.drop(4), "Heading2"))
                    line.startsWith("## ") || line.startsWith("# ") ->
                        append(paragraph(line.trimStart('#', ' '), "Heading1"))
                    line.startsWith("- ") || line.startsWith("* ") ->
                        append(paragraph("• " + line.drop(2)))
                    else -> append(paragraph(original))
                }
            }
        }
        h.zipPut(zip, "word/document.xml", """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="$w"><w:body>$body
<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>
<w:pgMar w:top="1190" w:right="1130" w:bottom="1190" w:left="1130"
w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>
</w:body></w:document>""")
    }
}
