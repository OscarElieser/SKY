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
        assertNull(SkyDailyCommandParser.parse("pon alarma a las 26:12"))
        assertNull(SkyDailyCommandParser.parse("pon alarma a las 12:78"))
        assertNull(SkyDailyCommandParser.parse("pon alarma a las 13:00 pm"))
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
        assertNull(SkyDailyCommandParser.parse("SKY abre mi banco"))
        assertNull(SkyDailyCommandParser.parse("Explícame qué es WhatsApp"))
    }

    @Test fun keepWindowsCommandsOutsideAndroid() {
        val app = SkyDailyCommandParser.parse("SKY abre Chrome en mi computadora")
        assertTrue(app is SkyDailyCommandParser.Command.Unsupported)
    }

    @Test fun privateNotesAndReadBack() {
        val note = SkyDailyCommandParser.parse("SKY anota comprar leche y pan") as SkyDailyCommandParser.Command.Note
        assertEquals("comprar leche y pan", note.value)
        assertEquals(SkyDailyCommandParser.Command.ShowNotes,
            SkyDailyCommandParser.parse("SKY mostrame mis notas"))
    }

    @Test fun sharingIsExplicitAndNeverSending() {
        val shared = SkyDailyCommandParser.parse("SKY escribe en WhatsApp: Buenos días")
            as SkyDailyCommandParser.Command.Share
        assertEquals("whatsapp", shared.app)
        assertEquals("Buenos días", shared.value)
        assertNull(SkyDailyCommandParser.parse("Respondé todos mis mensajes automáticamente"))
    }
}
