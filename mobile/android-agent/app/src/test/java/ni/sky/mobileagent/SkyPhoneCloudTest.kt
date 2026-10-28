package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Pruebas sin credenciales, ni red, ni dependencia de Windows. */
class SkyPhoneCloudTest {
    @Test fun modelIsPinnedToKnownStableGemini() {
        assertEquals("gemini-3.5-flash-lite", SkyPhoneCloud.MODEL)
    }
    @Test fun personalKeyRejectsDangerousCharactersAndMissingValues() {
        assertFalse(SkyPhoneCloud.validPersonalKey(""))
        assertFalse(SkyPhoneCloud.validPersonalKey("AIza nada"))
        assertFalse(SkyPhoneCloud.validPersonalKey("abc\nInjected"))
        assertTrue(SkyPhoneCloud.validPersonalKey("AIzaSyEXAMPLEonly-for-validation_12345"))
    }
}
