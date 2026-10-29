package ni.sky.mobileagent

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Comprueba escritura y lectura REALES de SQLite en Android (emulador/dispositivo).
 * Nunca usa un archivo simulado ni borra registros anteriores.
 */
@RunWith(AndroidJUnit4::class)
class SkyExecutionEvidenceRuntimeTest {
    @Test fun realDatabaseSeparatesAcceptedRequestsFromVerifiedEffects() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        SkyActionEvidence(context).use { evidence ->
            val before = evidence.summary()
            val key = "Prueba de evidencia Android " + System.nanoTime()
            val ids = listOf(
                evidence.record(key + " dispatch", "SENT", "Intent aceptado, resultado desconocido"),
                evidence.record(key + " saved", "VERIFIED_LOCAL", "Escritura releída desde disco"),
                evidence.record(key + " failure", "FAILED", "Android bloqueó el intento"),
                evidence.record(key + " rejected", "REJECTED", "El usuario denegó acceso")
            )
            assertEquals(4, ids.distinct().size)
            val after = evidence.summary()
            assertEquals(before.total + 4, after.total)
            assertEquals(before.verified + 1, after.verified)
            assertEquals(before.sentUnverified + 1, after.sentUnverified)
            assertEquals(before.failed + 1, after.failed)
            assertEquals(before.rejected + 1, after.rejected)
            val found = evidence.recent(10).filter { it.action.startsWith(key) }
            assertEquals(4, found.size)
            assertTrue(found.any { it.status == "ENVIADA_SIN_VERIFICAR" })
            assertTrue(found.any { it.status == "VERIFICADA_LOCAL" })
        }
    }
}
