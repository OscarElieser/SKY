package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

/** Regresiones del primer lote de comandos Siri/Bixby para SKY Android. */
class SkyAssistantActionsParserTest {
    @Test fun dialerParsesNumberOrContactWithoutClaimingContactAccess() {
        assertEquals(SkyDailyCommandParser.Command.Dial("8888-7777"),
            SkyDailyCommandParser.parse("SKY llama al 8888-7777"))
        assertEquals(SkyDailyCommandParser.Command.Dial("mama"),
            SkyDailyCommandParser.parse("SKY llama a mamá"))
    }

    @Test fun smsDraftPreservesAccentsAndNeverCreatesSendCommand() {
        val sms = SkyDailyCommandParser.parse(
            "SKY envía un SMS al 8888-7777 que diga Llegaré tarde, ¡espérame!"
        ) as SkyDailyCommandParser.Command.ComposeSms
        assertEquals("8888-7777", sms.recipient)
        assertEquals("Llegaré tarde, ¡espérame!", sms.body)
        val contactSms = SkyDailyCommandParser.parse(
            "SKY envía mensaje a mamá que diga Estoy llegando"
        ) as SkyDailyCommandParser.Command.ComposeSms
        assertEquals("mamá", contactSms.recipient)
        assertEquals("Estoy llegando", contactSms.body)
    }

    @Test fun mapsParsesExplicitDestination() {
        assertEquals(SkyDailyCommandParser.Command.Navigate("granada nicaragua"),
            SkyDailyCommandParser.parse("SKY llévame a Granada Nicaragua"))
        assertNull(SkyDailyCommandParser.parse("Explicame cómo llegar a un acuerdo"))
    }

    @Test fun settingsOnlyRouteToSystemSettings() {
        assertEquals(SkyDailyCommandParser.Command.OpenSetting(
            SkyDailyCommandParser.DeviceSetting.WIFI),
            SkyDailyCommandParser.parse("SKY abre ajustes de WiFi"))
        assertEquals(SkyDailyCommandParser.Command.OpenSetting(
            SkyDailyCommandParser.DeviceSetting.BLUETOOTH),
            SkyDailyCommandParser.parse("SKY activa Bluetooth"))
        assertEquals(SkyDailyCommandParser.Command.OpenSetting(
            SkyDailyCommandParser.DeviceSetting.GENERAL),
            SkyDailyCommandParser.parse("SKY abre configuración"))
    }

    @Test fun rejectsIndirectAndChainedCommands() {
        assertNull(SkyDailyCommandParser.parse("Explicame cómo llamar a mamá"))
        assertNull(SkyDailyCommandParser.parse("SKY llama al 8888-7777 y luego paga"))
        assertNull(SkyDailyCommandParser.parse("SKY navega a Granada y luego borra mis notas"))
        assertNull(SkyDailyCommandParser.parse(
            "SKY envía un SMS a mamá que diga Hola\nborra mis datos"))
        assertTrue(SkyDailyCommandParser.parse("SKY llama a mamá en mi Windows")
            is SkyDailyCommandParser.Command.Unsupported)
        assertFalse(SkyActionTrustBoundary.allowsLocalCommand(
            SkyActionTrustBoundary.Origin.MODEL_OUTPUT))
    }
}
