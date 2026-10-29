package ni.sky.mobileagent

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Historial privado del teléfono: una entrada por consulta, con fecha/hora reales
 * del dispositivo y título deducido de la pregunta. No sincroniza ni sube datos.
 */
class SkyConversationArchive(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "sky_conversations.db", null, 1) {

    data class Entry(
        val id: Long,
        val title: String,
        val question: String,
        val answer: String,
        val engine: String,
        val createdAt: Long
    ) {
        fun localTime(): String = SimpleDateFormat("dd/MM/yyyy · HH:mm", Locale("es", "NI"))
            .format(Date(createdAt))
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            engine TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        db.execSQL("CREATE INDEX idx_conversations_date ON conversations(created_at DESC)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit

    fun append(question: String, answer: String, engine: String): Entry {
        val now = System.currentTimeMillis()
        val entry = Entry(0, titleFor(question), question.take(4000),
            answer.take(5000), engine.take(120), now)
        val values = android.content.ContentValues().apply {
            put("title", entry.title)
            put("question", entry.question)
            put("answer", entry.answer)
            put("engine", entry.engine)
            put("created_at", now)
        }
        val id = writableDatabase.insertOrThrow("conversations", null, values)
        return entry.copy(id = id)
    }

    fun recent(limit: Int = 150): List<Entry> {
        val result = ArrayList<Entry>()
        readableDatabase.query(
            "conversations", arrayOf("id", "title", "question", "answer", "engine", "created_at"),
            null, null, null, null, "id DESC", limit.coerceIn(1, 500).toString()
        ).use { cursor ->
            while (cursor.moveToNext()) {
                result.add(Entry(cursor.getLong(0), cursor.getString(1),
                    cursor.getString(2), cursor.getString(3), cursor.getString(4),
                    cursor.getLong(5)))
            }
        }
        return result.asReversed()
    }

    fun deleteAll() {
        writableDatabase.delete("conversations", null, null)
    }

    companion object {
        /** Fallback local, sin inventar un asunto generado por una IA no consultada. */
        fun titleFor(raw: String): String {
            val clean = raw.replace(Regex("\\s+"), " ")
                .trim().trimStart('¿', '¡', ' ', '"')
                .substringBefore("\n")
            if (clean.isBlank()) return "Consulta sin título"
            val first = clean.take(72).trimEnd(' ', ',', '.', ';', ':', '?', '!', '¿')
            return first.replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale("es", "NI")) else it.toString() } +
                if (clean.length > 72) "…" else ""
        }
    }
}
