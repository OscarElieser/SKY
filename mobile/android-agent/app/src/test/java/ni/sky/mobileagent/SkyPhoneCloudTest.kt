package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Pruebas sin credenciales, ni red, ni dependencia de Windows. */
class SkyPhoneCloudTest {
    @Test fun shortPublicQuestionLimitsOnlyOutputTokens() {
        assertEquals(300, SkyPhoneCloud.responseTokenLimit(
            "SKY, explícame en dos oraciones qué es la fotosíntesis"))
        assertEquals(400, SkyPhoneCloud.responseTokenLimit(
            "¿Qué es la fotosíntesis?"))
        assertEquals(3500, SkyPhoneCloud.responseTokenLimit(
            "Redacta un documento con mi proyecto y sus objetivos"))
        assertEquals(3500, SkyPhoneCloud.responseTokenLimit(
            "Explica paso a paso cómo implementar un modelo de lenguaje"))
        assertEquals(3500, SkyPhoneCloud.responseTokenLimit(
            "Abrí WhatsApp y escribe un mensaje"))
        assertEquals(3500, SkyPhoneCloud.responseTokenLimit(
            "Investiga estas cuatro fuentes científicas y prepara una bibliografía"))
    }

    @Test fun longFormAnswersGetEnoughOutputBudget() {
        assertEquals(3500, SkyPhoneCloud.responseTokenLimit(
            "Redacta el documento completo de inteligencia artificial en Word"))
        assertEquals(1200, SkyPhoneCloud.responseTokenLimit(
            "Contame un chiste sencillo"))
    }

    @Test fun modelIsPinnedToKnownStableGemini() {
        assertEquals("gemini-3.5-flash-lite", SkyPhoneCloud.MODEL)
    }
    @Test fun keyErrorsExplainProjectIdWithoutLeakingSecrets() {
        val id = "projects/216507061862"
        assertTrue(SkyPhoneCloud.personalKeyProblem(id)!!.contains("identificador del proyecto"))
        assertFalse(SkyPhoneCloud.validPersonalKey(id))
        assertTrue(SkyPhoneCloud.personalKeyProblem("Bearer abcdefghijklmnopqrstuvwxyz")!!.contains("únicamente"))
        assertTrue(SkyPhoneCloud.personalKeyProblem("TESTSyEXAMPLEonly-for-validation_12345") == null)
    }
    @Test fun keyTrimsClipboardPaddingAndRejectsInBandWhitespace() {
        val valid = "TESTSyEXAMPLEonly-for-validation_12345"
        assertEquals(valid, SkyPhoneCloud.normalizePersonalKey("  " + valid + "\u200B"))
        assertTrue(SkyPhoneCloud.personalKeyProblem("  " + valid + "\u200B") == null)
        assertEquals("TESTEXAMPLEonly-for-validation_12345",
            SkyPhoneCloud.normalizePersonalKey("TEST  EXAMPLEonly-for-validation_12345"))
    }
    @Test fun clipboardInvisibleMarksAreRemovedEvenInsideKey() {
        val key = "TESTSyEXAMPLEonly-for-validation_12345"
        val clipboard = " \u200B" + key.take(8) + "\u200B \u00A0\uFEFF" + key.drop(8) + "\u200E\n"
        assertEquals(key, SkyPhoneCloud.normalizePersonalKey(clipboard))
        assertTrue(SkyPhoneCloud.validPersonalKey(clipboard))
    }
    @Test fun clipboardWrapperIsNotSilentlyAccepted() {
        val key = "TESTSyEXAMPLEonly-for-validation_12345"
        assertFalse(SkyPhoneCloud.validPersonalKey("Bearer " + key))
        assertFalse(SkyPhoneCloud.validPersonalKey("GEMINI_API_KEY=" + key))
        assertFalse(SkyPhoneCloud.validPersonalKey("x-goog-api-key: " + key))
    }
    @Test fun newAuthKeyPunctuationIsAllowedButNeverChanged() {
        val key = "auth.key+with/slashes=and:punctuation_12345678"
        assertTrue(SkyPhoneCloud.validPersonalKey(key))
        assertEquals(key, SkyPhoneCloud.normalizePersonalKey(key))
        assertTrue(SkyPhoneCloud.validPersonalKey("TESTSyEXAMPLEonly-for-validation_12345."))
    }
    @Test fun unsafeNonAsciiOrHeaderControlIsRejected() {
        assertFalse(SkyPhoneCloud.validPersonalKey("abcdefghi" + '\u0000' + "jklmnopqrstuv"))
        assertFalse(SkyPhoneCloud.validPersonalKey("abcdefghi" + '\u2022' + "jklmnopqrstuv"))
        assertFalse(SkyPhoneCloud.validPersonalKey("projects/216507061862"))
    }
    @Test fun personalKeyRejectsDangerousCharactersAndMissingValues() {
        assertFalse(SkyPhoneCloud.validPersonalKey(""))
        assertFalse(SkyPhoneCloud.validPersonalKey("TEST nada"))
        assertFalse(SkyPhoneCloud.validPersonalKey("abc\nInjected"))
        assertTrue(SkyPhoneCloud.validPersonalKey("TESTSyEXAMPLEonly-for-validation_12345"))
    }
    @Test fun academicYearAndEmotionalClimateAreNotLiveWebQueries() {
        assertFalse(SkyPhoneCloud.requiresLiveVerification(
            "Desarrolla una tesis de informática educativa en 2026"))
        assertFalse(SkyPhoneCloud.requiresLiveVerification(
            "Estudia el clima emocional en el aula universitaria"))
        assertFalse(SkyPhoneCloud.requiresLiveVerification(
            "Tiempo disponible seis meses y cronograma del proyecto"))
        assertTrue(SkyPhoneCloud.requiresLiveVerification(
            "¿Qué clima hace hoy en Managua?"))
    }

    @Test fun changingFactsRequireWebVerification() {
        assertTrue(SkyPhoneCloud.requiresLiveVerification("¿Cuáles son las noticias de hoy?"))
        assertTrue(SkyPhoneCloud.requiresLiveVerification("Dime el precio actual del dólar"))
        assertTrue(SkyPhoneCloud.requiresLiveVerification("¿Quién es el presidente hoy?"))
        assertFalse(SkyPhoneCloud.requiresLiveVerification("Escribí un cuento original"))
        assertFalse(SkyPhoneCloud.requiresLiveVerification("Dame una receta de nacatamales"))
    }

}
