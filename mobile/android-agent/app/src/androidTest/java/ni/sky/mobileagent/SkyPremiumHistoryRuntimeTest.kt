package ni.sky.mobileagent

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.ByteArrayOutputStream

/**
 * Pruebas SQLite dentro de Android. No borra el historial del usuario.
 * Se ejecutan en emulador de CI; nunca importan una base privada.
 */
@RunWith(AndroidJUnit4::class)
class SkyPremiumHistoryRuntimeTest {
    private val app get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun premiumHistoryPreservesMessagesAndUpdatesMetadata() {
        SkyConversationArchive(app).use { archive ->
            val question = "SKY UI prueba temporal " + System.nanoTime()
            val original = archive.append(question, "Respuesta protegida por prueba", "Groq · prueba")
            try {
                assertTrue(original.id > 0)
                assertTrue(archive.rename(original.id, "Consulta favorita de SKY"))
                assertTrue(archive.setFavorite(original.id, true))
                val item = archive.page("Consulta favorita de SKY", limit = 25,
                    filter = "Favoritos").firstOrNull { it.id == original.id }
                assertNotNull("El favorito debe poder recuperarse", item)
                assertEquals(original.question, item!!.question)
                assertEquals("Respuesta protegida por prueba", item.answer)
                assertTrue(item.favorite)
                assertTrue(archive.page(question, filter = "Groq")
                    .any { it.id == original.id })
                assertTrue(archive.page(question, filter = "Hoy")
                    .any { it.id == original.id })
                assertTrue(archive.setFavorite(original.id, false))
                assertFalse(archive.page(question, filter = "Favoritos")
                    .any { it.id == original.id })
                val export = ByteArrayOutputStream()
                archive.writeJson(export)
                assertTrue(export.toString("UTF-8").contains("Consulta favorita de SKY"))
            } finally {
                archive.delete(original.id)
            }
        }
    }

    @Test fun regularHistoryStillWorksAfterAdditiveMigration() {
        SkyConversationArchive(app).use { archive ->
            val original = archive.append("Consulta de compatibilidad SKY",
                "La respuesta no cambia", "Gemini")
            try {
                val found = archive.page("compatibilidad SKY")
                    .firstOrNull { it.id == original.id }
                assertNotNull(found)
                assertEquals(original.answer, found!!.answer)
                assertEquals(original.title, found.title)
                assertTrue(archive.page("compatibilidad SKY", filter = "Gemini")
                    .any { it.id == original.id })
            } finally {
                archive.delete(original.id)
            }
        }
    }
}
