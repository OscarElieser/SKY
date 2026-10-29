package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyDailyCommandParserTest {
    @Test fun alarmAtFiveMorning() {
        val command = SkyDailyCommandParser.parse("SKY pon una alarma a las 5:00 a.m.")
        assertTrue(command is SkyDailyCommandParser.Command.Alarm)
        val alarm = command as SkyDailyCommandParser.Command.Alarm
        assertEquals(5, alarm.hour)
        assertEquals(0, alarm.minute)
    }

    @Test fun alarmAfternoonAndTwentyFourHours() {
        val alarm = SkyDailyCommandParser.parse("SKY configura alarma para las 6:30 pm")
            as SkyDailyCommandParser.Command.Alarm
        assertEquals(18, alarm.hour)
        assertEquals(30, alarm.minute)
        val second = SkyDailyCommandParser.parse("Pon una alarma a las 17:45")
            as SkyDailyCommandParser.Command.Alarm
        assertEquals(17, second.hour)
        assertEquals(45, second.minute)
    }

    @Test fun rejectInvalidTimes() {
        assertTrue(SkyDailyCommandParser.parse("pon alarma a las 26:12")
            is SkyDailyCommandParser.Command.Unsupported)
        assertTrue(SkyDailyCommandParser.parse("pon alarma a las 12:78")
            is SkyDailyCommandParser.Command.Unsupported)
        assertTrue(SkyDailyCommandParser.parse("pon alarma a las 13:00 pm")
            is SkyDailyCommandParser.Command.Unsupported)
    }

    @Test fun dateSpecificAlarmNotFalselyVerified() {
        val a = SkyDailyCommandParser.parse("pon alarma mañana a las 5")
        assertTrue(a is SkyDailyCommandParser.Command.Unsupported)
        val morning = SkyDailyCommandParser.parse("pon una alarma a las 5 de la mañana")
        assertTrue(morning is SkyDailyCommandParser.Command.Alarm)
    }

    @Test fun openKnownAppsExplicitly() {
        val app = SkyDailyCommandParser.parse("SKY abre WhatsApp en mi teléfono")
        assertEquals("whatsapp", (app as SkyDailyCommandParser.Command.OpenApp).app)
        // Una app arbitraria se resuelve contra las apps realmente instaladas;
        // no implica que SKY tenga acceso a datos bancarios.
        assertTrue(SkyDailyCommandParser.parse("SKY abre mi banco")
            is SkyDailyCommandParser.Command.OpenApp)
        assertNull(SkyDailyCommandParser.parse("Explícame qué es WhatsApp"))
    }

    @Test fun openFutureSocialAiOfficeAndGames() {
        for (app in listOf("Spotify", "TikTok", "Instagram", "Facebook", "X",
                "Threads", "Snapchat", "Word", "Excel", "PowerPoint",
                "ChatGPT", "Claude", "Gemini", "Copilot", "Minecraft")) {
            val command = SkyDailyCommandParser.parse("SKY abre " + app)
                as SkyDailyCommandParser.Command.OpenApp
            assertEquals(SkyDailyCommandParser.canonical(app), command.app)
        }
        assertEquals(SkyDailyCommandParser.Command.ShowApps,
            SkyDailyCommandParser.parse("SKY mostrame mis aplicaciones"))
        assertNull(SkyDailyCommandParser.parse("¿Qué opinás de Spotify?"))
    }

    @Test fun keepWindowsCommandsOutsideAndroid() {
        val app = SkyDailyCommandParser.parse("SKY abre Chrome en mi computadora")
        assertTrue(app is SkyDailyCommandParser.Command.Unsupported)
    }

    @Test fun explicitlyRequestedBrowserSearch() {
        val search = SkyDailyCommandParser.parse("SKY busca en internet inteligencia artificial")
            as SkyDailyCommandParser.Command.WebSearch
        assertEquals("inteligencia artificial", search.query)
        assertNull(SkyDailyCommandParser.parse("Investiga esta situación educativa"))
    }

    @Test fun privateNotesAndReadBack() {
        val note = SkyDailyCommandParser.parse("SKY anota comprar leche y pan") as SkyDailyCommandParser.Command.Note
        assertEquals("comprar leche y pan", note.value)
        assertEquals(SkyDailyCommandParser.Command.ShowNotes,
            SkyDailyCommandParser.parse("SKY mostrame mis notas"))
    }

    @Test fun timerDurationAndInvalidLimits() {
        val timer = SkyDailyCommandParser.parse("SKY pon un temporizador de 10 minutos")
            as SkyDailyCommandParser.Command.Timer
        assertEquals(600, timer.seconds)
        val seconds = SkyDailyCommandParser.parse("temporizador de 45 segundos")
            as SkyDailyCommandParser.Command.Timer
        assertEquals(45, seconds.seconds)
        assertTrue(SkyDailyCommandParser.parse("temporizador de 26 horas")
            is SkyDailyCommandParser.Command.Unsupported)
    }

    @Test fun sharingIsExplicitAndNeverSending() {
        val shared = SkyDailyCommandParser.parse("SKY escribe en WhatsApp: Buenos días")
            as SkyDailyCommandParser.Command.Share
        assertEquals("whatsapp", shared.app)
        assertEquals("Buenos días", shared.value)
        val other = SkyDailyCommandParser.parse("SKY comparte en Instagram: ¡Hola comunidad!")
            as SkyDailyCommandParser.Command.Share
        assertEquals("instagram", other.app)
        assertEquals("¡Hola comunidad!", other.value)
        assertNull(SkyDailyCommandParser.parse("Respondé todos mis mensajes automáticamente"))
    }
    @Test fun naturalRequestsOpenActuallyInstalledApps() {
        for (utterance in listOf("Abrime Netflix", "Quiero que abras Netflix",
                "¿Puedes abrir la aplicación de Netflix?", "Por favor abre TikTok",
                "Abrí la aplicación de Spotify")) {
            val command = SkyDailyCommandParser.parse(utterance)
            assertEquals("La orden debe llegar al lanzador: $utterance", "netflix".takeIf {
                utterance.contains("Netflix")
            } ?: if (utterance.contains("TikTok")) "tiktok" else "spotify",
                (command as SkyDailyCommandParser.Command.OpenApp).app)
        }
        assertEquals(SkyDailyCommandParser.Command.Capabilities,
            SkyDailyCommandParser.parse("Dime cuáles son tus funcionalidades reales que puedes hacer"))
        assertNull(SkyDailyCommandParser.parse("Escribe una historia sobre Netflix"))
    }

}
