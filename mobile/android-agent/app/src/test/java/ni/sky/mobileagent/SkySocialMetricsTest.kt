package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkySocialMetricsTest {
    @Test fun importCreatorsOwnCSVWithSpanishColumns() {
        val csv = "Plataforma,Publicación,Vistas,Likes,Comentarios,Compartidos,Seguidores,Fecha\n" +
            "TikTok,Consejos de Nicaragua,1200,120,20,5,3,2026-10-28\n" +
            "Instagram,Consejos de diseño,800,60,10,2,1,2026-10-28"
        val rows = SkySocialMetrics.parseCsv(csv)
        assertEquals(2, rows.size)
        assertEquals(1200L, rows[0].views)
        assertEquals(145.0 / 1200.0 * 100, rows[0].engagementRate(), 0.00001)
        val analysis = SkySocialMetrics.analysis(rows)
        assertTrue(analysis.contains("2000"))
        assertTrue(analysis.contains("NO sincronizado"))
    }

    @Test fun parseQuotedPostContainingComma() {
        val rows = SkySocialMetrics.parseCsv(
            "platform,post,views,likes\n" +
            "YouTube,\"Hola, Nicaragua\",2000,100")
        assertEquals("Hola, Nicaragua", rows.first().post)
    }

    @Test fun rejectInvalidOrUnrelatedExports() {
        try {
            SkySocialMetrics.parseCsv("foo,bar\na,b")
            fail("Unexpected format should be rejected")
        } catch (_: IllegalArgumentException) { }
        try {
            SkySocialMetrics.parseCsv("plataforma,publicacion,vistas\nTikTok,Video,-90")
            fail("Negative counters should be rejected")
        } catch (_: IllegalArgumentException) { }
    }
}
