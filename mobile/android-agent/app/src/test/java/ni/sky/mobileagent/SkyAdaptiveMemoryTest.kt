package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyAdaptiveMemoryTest {
    @Test fun accentsAndPunctuationUseSameLocalKey() {
        assertEquals(SkyAdaptiveMemory.fingerprint("¿Cómo preparar una rúbrica?"),
            SkyAdaptiveMemory.fingerprint("como preparar una rubrica"))
    }
    @Test fun currentFactsAreNeverReplayedFromCache() {
        assertNotNull(SkyAdaptiveMemory.ineligibleReason("¿Cuál es el clima de hoy?"))
        assertNotNull(SkyAdaptiveMemory.ineligibleReason("Precio actual del dólar"))
    }
    @Test fun localDeviceCommandsAreNotLearnedAsCompleted() {
        assertNotNull(SkyAdaptiveMemory.ineligibleReason("Abre YouTube"))
        assertNotNull(SkyAdaptiveMemory.ineligibleReason("Reproduce música"))
        assertNotNull(SkyAdaptiveMemory.ineligibleReason("Recuerda que me gusta leer"))
    }
    @Test fun approvedReusableStaticQuestionIsEligible() {
        assertNull(SkyAdaptiveMemory.ineligibleReason("Explícame qué es un algoritmo"))
        assertNull(SkyAdaptiveMemory.ineligibleReason("Dame un ejemplo de una rúbrica"))
    }
    @Test fun spanishVoiceCorrectionIsParsedLocally() {
        assertEquals("Una rúbrica evalúa criterios.",
            SkyAdaptiveMemory.correctionFromCommand(
                "SKY, corregí tu última respuesta: Una rúbrica evalúa criterios."))
        assertEquals("", SkyAdaptiveMemory.correctionFromCommand(
            "corrige tu última respuesta"))
        assertNull(SkyAdaptiveMemory.correctionFromCommand(
            "¿Qué es una rúbrica?"))
    }
    @Test fun deepModelCommandIsNeverMistakenForCorrection() {
        assertNull(SkyAdaptiveMemory.correctionFromCommand(
            "Modo profundo: Explicá un Transformer"))
    }

    @Test fun secretsAreNotStoredAsAnswers() {
        assertNotNull(SkyAdaptiveMemory.ineligibleReason(
            "Mi token: abcdefg12345 ¿es seguro?"))
    }
}
