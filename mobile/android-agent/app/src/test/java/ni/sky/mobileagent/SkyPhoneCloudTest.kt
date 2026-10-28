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
    @Test fun keyErrorsExplainProjectIdWithoutLeakingSecrets() {
        val id = "projects/216507061862"
        assertTrue(SkyPhoneCloud.personalKeyProblem(id)!!.contains("identificador del proyecto"))
        assertFalse(SkyPhoneCloud.validPersonalKey(id))
        assertTrue(SkyPhoneCloud.personalKeyProblem("Bearer abcdefghijklmnopqrstuvwxyz")!!.contains("únicamente"))
        assertTrue(SkyPhoneCloud.personalKeyProblem("AIzaSyEXAMPLEonly-for-validation_12345") == null)
    }
    @Test fun keyTrimsClipboardPaddingAndRejectsInBandWhitespace() {
        val valid = "AIzaSyEXAMPLEonly-for-validation_12345"
        assertEquals(valid, SkyPhoneCloud.normalizePersonalKey("  " + valid + "\u200B"))
        assertTrue(SkyPhoneCloud.personalKeyProblem("  " + valid + "\u200B") == null)
        assertTrue(SkyPhoneCloud.personalKeyProblem("AIza  EXAMPLEonly-for-validation_12345")!!.contains("caracteres"))
    }
    @Test fun personalKeyRejectsDangerousCharactersAndMissingValues() {
        assertFalse(SkyPhoneCloud.validPersonalKey(""))
        assertFalse(SkyPhoneCloud.validPersonalKey("AIza nada"))
        assertFalse(SkyPhoneCloud.validPersonalKey("abc\nInjected"))
        assertTrue(SkyPhoneCloud.validPersonalKey("AIzaSyEXAMPLEonly-for-validation_12345"))
    }
}
