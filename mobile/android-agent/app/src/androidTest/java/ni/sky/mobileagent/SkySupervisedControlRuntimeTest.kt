package ni.sky.mobileagent

import android.content.Context
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Verifica consentimiento REAL en SharedPreferences del Android emulado. */
@RunWith(AndroidJUnit4::class)
class SkySupervisedControlRuntimeTest {
    @Test fun consentPersistsCanBeRevokedAndNeverGrantsRemoteRights() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val local = SkySupervisedControl(context)
        val legacy = context.getSharedPreferences("sky_trusted_launcher_apps", Context.MODE_PRIVATE)
        val remote = context.getSharedPreferences("sky_mobile_allowed_apps", Context.MODE_PRIVATE)
        val initial = local.isAuthorized()
        val remoteBefore = remote.getAll().toMap()
        try {
            assertTrue("Android no pudo persistir consentimiento local", local.setAuthorized(true))
            assertTrue("El consentimiento no quedó guardado", SkySupervisedControl(context).isAuthorized())
            assertEquals("No se puede modificar permisos remotos al aceptar", remoteBefore,
                remote.getAll().toMap())
            assertFalse("La APK estándar nunca debe habilitar AccessibilityService",
                BuildConfig.ENABLE_TEXT_ASSIST)
            assertTrue("No se pudo revocar consentimiento local", local.setAuthorized(false))
            assertFalse("La revocación no quedó guardada", SkySupervisedControl(context).isAuthorized())
        } finally {
            assertTrue("No se restauró el consentimiento previo", local.setAuthorized(initial))
        }
        assertEquals(initial, legacy.getBoolean("global_supervised_control", false))
    }
}
