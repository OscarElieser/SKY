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

    @Test fun longDocumentIsStoredAndRecoveredWithoutCuttingAtFiveThousand() {
        SkyConversationArchive(app).use { archive ->
            val document = "Inicio del documento. " +
                "Contenido académico completo. ".repeat(250) +
                "FIN DEL DOCUMENTO."
            assertTrue(document.length > 5_000)
            val saved = archive.append("Crear documento Word temporal " + System.nanoTime(),
                document, "Groq · prueba documental")
            try {
                val loaded = archive.page(saved.title, limit = 25)
                    .firstOrNull { it.id == saved.id }
                assertNotNull(loaded)
                assertEquals(document, loaded!!.answer)
                val exported = ByteArrayOutputStream()
                SkyNativeOfficeExport.write(exported, loaded,
                    SkyNativeOfficeExport.Format.WORD)
                assertTrue("Debe generarse un DOCX ZIP", exported.toByteArray().size > 700)
            } finally {
                archive.delete(saved.id)
            }
        }
    }

    @Test fun newChatKeepsOlderSqliteEntriesAndPreservesLongPrompts() {
        SkyConversationArchive(app).use { archive ->
            val lengthy = "Proyecto de tesis: " + "Apartado académico completo. ".repeat(270)
            assertTrue(lengthy.length > 4_000)
            val old = archive.append("Conversación anterior " + System.nanoTime(),
                "Respuesta guardada", "SKY · test")
            var current: SkyConversationArchive.Entry? = null
            try {
                val cutoff = SkyChatSessionPolicy.newBoundary(old.id)
                assertFalse(SkyChatSessionPolicy.visible(old.id, cutoff))
                current = archive.append(lengthy, "Documento completo", "SKY · test")
                assertTrue(SkyChatSessionPolicy.visible(current.id, cutoff))
                // New chat changes only the visual/session boundary, not SQLite.
                val archivedOld = archive.page(old.title, limit = 25)
                    .firstOrNull { it.id == old.id }
                assertNotNull(archivedOld)
                assertEquals("Respuesta guardada", archivedOld!!.answer)
                val archivedLong = archive.page(current.title, limit = 25)
                    .firstOrNull { it.id == current.id }
                assertNotNull(archivedLong)
                assertEquals(lengthy, archivedLong!!.question)
            } finally {
                current?.let { archive.delete(it.id) }
                archive.delete(old.id)
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
