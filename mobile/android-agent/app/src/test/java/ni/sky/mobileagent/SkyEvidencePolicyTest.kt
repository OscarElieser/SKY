package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyEvidencePolicyTest {
    @Test fun routesClaimsAndGoogleRequestsToActualWebSearch() {
        assertTrue(SkyEvidencePolicy.needsVerification("SKY, ¿es verdad esta noticia?"))
        assertTrue(SkyEvidencePolicy.needsVerification("busca en Google la noticia"))
        assertTrue(SkyEvidencePolicy.needsVerification("verifica el reglamento actual"))
        assertFalse(SkyEvidencePolicy.needsVerification("Hola, ¿cómo estás?"))
    }
    @Test fun differentiatesDomainsWithoutClaimingTruth() {
        val one = listOf(SkyPhoneCloud.Source("A", "https://example.org/paper"),
            SkyPhoneCloud.Source("A2", "https://example.org/update"))
        assertEquals("UNA_FUENTE", SkyEvidencePolicy.assess(one).level)
        val two = one + SkyPhoneCloud.Source("B", "https://nasa.gov/science")
        assertEquals("VARIAS_FUENTES", SkyEvidencePolicy.assess(two).level)
        assertTrue(SkyEvidencePolicy.qualify("Resultado", two)
            .contains("NO demuestra"))
    }
    @Test fun cannotTreatUnsafeUrlsAsTrustedSources() {
        val bad = listOf(SkyPhoneCloud.Source("a", "http://localhost/hello"),
            SkyPhoneCloud.Source("b", "javascript:alert(1)"))
        assertEquals("SIN_FUENTE", SkyEvidencePolicy.assess(bad).level)
    }
}
