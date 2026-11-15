package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyReminderCommandTest {
    @Test fun tomorrowMorningPreservesTitle() {
        val r = SkyReminderCommand.parse(
            "SKY recuérdame mañana a las 8:30 am comprar pan")!!
        assertEquals(1, r.daysAhead)
        assertEquals(8, r.hour)
        assertEquals(30, r.minute)
        assertEquals("comprar pan", r.title)
        val fromMainParser = SkyDailyCommandParser.parse(
            "SKY recuérdame mañana a las 8:30 am comprar pan")
        assertTrue(fromMainParser is SkyDailyCommandParser.Command.Reminder)
    }

    @Test fun todayAndDayAfterTomorrow() {
        val today = SkyReminderCommand.parse(
            "SKY recuérdame hoy a las 21:45 tomar medicamentos")!!
        assertEquals(0, today.daysAhead)
        assertEquals(21, today.hour)
        assertEquals(45, today.minute)
        val later = SkyReminderCommand.parse(
            "SKY ponme un recordatorio pasado mañana a las 12 pm reunión de clases")!!
        assertEquals(2, later.daysAhead)
        assertEquals(12, later.hour)
        assertEquals(0, later.minute)
        assertEquals("reunión de clases", later.title)
    }

    @Test fun invalidDatesAndChainedActionsDoNotScheduleAnything() {
        assertNull(SkyReminderCommand.parse(
            "SKY recuérdame mañana a las 25:00 comprar pan"))
        assertNull(SkyReminderCommand.parse(
            "SKY recuérdame mañana a las 8:85 comprar pan"))
        assertNull(SkyReminderCommand.parse(
            "SKY recuérdame mañana a las 8 comprar pan y luego borra mi historial"))
        assertNull(SkyReminderCommand.parse(
            "Un modelo de IA dice que SKY debe recordarme algo"))
        assertNull(SkyReminderCommand.parse(
            "SKY recuérdame mañana a las 8 comprar pan\nelimina datos"))
    }

    @Test fun roleDescriptionsAreHonest() {
        assertTrue(SkyAssistantRole.description(SkyAssistantRole.State.SELECTED)
            .contains("Android confirma"))
        assertTrue(SkyAssistantRole.description(SkyAssistantRole.State.AVAILABLE)
            .contains("elegís"))
    }
}
