package ni.sky.mobileagent

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/**
 * Evidencia local de acciones; SENT sólo confirma que Android aceptó la solicitud.
 * No confundir apertura de pantalla con reproducción, envío, publicación o ejecución final.
 */
class SkyActionEvidence(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "sky_action_evidence.db", null, 1) {
    data class Receipt(val id: Long, val action: String, val status: String,
                       val detail: String, val createdAt: Long)

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE action_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            state TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        db.execSQL("CREATE INDEX idx_action_evidence_date ON action_evidence(created_at DESC)")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit

    @Synchronized fun record(action: String, state: String, detail: String): Long {
        val status = normalized(state)
        require(action.isNotBlank()) { "Falta identificar la acción." }
        val values = ContentValues().apply {
            put("action", action.take(120))
            put("state", status)
            put("detail", detail.take(500))
            put("created_at", System.currentTimeMillis())
        }
        return writableDatabase.insertOrThrow("action_evidence", null, values)
    }

    fun recent(limit: Int = 30): List<Receipt> {
        val result = mutableListOf<Receipt>()
        readableDatabase.query("action_evidence",
            arrayOf("id","action","state","detail","created_at"),
            null,null,null,null,"id DESC",limit.coerceIn(1,200).toString()).use { c ->
            while (c.moveToNext()) result.add(Receipt(c.getLong(0),c.getString(1),
                c.getString(2),c.getString(3),c.getLong(4)))
        }
        return result
    }

    fun deleteAll(): Int = writableDatabase.delete("action_evidence", null, null)

    companion object {
        fun normalized(raw: String): String = when (raw.uppercase()) {
            "SENT", "LAUNCHED", "REQUESTED" -> "ENVIADA_SIN_VERIFICAR"
            "VERIFIED_LOCAL" -> "VERIFICADA_LOCAL"
            "FAILED", "ERROR" -> "FALLIDA"
            "REJECTED", "CANCELLED" -> "RECHAZADA"
            else -> "ESTADO_DESCONOCIDO"
        }
    }
}
