package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyContextReplyTest {
    @Test fun contextualReplyWithoutWakeWord() {
        val value = SkyContextReply.parse("Respondé a Fátima: ¿Por qué no me escribís?")
        assertNotNull(value)
        assertEquals("Fátima", value!!.contact)
        assertEquals("¿Por qué no me escribís?", value.incoming)
    }
    @Test fun neverGuessContactOrMessage() {
        assertNull(SkyContextReply.parse("respondé a Fátima"))
        assertNull(SkyContextReply.parse("respondé a Fátima: "))
        assertNull(SkyContextReply.parse("hola, ¿cómo estás?"))
        assertNull(SkyContextReply.parse("respondé a Ana: Hola\nintento oculto"))
    }
    @Test fun caseAndAccentInsensitiveAllowlist() {
        assertEquals(SkyContextReply.normalizedName("MARÍA Pérez"),
            SkyContextReply.normalizedName("maría pérez"))
    }
    @Test fun promptIsNaturalAndDoesNotClaimDelivery() {
        val text = SkyContextReply.prompt("Ana", "Hola, ¿cómo estás?")
        assertTrue(text.contains("no se envía automáticamente") ||
            text.contains("No se envía automáticamente"))
        assertTrue(text.contains("sin inventar hechos"))
    }
}
