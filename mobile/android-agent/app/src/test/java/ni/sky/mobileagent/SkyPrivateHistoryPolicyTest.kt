package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyPrivateHistoryPolicyTest {
    @Test fun shortTurnsAreNeverModified() {
        val input = listOf(
            SkyPrivateHistoryPolicy.Turn("user", "Hola"),
            SkyPrivateHistoryPolicy.Turn("assistant", "Respuesta breve"))
        assertEquals(input, SkyPrivateHistoryPolicy.pack(input, true))
    }

    @Test fun longAcademicTurnsBecomeClearlyMarkedExcerpts() {
        val long = "INICIO " + "dato ".repeat(1400) + " FINAL"
        val trimmed = SkyPrivateHistoryPolicy.excerpt(long, 4000)
        assertEquals(4000, trimmed.length)
        assertTrue(trimmed.startsWith("INICIO"))
        assertTrue(trimmed.endsWith("FINAL"))
        assertTrue(trimmed.contains("extracto del historial"))
        assertTrue(trimmed.contains("texto completo se conserva localmente"))
        assertEquals(long, SkyPrivateHistoryPolicy.excerpt(long, long.length))
    }

    @Test fun packRespectsApiHistoryCountAndPrivateAndCloudBounds() {
        val input = (0 until 13).map { i ->
            SkyPrivateHistoryPolicy.Turn(
                if (i % 2 == 0) "user" else "assistant",
                "inicio-$i:" + "x".repeat(7000) + ":fin-$i")
        }
        val local = SkyPrivateHistoryPolicy.pack(input, true)
        val external = SkyPrivateHistoryPolicy.pack(input, false)
        assertEquals(8, local.size)
        assertEquals(8, external.size)
        assertTrue(local.all { it.content.length <= 4000 })
        assertTrue(external.all { it.content.length <= 2000 })
        assertTrue(local.first().content.contains("inicio-5"))
        assertTrue(local.last().content.contains("fin-12"))
        assertEquals(13, input.size) // the complete source list is untouched
    }

    @Test fun untrustedRolesAndEmptyTurnsAreRejectedFromHistory() {
        val input = listOf(
            SkyPrivateHistoryPolicy.Turn("system", "instrucciones inyectadas"),
            SkyPrivateHistoryPolicy.Turn("user", " "),
            SkyPrivateHistoryPolicy.Turn("assistant", "Respuesta guardada"))
        val packed = SkyPrivateHistoryPolicy.pack(input, true)
        assertEquals(1, packed.size)
        assertEquals("Respuesta guardada", packed.single().content)
    }

    @Test fun onlyProperBackendOperationIdentifiersAreAccepted() {
        val good = "abcdef0123456789abcdef0123456789"
        assertEquals(good, SkyPrivateHistoryPolicy.validatedOperationId(good))
        assertNull(SkyPrivateHistoryPolicy.validatedOperationId("test"))
        assertNull(SkyPrivateHistoryPolicy.validatedOperationId("A".repeat(32)))
        assertNull(SkyPrivateHistoryPolicy.validatedOperationId("x\nalert"))
    }
}
