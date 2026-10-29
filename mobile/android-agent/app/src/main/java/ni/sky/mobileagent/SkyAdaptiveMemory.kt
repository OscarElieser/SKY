package ni.sky.mobileagent

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.text.Normalizer
import java.util.Locale

/**
 * Correcciones explícitas del propietario. Aprendizaje funcional por recuperación
 * local, NO reentrenamiento de pesos. No transmite ejemplos al proveedor.
 */
class SkyAdaptiveMemory(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "sky_approved_answers.db", null, 1) {

    data class Example(val id: Long, val question: String, val answer: String,
                       val updatedAt: Long, val used: Int)

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE approved_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT NOT NULL UNIQUE,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        )""")
        db.execSQL("CREATE INDEX idx_approved_answers_time ON approved_answers(updated_at DESC)")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit

    @Synchronized fun teach(question: String, answer: String): Example {
        val why = ineligibleReason(question)
        require(why == null) { why ?: "Consulta no elegible." }
        val value = answer.trim()
        require(value.length in 5..8000) { "La corrección debe tener entre 5 y 8000 caracteres." }
        require(!containsSecret(question) && !containsSecret(value)) {
            "No guardés contraseñas, claves API, tokens ni datos bancarios."
        }
        val key = fingerprint(question)
        val now = System.currentTimeMillis()
        val values = ContentValues().apply {
            put("fingerprint", key)
            put("question", question.trim().take(4000))
            put("answer", value)
            put("updated_at", now)
            put("used", 0)
        }
        writableDatabase.insertWithOnConflict("approved_answers", null, values,
            SQLiteDatabase.CONFLICT_REPLACE).let {
            check(it != -1L) { "La corrección no se guardó." }
        }
        return find(question) ?: error("No se pudo comprobar la corrección guardada.")
    }

    @Synchronized fun recall(question: String): Example? {
        if (ineligibleReason(question) != null) return null
        val value = find(question) ?: return null
        val values = ContentValues().apply { put("used", value.used + 1) }
        writableDatabase.update("approved_answers", values, "id = ?",
            arrayOf(value.id.toString()))
        return value.copy(used = value.used + 1)
    }

    fun find(question: String): Example? {
        val key = fingerprint(question)
        if (key.isBlank()) return null
        readableDatabase.rawQuery(
            "SELECT id,question,answer,updated_at,used FROM approved_answers WHERE fingerprint = ?",
            arrayOf(key)).use { c ->
            if (!c.moveToFirst()) return null
            return Example(c.getLong(0), c.getString(1), c.getString(2),
                c.getLong(3), c.getInt(4))
        }
    }

    fun recent(limit: Int = 40): List<Example> {
        val entries = mutableListOf<Example>()
        readableDatabase.query("approved_answers",
            arrayOf("id","question","answer","updated_at","used"),
            null, null, null, null, "updated_at DESC", limit.coerceIn(1,200).toString()
        ).use { c ->
            while(c.moveToNext()) entries.add(Example(c.getLong(0),c.getString(1),
                c.getString(2),c.getLong(3),c.getInt(4)))
        }
        return entries
    }

    fun delete(id: Long): Boolean = id > 0 &&
        writableDatabase.delete("approved_answers", "id = ?", arrayOf(id.toString())) == 1
    fun deleteAll(): Int = writableDatabase.delete("approved_answers", null, null)

    companion object {
        fun fingerprint(raw: String): String {
            val ascii = Normalizer.normalize(raw.lowercase(Locale.ROOT), Normalizer.Form.NFD)
                .replace(Regex("""\p{M}+"""), "")
            return ascii.replace(Regex("""[^a-z0-9]+"""), " ").trim()
                .replace(Regex("""\s+"""), " ").take(4000)
        }

        private val secret = Regex(
            """(?i)\b(?:api[_ -]?key|password|contrase(?:n|ñ)a|bearer|private[_ -]?key|cvv|clave secreta|token|pin)\s*[:=]"""
        )
        private fun containsSecret(text: String): Boolean = secret.containsMatchIn(text)

        /** Dynamic information and commands are never replayed as "learned facts". */
        fun ineligibleReason(question: String): String? {
            if (question.trim().length !in 4..4000)
                return "La consulta original está vacía o supera 4000 caracteres."
            if (SkyPhoneCloud.requiresLiveVerification(question) ||
                SkyAndroidCognition.classify(question).verifyWithSources)
                return "Los datos actuales necesitan fuentes nuevas, no una respuesta antigua."
            if (SkyAndroidCognition.classify(question).actionProposedOnly ||
                SkyAndroidCognition.explicitFact(question) != null)
                return "Las órdenes sobre aplicaciones o memoria no se pueden almacenar como respuestas ejecutadas."
            if (containsSecret(question))
                return "No se admiten consultas que contienen credenciales."
            return null
        }
    }
}
