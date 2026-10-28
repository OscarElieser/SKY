package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyAppNameMatcherTest {
    private val sample = listOf(
        SkyAppNameMatcher.Entry("TikTok", "com.zhiliaoapp.musically"),
        SkyAppNameMatcher.Entry("Spotify", "com.spotify.music"),
        SkyAppNameMatcher.Entry("Microsoft Word", "com.microsoft.office.word"),
        SkyAppNameMatcher.Entry("Microsoft Excel", "com.microsoft.office.excel"),
        SkyAppNameMatcher.Entry("PowerPoint", "com.microsoft.office.powerpoint"),
        SkyAppNameMatcher.Entry("ChatGPT", "com.openai.chatgpt"),
        SkyAppNameMatcher.Entry("Claude", "com.anthropic.claude"),
        SkyAppNameMatcher.Entry("Gemini", "com.google.android.apps.bard"),
        SkyAppNameMatcher.Entry("X", "com.twitter.android")
    )

    @Test fun exactForInstalled() {
        assertEquals("com.spotify.music", SkyAppNameMatcher.matches("Spotify", sample)[0].packageName)
        assertEquals("com.openai.chatgpt", SkyAppNameMatcher.matches("ChatGPT", sample)[0].packageName)
        assertEquals("com.anthropic.claude", SkyAppNameMatcher.matches("Claude", sample)[0].packageName)
    }

    @Test fun aliasesAndAccents() {
        assertEquals("X", SkyAppNameMatcher.matches("Twitter", sample)[0].label)
        assertEquals("Microsoft Word", SkyAppNameMatcher.matches("Word", sample)[0].label)
        assertEquals("Microsoft Excel", SkyAppNameMatcher.matches("Excel", sample)[0].label)
        assertEquals("Gemini", SkyAppNameMatcher.matches("Geminis", sample)[0].label)
    }

    @Test fun futureAppsImmediatelyResolvable() {
        assertTrue(SkyAppNameMatcher.matches("Nuevo Juego", sample).isEmpty())
        val changed = sample + SkyAppNameMatcher.Entry("Nuevo Juego", "app.example.newgame")
        assertEquals("app.example.newgame",
            SkyAppNameMatcher.matches("Nuevo Juego", changed)[0].packageName)
    }

    @Test fun ambiguitiesMustBeShownInsteadOfGuessed() {
        val choices = listOf(
            SkyAppNameMatcher.Entry("My Game", "a"),
            SkyAppNameMatcher.Entry("Game Plus", "b")
        )
        assertEquals(2, SkyAppNameMatcher.matches("Game", choices).size)
    }

    @Test fun neverUseArbitrarySubstringsOrUnknownApps() {
        assertTrue(SkyAppNameMatcher.matches("Tik", sample).isEmpty())
        assertTrue(SkyAppNameMatcher.matches("Banco no instalado", sample).isEmpty())
    }
}
