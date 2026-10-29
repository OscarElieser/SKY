package ni.sky.mobileagent

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Prueba la firma del APK realmente instalado en un emulador Android. */
@RunWith(AndroidJUnit4::class)
class SkyAndroidSecurityRuntimeTest {
    @Test fun installedApkHasReadableSha256SigningCertificate() {
        val app = InstrumentationRegistry.getInstrumentation().targetContext
        val thumbprint = SkyAndroidSecurityReport.certificateSha256(app)
        assertTrue("La firma instalada no tiene huella SHA-256 válida: $thumbprint",
            Regex("[A-F0-9]{2}(:[A-F0-9]{2}){31}").matches(thumbprint))
        val report = SkyAndroidSecurityReport.status(app)
        assertTrue(report.contains(thumbprint))
        assertTrue(report.contains("Play Protect"))
        assertTrue(report.contains("Control supervisado"))
    }
}
