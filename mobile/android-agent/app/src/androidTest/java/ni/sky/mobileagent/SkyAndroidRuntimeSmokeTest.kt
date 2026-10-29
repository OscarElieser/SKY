package ni.sky.mobileagent

import android.content.Intent
import android.content.pm.PackageManager
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Ejecuta lógica real dentro de Android en emulador o dispositivo.
 * No simula que YouTube o Spotify reprodujeron música ni prueba un micrófono real.
 */
@RunWith(AndroidJUnit4::class)
class SkyAndroidRuntimeSmokeTest {
    private val app get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun applicationAndForegroundMicrophoneServiceAreRegistered() {
        val pm = app.packageManager
        val packageInfo = pm.getPackageInfo(app.packageName, PackageManager.GET_SERVICES)
        val service = packageInfo.services?.firstOrNull {
            it.name.endsWith("SkyHandsFreeService")
        }
        assertNotNull("Falta servicio de activación por voz", service)
        assertFalse("No exponer el servicio de micrófono", service!!.exported)
        assertEquals("El agente debe ser Android", "ni.sky.mobileagent", app.packageName)
        val launcher = pm.getLaunchIntentForPackage(app.packageName)
        assertNotNull("SKY debe tener un punto de entrada", launcher)
    }

    @Test fun wakeAndAppCommandsRouteWithoutExecutingOtherApplications() {
        assertEquals(SkyWakePhrase.Kind.WAKE,
            SkyWakePhrase.decide("SKY", awake = false).kind)
        assertEquals(SkyWakePhrase.Kind.COMMAND,
            SkyWakePhrase.decide("SKY abre YouTube", awake = false).kind)
        assertEquals(SkyWakePhrase.Kind.IGNORE,
            SkyWakePhrase.decide("abrí YouTube", awake = false).kind)
        val parsed = SkyDailyCommandParser.parse("SKY abre YouTube")
        assertTrue(parsed is SkyDailyCommandParser.Command.OpenApp)
        assertEquals("youtube", (parsed as SkyDailyCommandParser.Command.OpenApp).app)
        val query = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        assertTrue("Android debe registrar algún lanzador",
            app.packageManager.queryIntentActivities(query, 0).isNotEmpty())
    }

    @Test fun privateLongTermMemoryReallyPersistsAndCanBeDeleted() {
        SkyLongTermMemory(app).use { memory ->
            val value = "Prueba temporal de persistencia SKY " + System.currentTimeMillis()
            val fact = memory.remember(value)
            assertTrue(fact.id > 0L)
            assertTrue(memory.recent().any { it.id == fact.id && it.text == value })
            assertTrue(memory.delete(fact.id))
            assertFalse(memory.recent().any { it.id == fact.id })
        }
    }

    @Test fun receiptsNeverTreatSentAsCompletedActions() {
        SkyActionEvidence(app).use { evidence ->
            val id = evidence.record("Música: prueba de intento", "SENT",
                "Android recibió solicitud, no hay audio confirmado")
            val actual = evidence.recent(10).firstOrNull { it.id == id }
            assertNotNull(actual)
            assertEquals("ENVIADA_SIN_VERIFICAR", actual!!.status)
            assertNotEquals("VERIFICADA_LOCAL", actual.status)
        }
    }

    @Test fun learnedParametersRequireVerifiedFeedback() {
        val learning = SkyVerifiedLearning(app)
        learning.clear()
        try {
            assertFalse(learning.observe("Guardar nota local", "SENT"))
            assertTrue(learning.report().all { it.examples == 0 })
            assertTrue(learning.observe("Guardar nota local", "VERIFIED_LOCAL"))
            val note = learning.report().first { it.category == "notas" }
            assertEquals(1, note.examples)
            assertEquals(1, note.verified)
            assertTrue(note.probability > 0.5)
            assertTrue(learning.observe("Guardar nota local", "FAILED"))
            assertEquals(2, learning.report().first { it.category == "notas" }.examples)
        } finally {
            learning.clear()
        }
    }
}
