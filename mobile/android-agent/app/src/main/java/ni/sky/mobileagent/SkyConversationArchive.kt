package ni.sky.mobileagent

import android.content.Context
import android.util.JsonWriter
import java.io.OutputStream
import java.io.OutputStreamWriter
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.Calendar

/**
 * Historial privado del teléfono: una entrada por consulta, con fecha/hora reales
 * del dispositivo y título deducido de la pregunta. No sincroniza ni sube datos.
 */
class SkyConversationArchive(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "sky_conversations.db", null, 2) {

    data class Entry(
        val id: Long,
        val title: String,
        val question: String,
        val answer: String,
        val engine: String,
        val createdAt: Long,
        val favorite: Boolean = false
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
            created_at INTEGER NOT NULL,
            is_favorite INTEGER NOT NULL DEFAULT 0
        )""")
        db.execSQL("CREATE INDEX idx_conversations_date ON conversations(created_at DESC)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // Migración aditiva: NO eliminar ni reemplazar el historial 0.8.20.
        if (oldVersion < 2) db.execSQL(
            "ALTER TABLE conversations ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0")
    }

    fun append(question: String, answer: String, engine: String): Entry {
        val now = System.currentTimeMillis()
        // No cortar respuestas de IA ni documentos a mitad de una frase.
        // La salida extensa permanece íntegra en SQLite y al exportar DOCX.
        require(answer.length <= 100_000) { "La respuesta supera 100.000 caracteres." }
        // Preserve full authorized private SKY API requests in SQLite.
        // Keep additive migrations: never erase past conversations.
        require(question.length <= SkyPromptLengthPolicy.OWN_API_MAX) {
            "La consulta supera el límite seguro de " +
                SkyPromptLengthPolicy.OWN_API_MAX + " caracteres."
        }
        val entry = Entry(0, titleFor(question), question,
            answer, engine.take(120), now)
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

    /** SQL parametrizado: búsqueda en título, pregunta y respuesta, sin perder registros antiguos. */
    fun page(query: String = "", beforeId: Long? = null,
             limit: Int = 25, filter: String = "Todos"): List<Entry> {
        val clauses = mutableListOf<String>()
        val args = mutableListOf<String>()
        if (beforeId != null) {
            require(beforeId > 0) { "Cursor de historial inválido." }
            clauses.add("id < ?")
            args.add(beforeId.toString())
        }
        if (query.isNotBlank()) {
            val safe = query.trim().take(100)
                .replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.add("(title LIKE ? ESCAPE '\\' OR question LIKE ? ESCAPE '\\' OR answer LIKE ? ESCAPE '\\')")
            repeat(3) { args.add("%$safe%") }
        }
        when (filter) {
            "Favoritos" -> clauses.add("is_favorite = 1")
            "Groq" -> { clauses.add("engine LIKE ?"); args.add("%Groq%") }
            "Gemini" -> { clauses.add("engine LIKE ?"); args.add("%Gemini%") }
            "Hoy", "Ayer" -> {
                val calendar = Calendar.getInstance().apply {
                    set(Calendar.HOUR_OF_DAY, 0)
                    set(Calendar.MINUTE, 0)
                    set(Calendar.SECOND, 0)
                    set(Calendar.MILLISECOND, 0)
                    if (filter == "Ayer") add(Calendar.DAY_OF_YEAR, -1)
                }
                val start = calendar.timeInMillis
                calendar.add(Calendar.DAY_OF_YEAR, 1)
                clauses.add("created_at >= ? AND created_at < ?")
                args.add(start.toString()); args.add(calendar.timeInMillis.toString())
            }
        }
        val found = ArrayList<Entry>()
        readableDatabase.query("conversations",
            arrayOf("id", "title", "question", "answer", "engine", "created_at", "is_favorite"),
            clauses.joinToString(" AND ").ifEmpty { null }, args.toTypedArray().takeIf { it.isNotEmpty() },
            null, null, "id DESC", limit.coerceIn(1, 101).toString()
        ).use { cursor ->
            while (cursor.moveToNext()) {
                found.add(Entry(cursor.getLong(0), cursor.getString(1),
                    cursor.getString(2), cursor.getString(3), cursor.getString(4),
                    cursor.getLong(5), cursor.getInt(6) == 1))
            }
        }
        return found
    }

    /** Editar solo título: la pregunta y respuesta originales se conservan. */
    fun rename(id: Long, rawTitle: String): Boolean {
        require(id > 0)
        val title = rawTitle.trim().replace(Regex("\\s+"), " ").take(100)
        require(title.length in 2..100)
        val values = android.content.ContentValues().apply { put("title", title) }
        return writableDatabase.update("conversations", values,
            "id = ?", arrayOf(id.toString())) == 1
    }

    fun setFavorite(id: Long, isFavorite: Boolean): Boolean {
        require(id > 0)
        val values = android.content.ContentValues().apply {
            put("is_favorite", if (isFavorite) 1 else 0)
        }
        return writableDatabase.update("conversations", values,
            "id = ?", arrayOf(id.toString())) == 1
    }

    fun delete(id: Long): Boolean {
        require(id > 0)
        return writableDatabase.delete("conversations", "id = ?",
            arrayOf(id.toString())) == 1
    }

    /** Exportación voluntaria sin volcar todo el historial a RAM ni enviarlo a la nube. */
    fun writeJson(output: OutputStream): Int {
        var count = 0
        JsonWriter(OutputStreamWriter(output, Charsets.UTF_8)).use { json ->
            json.setIndent("  ")
            json.beginObject()
            json.name("sky_history_export_version").value(1)
            json.name("records").beginArray()
            readableDatabase.query("conversations",
                arrayOf("id", "title", "question", "answer", "engine", "created_at"),
                null, null, null, null, "id ASC"
            ).use { cursor ->
                while (cursor.moveToNext()) {
                    json.beginObject()
                    json.name("id").value(cursor.getLong(0))
                    json.name("title").value(cursor.getString(1))
                    json.name("question").value(cursor.getString(2))
                    json.name("answer").value(cursor.getString(3))
                    json.name("engine").value(cursor.getString(4))
                    json.name("timestamp_ms").value(cursor.getLong(5))
                    json.endObject()
                    count++
                }
            }
            json.endArray().endObject()
        }
        return count
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
