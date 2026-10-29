package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

/** Validación del destino HTTPS antes de transmitir tokens o datos privados. */
class SkyNetworkSecurityTest {
    @Test fun acceptsOnlyBaseHttpsOrigin() {
        assertEquals("https://sky.example", SkyNetwork.validateServer(" https://sky.example/ "))
        assertEquals("https://sky.example:443", SkyNetwork.validateServer("https://sky.example:443"))
    }

    @Test fun rejectsHttpCredentialsPathsFragmentsAndQueries() {
        val forbidden = listOf(
            "http://sky.example", "https://user:pass@sky.example",
            "https://sky.example/private",
            "https://sky.example/?token=private",
            "https://sky.example/#fragment",
            "file:///etc/passwd", "javascript:alert(1)",
            "https://", ""
        )
        for (candidate in forbidden) {
            assertTrue("No debe aceptar destino inseguro: $candidate",
                runCatching { SkyNetwork.validateServer(candidate) }.isFailure)
        }
    }
}
