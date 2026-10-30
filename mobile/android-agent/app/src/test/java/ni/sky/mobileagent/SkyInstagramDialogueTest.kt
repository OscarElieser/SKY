package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Test

class SkyInstagramDialogueTest {
    @Test fun acceptsNaturalSpanishAfterAsk() {
        assertEquals(SkyInstagramDialogue.Answer.YES,
            SkyInstagramDialogue.answer("Sí, revisalos."))
        assertEquals(SkyInstagramDialogue.Answer.YES,
            SkyInstagramDialogue.answer("SKY, claro revisalo"))
        assertEquals(SkyInstagramDialogue.Answer.YES,
            SkyInstagramDialogue.answer("Dale"))
        assertEquals(SkyInstagramDialogue.Answer.NO,
            SkyInstagramDialogue.answer("Ahora no"))
        assertEquals(SkyInstagramDialogue.Answer.NO,
            SkyInstagramDialogue.answer("SKY, mejor después"))
    }

    @Test fun ignoresUnrelatedOrDangerousActions() {
        assertEquals(SkyInstagramDialogue.Answer.NONE,
            SkyInstagramDialogue.answer("Sky envía el mensaje ya"))
        assertEquals(SkyInstagramDialogue.Answer.NONE,
            SkyInstagramDialogue.answer("Abre YouTube"))
        assertEquals(SkyInstagramDialogue.Answer.NONE,
            SkyInstagramDialogue.answer("Borra mis conversaciones"))
    }
}
