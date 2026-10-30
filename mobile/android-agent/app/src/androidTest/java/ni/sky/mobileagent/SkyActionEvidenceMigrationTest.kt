package ni.sky.mobileagent

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SkyActionEvidenceMigrationTest {
    private lateinit var context: Context

    @Before fun setUp() {
        context = InstrumentationRegistry.getInstrumentation().targetContext
        context.deleteDatabase("sky_action_evidence.db")
    }

    @After fun tearDown() {
        context.deleteDatabase("sky_action_evidence.db")
    }

    @Test fun legacyVersionOneSurvivesMigrationAndNewEventsShareOperationId() {
        val file = context.getDatabasePath("sky_action_evidence.db")
        file.parentFile?.mkdirs()
        SQLiteDatabase.openOrCreateDatabase(file, null).use { db ->
            db.execSQL("""CREATE TABLE action_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                state TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )""")
            db.execSQL("INSERT INTO action_evidence(action,state,detail,created_at) VALUES ('Anterior','FALLIDA','Prueba histórica',1234)")
            db.version = 1
        }
        SkyActionEvidence(context).use { store ->
            val old = store.recent().single()
            assertEquals("Anterior", old.action)
            assertEquals("FALLIDA", old.status)
            assertEquals(1234L, old.createdAt)
            assertEquals("legacy-" + old.id, old.operationId)

            val operation = store.newOperationId()
            store.record("Reproducir música", "SENT", "Intent aceptado", operation)
            store.record("Reproducir música", "ESTADO_DESCONOCIDO", "No comprobado", operation)
            val events = store.recent()
            assertEquals(3, events.size)
            val pair = events.filter { it.operationId == operation }
            assertEquals(2, pair.size)
            assertNotEquals(pair[0].eventId, pair[1].eventId)
            assertEquals(1, store.summary().failed)
            assertEquals(1, store.summary().sentUnverified)
            assertEquals(1, store.summary().unknown)
        }
    }

    @Test fun invalidOperationIdCannotCreateEvidence() {
        SkyActionEvidence(context).use { store ->
            try {
                store.record("Prueba", "SENT", "Test", "id-invalido")
                fail("Operation ID inválido aceptado")
            } catch (_: IllegalArgumentException) {
                assertEquals(0, store.recent().size)
            }
        }
    }
}
