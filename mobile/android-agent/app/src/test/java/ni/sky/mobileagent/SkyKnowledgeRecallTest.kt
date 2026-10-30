package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyKnowledgeRecallTest {
    @Test fun retrievesRelevantRecentPublicSourcesOnly() {
        val now = 1_800_000_000_000L
        val entries = listOf(
            SkyAndroidKnowledgeSources.SourceEntry("Investigación de Flutter",
                "https://flutter.dev/resources", now - 86_400_000L, "verified search"),
            SkyAndroidKnowledgeSources.SourceEntry("Guía Flutter antigua",
                "https://flutter.dev/old", now - 40L*86_400_000L, "verified search"),
            SkyAndroidKnowledgeSources.SourceEntry("Otro tema",
                "https://example.org/paper", now, "verified search"))
        val found = SkyKnowledgeRecall.select("investigación sobre Flutter", entries, now)
        assertEquals(1, found.size)
        assertTrue(SkyKnowledgeRecall.guidance(found).contains("no las declares actuales"))
    }
    @Test fun neverInventsSources() {
        assertTrue(SkyKnowledgeRecall.select("Hola", emptyList()).isEmpty())
    }
}
