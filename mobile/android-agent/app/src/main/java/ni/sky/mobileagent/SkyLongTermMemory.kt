package ni.sky.mobileagent

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.text.Normalizer
import java.util.Locale

/**
 * Memoria explícita y persistente SOLO Android. No entrena pesos ni sube datos.
 * La base permanece dentro del sandbox de la app (sin cifrado adicional).
 * Se usan consultas parametrizadas; jamás ejecuta SQL procedente del usuario.
 */
class SkyLongTermMemory(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "sky_long_term_memory.db", null, 1) {

    data class Fact(val id: Long, val text: String, val createdAt: Long, val source: String)
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE owner_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL UNIQUE,
            created_at INTEGER NOT NULL,
            source TEXT NOT NULL
        )""")
        db.execSQL("CREATE INDEX idx_owner_facts_time ON owner_facts(created_at DESC)")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit

    /** Solo hechos introducidos por una orden explícita del propietario. */
    @Synchronized fun remember(raw: String): Fact {
        val text = SkyOwnerContext.parseWindows(raw.trim()).trim()
        require(text.length in 5..1800) { "El recuerdo debe tener entre 5 y 1800 caracteres." }
        val db = writableDatabase
        db.execSQL("INSERT OR IGNORE INTO owner_facts(content,created_at,source) VALUES(?,?,?)",
            arrayOf(text, System.currentTimeMillis(), "owner_explicit"))
        db.rawQuery("SELECT id, content, created_at, source FROM owner_facts WHERE content = ?",
            arrayOf(text)).use { cursor ->
            check(cursor.moveToFirst()) { "No se guardó el recuerdo." }
            return Fact(cursor.getLong(0), cursor.getString(1), cursor.getLong(2),
                cursor.getString(3))
        }
    }

    fun recent(limit: Int = 100): List<Fact> {
        val result = ArrayList<Fact>()
        readableDatabase.query("owner_facts",
            arrayOf("id","content","created_at","source"), null, null, null, null,
            "id DESC", limit.coerceIn(1, 2000).toString()).use { cursor ->
            while (cursor.moveToNext())
                result.add(Fact(cursor.getLong(0), cursor.getString(1), cursor.getLong(2),
                    cursor.getString(3)))
        }
        return result
    }

    /** Recuperación local explicable: coincidencia de términos; sin inferir identidades. */
    fun relevant(question: String, limit: Int = 5): List<Fact> {
        val candidates = recent(1500)
        return rank(question, candidates, limit)
    }

    fun delete(id: Long): Boolean {
        require(id > 0) { "Recuerdo inválido." }
        return writableDatabase.delete("owner_facts", "id = ?", arrayOf(id.toString())) > 0
    }

    fun deleteAll(): Int = writableDatabase.delete("owner_facts", null, null)

    companion object {
        private val stopwords = setOf(
            "que","como","para","este","esta","esto","donde","cuando","porque",
            "quiero","puedes","podrias","sobre","con","los","las","del","una",
            "uno","mis","tus","soy","eres","recuerdas","recuerda","sky")
        fun terms(text: String): Set<String> {
            val value = Normalizer.normalize(text.lowercase(Locale.ROOT), Normalizer.Form.NFD)
                .replace(Regex("""\p{M}+"""), "")
            return Regex("[a-z0-9]{3,}").findAll(value).map { it.value }
                .filterNot { it in stopwords }.take(150).toSet()
        }
        fun rank(question: String, candidates: List<Fact>, limit: Int = 5): List<Fact> {
            val tokens = terms(question)
            if (tokens.isEmpty()) return emptyList()
            return candidates.mapNotNull { fact ->
                val overlap = tokens.intersect(terms(fact.text)).size
                if (overlap == 0) null else fact to overlap
            }.sortedWith(compareByDescending<Pair<Fact,Int>> { it.second }
                .thenByDescending { it.first.createdAt })
                .take(limit.coerceIn(1, 10)).map { it.first }
        }
    }
}
