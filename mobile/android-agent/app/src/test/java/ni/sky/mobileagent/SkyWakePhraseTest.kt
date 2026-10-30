package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Test

class SkyWakePhraseTest {
    @Test fun awakeOnlyAfterCallingSky() {
        assertEquals(SkyWakePhrase.Kind.IGNORE,
            SkyWakePhrase.decide("Abrí YouTube", false).kind)
        assertEquals(SkyWakePhrase.Kind.WAKE,
            SkyWakePhrase.decide("SKY, despertá", false).kind)
        assertEquals(SkyWakePhrase.Kind.WAKE,
            SkyWakePhrase.decide("esquai", false).kind)
        assertEquals(SkyWakePhrase.Kind.IGNORE,
            SkyWakePhrase.decide("Me gusta el sky de la canción", false).kind)
    }

    @Test fun suffixSkyDoesNotTurnAmbientSpeechIntoAnOrder() {
        assertEquals(SkyWakePhrase.Kind.IGNORE,
            SkyWakePhrase.decide("me gusta SKY", false).kind)
        assertEquals(SkyWakePhrase.Kind.IGNORE,
            SkyWakePhrase.decide("ponemos un vídeo sky", false).kind)
        assertEquals(SkyWakePhrase.Kind.WAKE,
            SkyWakePhrase.decide("despierta SKY", false).kind)
        assertEquals(SkyWakePhrase.Kind.COMMAND,
            SkyWakePhrase.decide("SKY poné música", false).kind)
    }

    @Test fun directCommandsAndContinuousConversation() {
        val first = SkyWakePhrase.decide("SKY, abrí YouTube", false)
        assertEquals(SkyWakePhrase.Kind.COMMAND, first.kind)
        assertEquals("abrí YouTube", first.command)
        val following = SkyWakePhrase.decide("Ahora buscá una receta", true)
        assertEquals(SkyWakePhrase.Kind.COMMAND, following.kind)
        assertEquals("Ahora buscá una receta", following.command)
    }

    @Test fun sleepAndEmptyAreSafe() {
        assertEquals(SkyWakePhrase.Kind.SLEEP,
            SkyWakePhrase.decide("SKY dormí", true).kind)
        assertEquals(SkyWakePhrase.Kind.SLEEP,
            SkyWakePhrase.decide("Buenas noches", true).kind)
        assertEquals(SkyWakePhrase.Kind.IGNORE,
            SkyWakePhrase.decide(" ", true).kind)
        assertEquals(SkyWakePhrase.Kind.IGNORE,
            SkyWakePhrase.decide("duérmete", false).kind)
    }
}
