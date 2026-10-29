package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyExpressionCommandTest {
    @Test fun explicitExpressionsWorkOffline() {
        assertEquals("llora", SkyExpressionCommand.parse("SKY, llora"))
        assertEquals("triste", SkyExpressionCommand.parse("Sky ponte triste"))
        assertEquals("feliz", SkyExpressionCommand.parse("SKY, sonrí"))
        assertEquals("enojada", SkyExpressionCommand.parse("Muestra una cara enojada"))
        assertEquals("emocionada", SkyExpressionCommand.parse("Haz una cara emocionada"))
    }

    @Test fun regularConversationNeverGetsHijackedByExpressions() {
        assertNull(SkyExpressionCommand.parse("Dime cómo ayudar a un niño triste"))
        assertNull(SkyExpressionCommand.parse("¿Qué noticias hay hoy en Nicaragua?"))
        assertNull(SkyExpressionCommand.parse("Qué onda SKY"))
    }
}
