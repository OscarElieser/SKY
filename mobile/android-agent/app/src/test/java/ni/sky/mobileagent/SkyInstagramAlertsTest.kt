package ni.sky.mobileagent
import org.junit.Assert.*
import org.junit.Test
class SkyInstagramAlertsTest {
 @Test fun naturalVoiceCommandsWork() {
   assertEquals(SkyInstagramAlerts.Command.READ, SkyInstagramAlerts.command("SKY revisá mis mensajes de Instagram"))
   assertEquals(SkyInstagramAlerts.Command.READ, SkyInstagramAlerts.command("SKY qué mensajes tengo en Instagram"))
   assertEquals(SkyInstagramAlerts.Command.ENABLE, SkyInstagramAlerts.command("SKY activá avisos de Instagram"))
   assertEquals(SkyInstagramAlerts.Command.DISABLE, SkyInstagramAlerts.command("SKY apagá los avisos de Instagram"))
   assertEquals(SkyInstagramAlerts.Command.NONE, SkyInstagramAlerts.command("SKY pon música en YouTube"))
 }
 @Test fun onlyActualMessagesAreAnnounced() {
   assertEquals("No encontré mensajes recibidos en el historial reciente de Instagram.",
     SkyInstagramAlerts.summary(SkyInstagramAlerts.Snapshot("12345", emptyList())))
   val data = SkyInstagramAlerts.Snapshot("12345",
     listOf(SkyInstagramAlerts.Message("event1", "67890", "Hola SKY", 99L)))
   assertTrue(SkyInstagramAlerts.summary(data).contains("Hola SKY"))
 }
}