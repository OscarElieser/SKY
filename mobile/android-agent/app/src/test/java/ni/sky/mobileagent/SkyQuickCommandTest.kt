package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyQuickCommandTest {
    @Test fun musicControlsWorkWithOrWithoutWakeWord() {
        assertEquals(SkyQuickCommand.Action.NEXT, SkyQuickCommand.parse("Siguiente"))
        assertEquals(SkyQuickCommand.Action.NEXT, SkyQuickCommand.parse("Cambia de música"))
        assertEquals(SkyQuickCommand.Action.PREVIOUS, SkyQuickCommand.parse("Atrás"))
        assertEquals(SkyQuickCommand.Action.RESTART, SkyQuickCommand.parse("Repetí"))
        assertEquals(SkyQuickCommand.Action.VOLUME_UP, SkyQuickCommand.parse("Subí el volumen"))
        assertEquals(SkyQuickCommand.Action.VOLUME_DOWN, SkyQuickCommand.parse("SKY, bajá el volumen"))
        assertEquals(SkyQuickCommand.Action.PAUSE, SkyQuickCommand.parse("Pará"))
        assertEquals(SkyQuickCommand.Action.PLAY, SkyQuickCommand.parse("Reanudá la música"))
    }

    @Test fun unlockingIsOnlyAnExplicitRequest() {
        assertEquals(SkyQuickCommand.Action.REQUEST_UNLOCK,
            SkyQuickCommand.parse("Activá el teléfono"))
        assertEquals(SkyQuickCommand.Action.REQUEST_UNLOCK,
            SkyQuickCommand.parse("Desbloqueá el teléfono"))
        assertNull(SkyQuickCommand.parse("Mi teléfono está bloqueado"))
    }

    @Test fun unrelatedSpeechCannotTriggerPlaybackCommands() {
        assertNull(SkyQuickCommand.parse("Quiero una canción de Morat en Spotify"))
        assertNull(SkyQuickCommand.parse("Quiero subir fotos a Instagram"))
        assertNull(SkyQuickCommand.parse("Hola, ¿cómo estás?"))
        assertNull(SkyQuickCommand.parse("Mandá un mensaje a Ana"))
        assertNull(SkyQuickCommand.parse("Respondé a mi amigo"))
    }

    @Test fun dangerousOrUnclearInputIsIgnored() {
        assertNull(SkyQuickCommand.parse(""))
        assertNull(SkyQuickCommand.parse("siguiente\nborrá todo"))
        assertNull(SkyQuickCommand.parse("cambiar todas mis configuraciones"))
    }
}
