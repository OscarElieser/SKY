package ni.sky.mobileagent

import java.util.zip.ZipOutputStream

/**
 * PowerPoint 16:9 con diapositivas, textos y formas nativas editables.
 * El diseño es azul/cian SKY. No usa capturas planas ni genera imágenes ficticias.
 */
object SkyNativePowerPoint {
    internal data class Slide(val title: String, val bullets: List<String>)

    /** Cada sección del texto se convierte en diapositivas de hasta 5 bloques. */
    internal fun outline(entry: SkyConversationArchive.Entry): List<Slide> {
        val slides = mutableListOf(Slide(entry.title.take(110),
            listOf("Presentación editable creada con SKY IA", entry.localTime())))
        var section = "Ideas principales"
        val current = mutableListOf<String>()
        fun flush() {
            current.chunked(5).forEachIndexed { group, bullets ->
                if (slides.size < 25) slides.add(
                    Slide(section + if (group > 0) " · continuación" else "", bullets)
                )
            }
            current.clear()
        }
        for (line in entry.answer.lines()) {
            val raw = line.trim()
            if (raw.isEmpty()) continue
            if (raw.startsWith("#")) {
                flush()
                section = raw.trimStart('#', ' ').take(90).ifBlank { "Contenido" }
                continue
            }
            val text = raw.removePrefix("- ").removePrefix("* ")
                .replace(Regex("""^\d+[.)]\s+"""), "")
            var buffer = StringBuilder()
            for (word in text.split(Regex("""\s+"""))) {
                if (buffer.isNotEmpty() && buffer.length + word.length + 1 > 135) {
                    current.add(buffer.toString())
                    buffer = StringBuilder()
                }
                if (buffer.isNotEmpty()) buffer.append(' ')
                buffer.append(word.take(135))
            }
            if (buffer.isNotEmpty()) current.add(buffer.toString())
        }
        flush()
        if (slides.size == 1) slides.add(Slide("Contenido", listOf("No hay contenido para presentar.")))
        return slides
    }

    fun write(zip: ZipOutputStream, entry: SkyConversationArchive.Entry) {
        val office = SkyNativeOfficeExport
        val rels = office.RELS
        val docRels = office.DOCRELS
        val p = office.PRESENT
        val a = office.DRAW
        val slides = outline(entry)
        val typesSlides = slides.indices.joinToString("") { index ->
            """<Override PartName="/ppt/slides/slide${index + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>"""
        }
        office.zipPut(zip, "[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="${office.CONTENT}">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
$typesSlides</Types>""")
        office.zipPut(zip, "_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="$rels">
<Relationship Id="rId1" Type="$docRels/officeDocument" Target="ppt/presentation.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>""")
        office.zipPut(zip, "docProps/core.xml", office.core(entry))
        val slideIds = slides.indices.joinToString("") { index ->
            """<p:sldId id="${256 + index}" r:id="rId${index + 2}"/>"""
        }
        office.zipPut(zip, "ppt/presentation.xml", """<?xml version="1.0" encoding="UTF-8"?>
<p:presentation xmlns:p="$p" xmlns:a="$a" xmlns:r="$docRels">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
<p:sldIdLst>$slideIds</p:sldIdLst>
<p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
<p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>""")
        val relatedSlides = slides.indices.joinToString("") { index ->
            """<Relationship Id="rId${index + 2}" Type="$docRels/slide" Target="slides/slide${index + 1}.xml"/>"""
        }
        office.zipPut(zip, "ppt/_rels/presentation.xml.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="$rels">
<Relationship Id="rId1" Type="$docRels/slideMaster" Target="slideMasters/slideMaster1.xml"/>
$relatedSlides</Relationships>""")

        val emptyTree = """<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>
<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree>"""

        office.zipPut(zip, "ppt/slideMasters/slideMaster1.xml", """<?xml version="1.0" encoding="UTF-8"?>
<p:sldMaster xmlns:p="$p" xmlns:a="$a" xmlns:r="$docRels">
<p:cSld name="SKY IA">$emptyTree</p:cSld>
<p:clrMap accent1="accent1" accent2="accent2" accent3="accent3"
accent4="accent4" accent5="accent5" accent6="accent6"
bg1="lt1" bg2="lt2" tx1="dk1" tx2="dk2" hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>""")
        office.zipPut(zip, "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="$rels">
<Relationship Id="rId1" Type="$docRels/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
<Relationship Id="rId2" Type="$docRels/theme" Target="../theme/theme1.xml"/>
</Relationships>""")
        office.zipPut(zip, "ppt/slideLayouts/slideLayout1.xml", """<?xml version="1.0" encoding="UTF-8"?>
<p:sldLayout xmlns:p="$p" xmlns:a="$a" xmlns:r="$docRels" type="blank" preserve="1">
<p:cSld name="SKY · En blanco">$emptyTree</p:cSld>
<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>""")
        office.zipPut(zip, "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="$rels">
<Relationship Id="rId1" Type="$docRels/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>""")
        office.zipPut(zip, "ppt/theme/theme1.xml", theme(a))
        slides.forEachIndexed { index, slide ->
            office.zipPut(zip, "ppt/slides/slide${index + 1}.xml",
                slideXml(slide, index, slides.size, p, a, docRels))
            office.zipPut(zip, "ppt/slides/_rels/slide${index + 1}.xml.rels",
                """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="$rels">
<Relationship Id="rId1" Type="$docRels/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>""")
        }
    }

