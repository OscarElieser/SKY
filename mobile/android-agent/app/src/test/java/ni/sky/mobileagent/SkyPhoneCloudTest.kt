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
        assertEquals("AIzaEXAMPLEonly-for-validation_12345",
            SkyPhoneCloud.normalizePersonalKey("AIza  EXAMPLEonly-for-validation_12345"))
    }
    @Test fun clipboardInvisibleMarksAreRemovedEvenInsideKey() {
        val key = "AIzaSyEXAMPLEonly-for-validation_12345"
        val clipboard = " \u200B" + key.take(8) + "\u200B \u00A0\uFEFF" + key.drop(8) + "\u200E\n"
        assertEquals(key, SkyPhoneCloud.normalizePersonalKey(clipboard))
        assertTrue(SkyPhoneCloud.validPersonalKey(clipboard))
    }
    @Test fun clipboardWrapperIsNotSilentlyAccepted() {
        val key = "AIzaSyEXAMPLEonly-for-validation_12345"
        assertFalse(SkyPhoneCloud.validPersonalKey("Bearer " + key))
        assertFalse(SkyPhoneCloud.validPersonalKey("GEMINI_API_KEY=" + key))
        assertFalse(SkyPhoneCloud.validPersonalKey("x-goog-api-key: " + key))
    }
    @Test fun newAuthKeyPunctuationIsAllowedButNeverChanged() {
        val key = "auth.key+with/slashes=and:punctuation_12345678"
        assertTrue(SkyPhoneCloud.validPersonalKey(key))
        assertEquals(key, SkyPhoneCloud.normalizePersonalKey(key))
        assertTrue(SkyPhoneCloud.validPersonalKey("AIzaSyEXAMPLEonly-for-validation_12345."))
    }
    @Test fun unsafeNonAsciiOrHeaderControlIsRejected() {
        assertFalse(SkyPhoneCloud.validPersonalKey("abcdefghi" + '\u0000' + "jklmnopqrstuv"))
        assertFalse(SkyPhoneCloud.validPersonalKey("abcdefghi" + '\u2022' + "jklmnopqrstuv"))
        assertFalse(SkyPhoneCloud.validPersonalKey("projects/216507061862"))
    }
    @Test fun personalKeyRejectsDangerousCharactersAndMissingValues() {
        assertFalse(SkyPhoneCloud.validPersonalKey(""))
        assertFalse(SkyPhoneCloud.validPersonalKey("AIza nada"))
        assertFalse(SkyPhoneCloud.validPersonalKey("abc\nInjected"))
        assertTrue(SkyPhoneCloud.validPersonalKey("AIzaSyEXAMPLEonly-for-validation_12345"))
    }
}
