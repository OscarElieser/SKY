package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyMusicCommandTest {
    @Test fun naturalCommandsNeedNoWakeWord() {
        val one = SkyMusicCommand.parse("Reproduce la canción Eres tú en Spotify")
        assertEquals("Eres tu", one?.query)
        assertEquals(SkyMusicCommand.Service.SPOTIFY, one?.service)
        val two = SkyMusicCommand.parse("Ponme la canción Bonita de Morat en YouTube Music")
        assertEquals("Bonita de Morat", two?.query)
        assertEquals(SkyMusicCommand.Service.YOUTUBE_MUSIC, two?.service)
        assertEquals("Mi canción", SkyMusicCommand.parse("SKY, pon Mi canción")?.query)
    }
    @Test fun noAccidentalActivation() {
        assertNull(SkyMusicCommand.parse("Quiero crecer en YouTube"))
        assertNull(SkyMusicCommand.parse("mandá un mensaje por Spotify"))
        assertNull(SkyMusicCommand.parse("reproduce"))
        assertNull(SkyMusicCommand.parse("reproduce musica"))
    }
    @Test fun youtubeSearchAndDefaultChoice() {
        val result = SkyMusicCommand.parse("Buscá música de Carlos Vives en YouTube")
        assertEquals("de Carlos Vives", result?.query)
        assertEquals(SkyMusicCommand.Service.YOUTUBE, result?.service)
        assertNull(SkyMusicCommand.parse("Escuchame, ¿cómo estás?"))
    }
}
