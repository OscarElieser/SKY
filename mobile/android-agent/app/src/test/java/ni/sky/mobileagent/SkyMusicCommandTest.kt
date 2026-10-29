package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyMusicCommandTest {
    @Test fun naturalCommandsNeedNoWakeWord() {
        val one = SkyMusicCommand.parse("Reproduce la canción Eres tú en Spotify")
        assertEquals("eres tu", one?.query)
        assertEquals(SkyMusicCommand.Service.SPOTIFY, one?.service)
        val two = SkyMusicCommand.parse("Ponme la canción Bonita de Morat en YouTube Music")
        assertEquals("bonita de morat", two?.query)
        assertEquals(SkyMusicCommand.Service.YOUTUBE_MUSIC, two?.service)
        assertEquals("mi cancion", SkyMusicCommand.parse("SKY, pon Mi canción")?.query)
    }
    @Test fun opensPlayerAndRequestsSpecificSongInOneCommand() {
        val youtube = SkyMusicCommand.parse("SKY, abre YouTube y reproduce la canción Bonita de Morat")
        assertEquals(SkyMusicCommand.Service.YOUTUBE, youtube?.service)
        assertEquals("bonita de morat", youtube?.query)
        val spotify = SkyMusicCommand.parse("Abrime Spotify y poné la canción de mi persona favorita")
        assertEquals(SkyMusicCommand.Service.SPOTIFY, spotify?.service)
        assertEquals("mi persona favorita", spotify?.query)
        val youtubeMusic = SkyMusicCommand.parse("Abre YouTube Music para reproducir la canción Eres tú")
        assertEquals(SkyMusicCommand.Service.YOUTUBE_MUSIC, youtubeMusic?.service)
        assertEquals("eres tu", youtubeMusic?.query)
        assertNull(SkyMusicCommand.parse("Abre YouTube y reproduce música"))
    }
    @Test fun providerCanComeBeforeTheSong() {
        val a = SkyMusicCommand.parse("Reproduce en Spotify la canción mi persona favorita")
        assertEquals(SkyMusicCommand.Service.SPOTIFY, a?.service)
        assertEquals("mi persona favorita", a?.query)
        val b = SkyMusicCommand.parse("pon en YouTube Music la canción la bicicleta")
        assertEquals(SkyMusicCommand.Service.YOUTUBE_MUSIC, b?.service)
        assertEquals("la bicicleta", b?.query)
    }
    @Test fun noAccidentalActivation() {
        assertNull(SkyMusicCommand.parse("Quiero crecer en YouTube"))
        assertNull(SkyMusicCommand.parse("mandá un mensaje por Spotify"))
        assertNull(SkyMusicCommand.parse("reproduce"))
        assertNull(SkyMusicCommand.parse("reproduce musica"))
    }
    @Test fun youtubeSearchAndDefaultChoice() {
        val result = SkyMusicCommand.parse("Buscá música de Carlos Vives en YouTube")
        assertEquals("carlos vives", result?.query)
        assertEquals(SkyMusicCommand.Service.YOUTUBE, result?.service)
        assertNull(SkyMusicCommand.parse("Escuchame, ¿cómo estás?"))
    }
    @Test fun exactNovemberRainCommandGoesToMusicController() {
        val request = SkyMusicCommand.parse("SKY reproduce November Rain en YouTube Music")
        assertEquals("november rain", request?.query)
        assertEquals(SkyMusicCommand.Service.YOUTUBE_MUSIC, request?.service)
        val explicit = SkyMusicCommand.parse("Abrí Spotify y reproducí la canción November Rain")
        assertEquals(SkyMusicCommand.Service.SPOTIFY, explicit?.service)
        assertEquals("november rain", explicit?.query)
    }

    @Test fun signedStandardVariantNeverEnablesMusicAccessibility() {
        assertFalse(BuildConfig.ENABLE_TEXT_ASSIST)
        assertFalse(SkyMusicControlService.enabled())
        assertFalse(SkyMusicControlService.arm("com.spotify.music", "november rain") { })
    }

    @Test fun researchAndLiveNewsMustNotStartMusic() {
        assertNull(SkyMusicCommand.parse("busca noticias de Nicaragua de hoy"))
        assertNull(SkyMusicCommand.parse("SKY busca información en internet"))
        assertNull(SkyMusicCommand.parse("buscame la cotización del dólar"))
        val music = SkyMusicCommand.parse("SKY busca la canción November Rain en YouTube Music")
        assertEquals("november rain", music?.query)
        assertEquals(SkyMusicCommand.Service.YOUTUBE_MUSIC, music?.service)
        assertEquals("carlos vives",
            SkyMusicCommand.parse("Buscá música de Carlos Vives en YouTube")?.query)
    }

}
