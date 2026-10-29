package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyGroqCloudTest {
    @Test fun modelIsPinnedToSupportedFastTextModel() {
        assertEquals("openai/gpt-oss-20b", SkyGroqCloud.MODEL)
        assertEquals("openai/gpt-oss-20b", SkyGroqCloud.selectModel(listOf("openai/gpt-oss-20b", "openai/gpt-oss-120b")))
        assertEquals("openai/gpt-oss-120b", SkyGroqCloud.selectModel(listOf("openai/gpt-oss-120b")))
        assertNull(SkyGroqCloud.selectModel(listOf("llama-3.1-8b-instant")))
    }

    @Test fun keyValidationDoesNotLogOrAcceptHeaderWrappers() {
        val key = "gsk_test_for_unit_tests_only_12345678901234567890"
        assertTrue(SkyGroqCloud.validKey(key))
        assertFalse(SkyGroqCloud.validKey("Bearer " + key))
        assertFalse(SkyGroqCloud.validKey("GROQ_API_KEY=" + key))
        assertFalse(SkyGroqCloud.validKey("abc\nxyz"))
    }

    @Test fun greetingsNeedNoInternetAndDoNotClaimExternalActions() {
        assertNotNull(SkyLocalConversation.reply("Qué onda Sky"))
        assertNotNull(SkyLocalConversation.reply("¡Hola, SKY!"))
        assertNotNull(SkyLocalConversation.reply("Buenos días"))
        assertNull(SkyLocalConversation.reply("¿Qué noticias hay hoy en Nicaragua?"))
        assertNull(SkyLocalConversation.reply("Abre YouTube y reproduce una canción"))
    }

    @Test fun currentFactsAreMarkedForLiveVerification() {
        assertTrue(SkyPhoneCloud.requiresLiveVerification("Noticias de Nicaragua de hoy"))
        assertTrue(SkyPhoneCloud.requiresLiveVerification("Precio actual del dólar"))
        assertFalse(SkyPhoneCloud.requiresLiveVerification("Qué onda Sky"))
        assertFalse(SkyPhoneCloud.requiresLiveVerification("Escribe una presentación"))
    }
}
