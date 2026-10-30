package ni.sky.mobileagent

import android.Manifest
import android.content.pm.PackageManager
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Verifies the manifest's Android OS permission boundary, not a playback simulation. */
@RunWith(AndroidJUnit4::class)
class SkyPlaybackProofRuntimeTest {
    @Test fun optionalListenerIsControlledByAndroidSystemPermission() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        @Suppress("DEPRECATION")
        val info = context.packageManager.getPackageInfo(
            context.packageName, PackageManager.GET_SERVICES)
        val service = info.services?.firstOrNull {
            it.name.endsWith("SkyPlaybackProofListener")
        }
        assertNotNull("La verificación requiere un servicio declarado explícitamente", service)
        assertEquals(Manifest.permission.BIND_NOTIFICATION_LISTENER_SERVICE, service?.permission)
        assertFalse("Una instalación de prueba limpia no debe activar permisos por sí sola",
            SkyPlaybackProof.available(context))
    }

    @Test fun noPlaybackIsClaimedWithoutUserEnablingPermission() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        if (!SkyPlaybackProof.available(context)) {
            assertFalse(SkyPlaybackProof.playing(context, "com.spotify.music", "November Rain"))
        }
        assertFalse(SkyPlaybackProof.playing(context, "com.whatsapp", "November Rain"))
    }
}
