package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyMessagingIntentTest {
    @Test fun userWhatsAppExample() {
        val raw = "abre el WhatsApp y manda un mensaje a Fátima Michell cárdenas Narváez: y decirle hola porque estoy triste te extraño algo así o tu mejorarlo"
        val draft = SkyMessagingIntent.parse(raw)
        assertNotNull(draft)
        assertEquals("Fátima Michell cárdenas Narváez", draft!!.recipient)
        assertTrue(draft.polish)
        assertTrue(SkyMessagingIntent.preparedText(draft).contains("te extraño"))
    }
    @Test fun dictation() {
        val draft = SkyMessagingIntent.parse("SKY, envía un mensaje a María diciendo Llegaré mañana")
        assertEquals("María", draft?.recipient)
        assertEquals("Llegaré mañana", draft?.body)
        assertFalse(draft!!.polish)
    }
    @Test fun missingContactOrMessageMustNotLaunch() {
        assertNull(SkyMessagingIntent.parse("abre WhatsApp"))
        assertNull(SkyMessagingIntent.parse("manda un mensaje a María"))
        assertNull(SkyMessagingIntent.parse("envía un mensaje a Ana: "))
        assertNull(SkyMessagingIntent.parse("envía un mensaje a Ana: hola\nborrar"))
    }
    @Test fun preserveExactApprovedText() {
        assertEquals("Hola", SkyMessagingIntent.preparedText(
            SkyMessagingIntent.parse("manda un mensaje a Ana: Hola")!!))
    }
}
