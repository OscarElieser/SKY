package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyFrontierSpecialtiesTest {
    @Test fun catalogueHasUniqueWellScopedEntries() {
        assertEquals(42, SkyFrontierSpecialties.entries.size)
        assertEquals(42,
            SkyFrontierSpecialties.entries.map { it.id }.toSet().size)
    }
    @Test fun categorizesResearchDefenceAndSpeculation() {
        assertEquals(SkyFrontierSpecialties.Domain.RESEARCH,
            SkyFrontierSpecialties.detect("quiero entrenar redes neuronales profundas").first().domain)
        assertEquals(SkyFrontierSpecialties.Domain.DEFENSIVE,
            SkyFrontierSpecialties.detect("revisar seguridad de firmware").first().domain)
        assertEquals(SkyFrontierSpecialties.Domain.SPECULATIVE,
            SkyFrontierSpecialties.detect("discutamos terraformación").first().domain)
    }
    @Test fun neverAuthorizesHiddenActions() {
        val g = SkyFrontierSpecialties.guidance("prompt injection")
        assertTrue(g.contains("pruebas explícitamente autorizadas"))
        assertTrue(g.contains("sin ejecución"))
        assertTrue(SkyFrontierSpecialties.guidance("teoría de cuerdas").contains("hipótesis"))
        assertEquals("", SkyFrontierSpecialties.guidance("Hola SKY"))
    }
}
