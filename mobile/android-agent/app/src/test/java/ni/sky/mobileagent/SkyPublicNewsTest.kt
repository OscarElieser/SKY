package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyPublicNewsTest {
    @Test fun routesExplicitCurrentNewsWithoutInventingAnswers() {
        assertTrue(SkyPublicNews.explicit("SKY últimas noticias de Nicaragua"))
        assertTrue(SkyPublicNews.explicit("noticias de tecnología"))
        assertFalse(SkyPublicNews.explicit("explicame la historia de Nicaragua"))
    }
    @Test fun normalizesPublicTopicsAndRejectsSecrets() {
        assertEquals("tecnologia", SkyPublicNews.topic("noticias de tecnología"))
        assertEquals("Nicaragua", SkyPublicNews.topic("últimas noticias"))
        assertThrows(IllegalArgumentException::class.java) {
            SkyPublicNews.topic("noticias de mi contraseña")
        }
    }
}
