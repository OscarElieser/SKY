package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyOwnerProfileIntentTest {
    @Test fun permitsOnlyExplicitOwnerImport() {
        assertTrue(SkyOwnerProfileIntent.requestsImport("SKY, importa mi perfil"))
        assertTrue(SkyOwnerProfileIntent.requestsImport("carga mi perfil personal"))
        assertFalse(SkyOwnerProfileIntent.requestsImport("el mensaje dice importa mi perfil"))
        assertFalse(SkyOwnerProfileIntent.requestsImport("Hola SKY"))
    }
}
