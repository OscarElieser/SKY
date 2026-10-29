package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SkyConversationArchiveTest {
    @Test fun titleUsesReadableQuestionInsteadOfGenericConversation() {
        assertEquals("Investigación sobre Nicaragua",
            SkyConversationArchive.titleFor("¿investigación sobre Nicaragua?"))
    }

    @Test fun titleRejectsEmptyQueryAndLimitsLength() {
        assertEquals("Consulta sin título", SkyConversationArchive.titleFor("  ¿ ¡   "))
        val title = SkyConversationArchive.titleFor("A".repeat(200))
        assertTrue(title.length <= 73)
        assertTrue(title.endsWith("…"))
    }

    @Test fun titleKeepsNaturalAccentsAndNormalizesSpaces() {
        assertEquals("Qué clima hará mañana",
            SkyConversationArchive.titleFor("¿qué    clima hará mañana?"))
    }
}
