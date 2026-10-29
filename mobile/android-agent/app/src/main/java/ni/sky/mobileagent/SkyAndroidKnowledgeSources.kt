package ni.sky.mobileagent

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.net.URI
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Biblioteca incremental SOLO de referencias de búsqueda confirmadas por el proveedor.
 * No guarda consultas personales, cuerpos de conversaciones, archivos o tokens.
 * Las URL externas son datos NO confiables; guardar un enlace no verifica su contenido.
 */
class SkyAndroidKnowledgeSources(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "sky_android_sources.db", null, 1) {

    data class SourceEntry(
        val title: String,
        val url: String,
        val savedAt: Long,
        val origin: String
    ) {
        fun localDate(): String =
            SimpleDateFormat("dd/MM/yyyy HH:mm", Locale("es", "NI")).format(Date(savedAt))
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE sources(
            url TEXT PRIMARY KEY NOT NULL,
            title TEXT NOT NULL,
            origin TEXT NOT NULL,
            saved_at INTEGER NOT NULL
        )""")
        db.execSQL("CREATE INDEX idx_sky_source_saved ON sources(saved_at DESC)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit

    fun saveGrounded(sources: List<SkyPhoneCloud.Source>, searchedWeb: Boolean): Int {
        if (!searchedWeb || sources.isEmpty()) return 0
        var written = 0
        writableDatabase.beginTransaction()
        try {
            val db = writableDatabase
            for (source in sources.take(5)) {
                if (!publicSourceUrl(source.url)) continue
                val cleanTitle = source.title.trim().replace(Regex("""\s+"""), " ").take(130)
                if (cleanTitle.isEmpty()) continue
                val row = ContentValues().apply {
                    put("url", source.url)
                    put("title", cleanTitle)
                    put("origin", "Gemini · referencias de Google Search")
                    put("saved_at", System.currentTimeMillis())
                }
                db.insertWithOnConflict("sources", null, row, SQLiteDatabase.CONFLICT_REPLACE)
                written++
            }
            // Retener solo 500 referencias sin perder las más recientes.
            db.execSQL("""DELETE FROM sources WHERE url NOT IN
                (SELECT url FROM sources ORDER BY saved_at DESC LIMIT 500)""")
            db.setTransactionSuccessful()
        } finally {
            writableDatabase.endTransaction()
        }
        return written
    }

    fun recent(limit: Int = 20): List<SourceEntry> {
        val data = ArrayList<SourceEntry>()
        readableDatabase.query(
            "sources", arrayOf("title", "url", "saved_at", "origin"),
            null, null, null, null, "saved_at DESC", limit.coerceIn(1, 50).toString()
        ).use { cursor ->
            while (cursor.moveToNext()) {
                data.add(SourceEntry(cursor.getString(0), cursor.getString(1),
                    cursor.getLong(2), cursor.getString(3)))
            }
        }
        return data
    }

    fun clearAll(): Int = writableDatabase.delete("sources", null, null)

    companion object {
        /** No se contacta la URL: solo validación sintáctica para almacenarla. */
        fun publicSourceUrl(raw: String): Boolean {
            if (raw.length !in 15..1500 || raw.any { it.isWhitespace() || Character.isISOControl(it) }) {
                return false
            }
            return try {
                val parsed = URI(raw)
                val host = parsed.host?.lowercase(Locale.ROOT).orEmpty()
                parsed.scheme.equals("https", ignoreCase = true) &&
                    parsed.userInfo == null && parsed.port == -1 &&
                    host.contains('.') &&
                    host != "localhost" && !host.endsWith(".local") &&
                    !host.endsWith(".internal") &&
                    !host.endsWith(".localhost") &&
                    !host.startsWith("127.") && !host.startsWith("10.") &&
                    !host.startsWith("192.168.") && !host.startsWith("172.") &&
                    host != "0.0.0.0" &&
                    !host.endsWith(".example") &&
                    parsed.rawFragment == null
            } catch (_: IllegalArgumentException) {
                false
            }
        }
    }
}
