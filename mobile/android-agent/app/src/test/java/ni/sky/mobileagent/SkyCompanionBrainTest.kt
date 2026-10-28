package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyCompanionBrainTest {
    @Test fun busCompanionIsExplicit() {
        val brain = SkyCompanionBrain()
        assertEquals(SkyCompanionBrain.Mode.OFF, brain.mode)
        val reply = brain.answer("SKY estoy en el bus")
        assertNotNull(reply)
        assertEquals(SkyCompanionBrain.Mode.BUS, brain.mode)
        assertNotNull(brain.nextCheckIn())
        brain.answer("SKY desactiva modo acompañante")
        assertEquals(SkyCompanionBrain.Mode.OFF, brain.mode)
        assertNull(brain.nextCheckIn())
    }

    @Test fun walkingCompanionPrioritizesAttention() {
        val brain = SkyCompanionBrain()
        val r = brain.answer("SKY voy caminando")!!
        assertEquals(SkyCompanionBrain.Mode.WALKING, brain.mode)
        assertTrue(r.spoken.contains("camino"))
    }

    @Test fun jokesAndWhistlesNeedExplicitRequests() {
        val brain = SkyCompanionBrain()
        assertTrue(brain.answer("SKY contame un chiste")!!.spoken.isNotBlank())
        assertTrue(brain.answer("SKY silba")!!.whistle)
        assertNull(brain.answer("Explicame la teoría de la evolución"))
        assertFalse(brain.answer("SKY sorprendeme")!!.whistle)
    }
}