    private fun theme(a: String): String = """<?xml version="1.0" encoding="UTF-8"?>
<a:theme xmlns:a="$a" name="SKY IA">
<a:themeElements>
<a:clrScheme name="SKY">
<a:dk1><a:srgbClr val="0B1733"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
<a:dk2><a:srgbClr val="182948"/></a:dk2><a:lt2><a:srgbClr val="F4F8FC"/></a:lt2>
<a:accent1><a:srgbClr val="11B8E8"/></a:accent1>
<a:accent2><a:srgbClr val="596DE8"/></a:accent2>
<a:accent3><a:srgbClr val="5AC8A5"/></a:accent3>
<a:accent4><a:srgbClr val="A8B8DF"/></a:accent4>
<a:accent5><a:srgbClr val="00A2C7"/></a:accent5>
<a:accent6><a:srgbClr val="B6DFF2"/></a:accent6>
<a:hlink><a:srgbClr val="0077BB"/></a:hlink>
<a:folHlink><a:srgbClr val="6858BA"/></a:folHlink>
</a:clrScheme>
<a:fontScheme name="SKY">
<a:majorFont><a:latin typeface="Aptos Display"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
<a:minorFont><a:latin typeface="Aptos"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
</a:fontScheme>
<a:fmtScheme name="SKY">
<a:fillStyleLst>
<a:solidFill><a:schemeClr val="accent1"/></a:solidFill>
<a:solidFill><a:schemeClr val="accent2"/></a:solidFill>
<a:solidFill><a:schemeClr val="accent3"/></a:solidFill>
</a:fillStyleLst>
<a:lnStyleLst>
<a:ln w="9525"><a:solidFill><a:schemeClr val="accent1"/></a:solidFill></a:ln>
<a:ln w="19050"><a:solidFill><a:schemeClr val="accent2"/></a:solidFill></a:ln>
<a:ln w="28575"><a:solidFill><a:schemeClr val="accent3"/></a:solidFill></a:ln>
</a:lnStyleLst>
<a:effectStyleLst>
<a:effectStyle><a:effectLst/></a:effectStyle>
<a:effectStyle><a:effectLst/></a:effectStyle>
<a:effectStyle><a:effectLst/></a:effectStyle>
</a:effectStyleLst>
<a:bgFillStyleLst>
<a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
<a:solidFill><a:schemeClr val="lt2"/></a:solidFill>
<a:solidFill><a:schemeClr val="dk1"/></a:solidFill>
</a:bgFillStyleLst>
</a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/>
</a:theme>"""

    private fun textShape(id: Int, label: String, x: Long, y: Long, w: Long, h: Long,
                          paragraphs: List<String>, size: Int, color: String, bold: Boolean): String {
        val escapedLabel = SkyNativeOfficeExport.escapeXml(label)
        val runs = paragraphs.joinToString("") { raw ->
            val safe = SkyNativeOfficeExport.escapeXml(raw.take(400))
            """<a:p><a:pPr algn="l"/>
<a:r><a:rPr lang="es-NI" sz="$size" b="${if (bold) 1 else 0}" dirty="0">
<a:solidFill><a:srgbClr val="$color"/></a:solidFill>
<a:latin typeface="Aptos"/></a:rPr><a:t>$safe</a:t></a:r>
<a:endParaRPr lang="es-NI"/></a:p>"""
        }
        return """<p:sp>
<p:nvSpPr><p:cNvPr id="$id" name="$escapedLabel"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="$x" y="$y"/><a:ext cx="$w" cy="$h"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/>
<a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap="square" lIns="0" rIns="0" tIns="0" bIns="0"/>
<a:lstStyle/>$runs</p:txBody></p:sp>"""
    }

    private fun accentShape(): String = """<p:sp>
<p:nvSpPr><p:cNvPr id="5" name="Barra visual editable"/>
<p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="780000" y="1460000"/>
<a:ext cx="1300000" cy="65000"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
<a:solidFill><a:srgbClr val="11B8E8"/></a:solidFill>
<a:ln><a:noFill/></a:ln></p:spPr></p:sp>"""

    private fun slideXml(slide: Slide, index: Int, total: Int,
                         p: String, a: String, relationships: String): String {
        val cover = index == 0
        val bg = if (cover) "0B1733" else "F4F8FC"
        val titleColor = if (cover) "76DBF9" else "103F73"
        val bodyColor = if (cover) "E5F0FF" else "182948"
        val title = textShape(2, "Título de diapositiva",
            780000L, if (cover) 1600000L else 560000L, 10600000L,
            if (cover) 1600000L else 980000L,
            listOf(slide.title), if (cover) 3800 else 3100, titleColor, true)
        val body = textShape(3, "Contenido editable",
            820000L, if (cover) 3650000L else 1840000L, 10500000L,
            if (cover) 1500000L else 4000000L,
            slide.bullets.map { if (cover) it else "• " + it },
            if (cover) 2200 else 2050, bodyColor, false)
        val footer = textShape(4, "Pie de página SKY IA",
            820000L, 6300000L, 10400000L, 300000L,
            listOf("SKY IA · " + (index + 1) + "/" + total), 1200,
            if (cover) "A7DCEC" else "596C87", false)
        val accents = if (cover) "" else accentShape()
        return """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="$p" xmlns:a="$a" xmlns:r="$relationships">
<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="$bg"/></a:solidFill>
<a:effectLst/></p:bgPr></p:bg>
<p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
$title$body$footer$accents</p:spTree></p:cSld>
<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"""
    }
}
