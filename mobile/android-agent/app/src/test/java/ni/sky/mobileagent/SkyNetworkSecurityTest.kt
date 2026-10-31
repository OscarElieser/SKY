package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

/** Validación del destino HTTPS antes de transmitir tokens o datos privados. */
class SkyNetworkSecurityTest {
    @Test fun acceptsOnlyBaseHttpsOrigin() {
        assertEquals("https://sky.example", SkyNetwork.validateServer(" https://sky.example/ "))
        assertEquals("https://sky.example:443", SkyNetwork.validateServer("https://sky.example:443"))
    }

    @Test fun longMultilingualRepliesAreReadInFullWithinHardByteLimit() {
        val original = ("Investigación educativa: síntesis y método. ").repeat(6000)
            .toByteArray(Charsets.UTF_8)
        assertTrue(original.size > 131072)
        assertTrue(original.size < SkyNetwork.CHAT_RESPONSE_MAX_BYTES)
        val result = SkyNetwork.readBoundedBytes(
            java.io.ByteArrayInputStream(original),
            SkyNetwork.CHAT_RESPONSE_MAX_BYTES)
        assertArrayEquals(original, result)
    }

    @Test fun oversizedTransportIsRejectedInsteadOfShowingPartialDocument() {
        val excessive = ByteArray(SkyNetwork.CHAT_RESPONSE_MAX_BYTES + 1) { 42 }
        val failure = runCatching {
            SkyNetwork.readBoundedBytes(
                java.io.ByteArrayInputStream(excessive),
                SkyNetwork.CHAT_RESPONSE_MAX_BYTES)
        }.exceptionOrNull()
        assertTrue(failure is IllegalStateException)
        assertTrue(failure?.message?.contains("incompleta") == true)
        assertEquals(16_384, SkyNetwork.CONTROL_RESPONSE_MAX_BYTES)
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
