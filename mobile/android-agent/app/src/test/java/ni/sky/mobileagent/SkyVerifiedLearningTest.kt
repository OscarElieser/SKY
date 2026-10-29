package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

/** Ninguna prueba usa voz, archivos personales, red ni permisos Android. */
class SkyVerifiedLearningTest {
    @Test fun sentCommandsMustNeverTrain() {
        assertNull(SkyVerifiedLearning.outcome("SENT"))
        assertNull(SkyVerifiedLearning.outcome("LAUNCHED"))
        assertNull(SkyVerifiedLearning.outcome("REQUESTED"))
        assertNull(SkyVerifiedLearning.outcome("CANCELLED"))
        assertNull(SkyVerifiedLearning.outcome("UNKNOWN"))
    }

    @Test fun onlyVerifiedAndFailedOutcomesHaveLabels() {
        assertEquals(true, SkyVerifiedLearning.outcome("VERIFIED_LOCAL"))
        assertEquals(true, SkyVerifiedLearning.outcome("VERIFICADA_LOCAL"))
        assertEquals(false, SkyVerifiedLearning.outcome("FAILED"))
        assertEquals(false, SkyVerifiedLearning.outcome("FALLIDA"))
    }

    @Test fun verifiedFeedbackChangesOnlyLocalLearningWeights() {
        val initial = 0.0
        val positive = SkyVerifiedLearning.train(initial, true)
        val negative = SkyVerifiedLearning.train(initial, false)
        assertTrue(positive > initial)
        assertTrue(negative < initial)
        assertTrue(SkyVerifiedLearning.sigmoid(positive) > 0.5)
        assertTrue(SkyVerifiedLearning.sigmoid(negative) < 0.5)
    }

    @Test fun repeatedTrainingIsBounded() {
        var positive = 0.0
        var negative = 0.0
        repeat(20000) {
            positive = SkyVerifiedLearning.train(positive, true)
            negative = SkyVerifiedLearning.train(negative, false)
        }
        assertTrue(positive in -5.0..5.0)
        assertTrue(negative in -5.0..5.0)
        assertTrue(SkyVerifiedLearning.sigmoid(positive) < 1.0)
        assertTrue(SkyVerifiedLearning.sigmoid(negative) > 0.0)
    }

    @Test fun learningNeverInventsSensitiveDataOrRolePrivileges() {
        assertEquals("notas", SkyVerifiedLearning.category("Guardar nota local"))
        assertEquals("aplicaciones", SkyVerifiedLearning.category("Abrir YouTube"))
        assertEquals("musica", SkyVerifiedLearning.category("Música: canción"))
        assertEquals("mensajeria", SkyVerifiedLearning.category("Enviar mensaje"))
    }

    @Test fun actualAudioControlIsClassifiedCorrectlyWithoutLearningFromDispatch() {
        assertEquals("musica", SkyVerifiedLearning.category("Control Android VOLUME_UP"))
        assertEquals("musica", SkyVerifiedLearning.category("Control Android PAUSE"))
        assertEquals("musica", SkyVerifiedLearning.category("Control Android NEXT"))
        assertNull(SkyVerifiedLearning.outcome("SENT"))
        assertEquals(true, SkyVerifiedLearning.outcome("VERIFIED_LOCAL"))
        assertEquals(false, SkyVerifiedLearning.outcome("FAILED"))
    }

    @Test fun rejectsUnsafeLearningRates() {
        try {
            SkyVerifiedLearning.train(0.0, true, rate = 0.3)
            fail("Debió rechazar una tasa de aprendizaje mayor al límite")
        } catch (_: IllegalArgumentException) {}
    }
}
