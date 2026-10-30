package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyInstagramInboxRulesTest {
    @Test fun onlyExactVerifiedProfileReceivesEvents() {
        assertTrue(SkyInstagramInboxRules.belongsToProfile(
            "17841400814404664", "17841400814404664"))
        assertFalse(SkyInstagramInboxRules.belongsToProfile(
            "17841400814404664", "17841499999999999"))
        assertFalse(SkyInstagramInboxRules.belongsToProfile(
            "@chamorro.oscar", "@chamorro.oscar"))
    }

    @Test fun ownerEchoIsNotTreatedAsIncoming() {
        assertFalse(SkyInstagramInboxRules.isIncoming("123456789", "123456789"))
        assertFalse(SkyInstagramInboxRules.isIncoming("123456789", ""))
        assertTrue(SkyInstagramInboxRules.isIncoming("123456789", "987654321"))
    }

    @Test fun previewsDoNotFabricateMessages() {
        assertEquals("Mensaje sin texto o contenido multimedia",
            SkyInstagramInboxRules.preview(null))
        assertEquals("Hola SKY",
            SkyInstagramInboxRules.preview("  Hola\nSKY  "))
        assertEquals(20, SkyInstagramInboxRules.preview("A".repeat(90), 20).length)
    }

    @Test fun partialSenderIdsDoNotExposeFullIdentity() {
        assertEquals("Remitente ···12345",
            SkyInstagramInboxRules.senderLabel("1784140000012345"))
        assertEquals("Remitente no identificado",
            SkyInstagramInboxRules.senderLabel("unknown"))
    }
}
