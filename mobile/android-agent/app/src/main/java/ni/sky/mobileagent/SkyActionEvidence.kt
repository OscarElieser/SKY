package ni.sky.mobileagent

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.util.UUID

/**
 * Evidencia local de acciones; SENT sólo confirma que Android aceptó la solicitud.
 * No confundir apertura de pantalla con reproducción, envío, publicación o ejecución final.
 */
class SkyActionEvidence(context: Context) :
    SQLiteOpenHelper(context.applicationContext, "sky_action_evidence.db", null, 3) {
    data class Receipt(val id: Long, val action: String, val status: String,
                       val detail: String, val createdAt: Long, val eventId: String,
                       val operationId: String)

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE action_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            state TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            event_id TEXT,
            operation_id TEXT
        )""")
        db.execSQL("CREATE INDEX idx_action_evidence_date ON action_evidence(created_at DESC)")
        db.execSQL("CREATE UNIQUE INDEX idx_action_evidence_event ON action_evidence(event_id)")
        db.execSQL("CREATE INDEX idx_action_evidence_operation ON action_evidence(operation_id)")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            db.execSQL("ALTER TABLE action_evidence ADD COLUMN event_id TEXT")
            db.execSQL("CREATE UNIQUE INDEX idx_action_evidence_event ON action_evidence(event_id)")
        }
        if (oldVersion < 3) {
            db.execSQL("ALTER TABLE action_evidence ADD COLUMN operation_id TEXT")
            db.execSQL("CREATE INDEX idx_action_evidence_operation ON action_evidence(operation_id)")
        }
    }

    /** Share an operation ID across authorization, launch and observed outcome. */
    fun newOperationId(): String = UUID.randomUUID().toString()

    @Synchronized fun record(action: String, state: String, detail: String,
                             operationId: String? = null): Long {
        val status = normalized(state)
        require(operationId == null || runCatching { UUID.fromString(operationId) }.isSuccess) {
            "Identificador de operación inválido."
        }
        require(action.isNotBlank()) { "Falta identificar la acción." }
        val values = ContentValues().apply {
            put("action", action.take(120))
            put("state", status)
            put("detail", detail.take(500))
            put("created_at", System.currentTimeMillis())
            put("event_id", UUID.randomUUID().toString())
            put("operation_id", operationId ?: UUID.randomUUID().toString())
        }
        return writableDatabase.insertOrThrow("action_evidence", null, values)
    }

    data class Summary(
        val total: Int,
        val verified: Int,
        val sentUnverified: Int,
        val failed: Int,
        val rejected: Int,
        val remoteResponse: Int,
        val unknown: Int,
        val authorized: Int
    )

    /** Agrega estados reales de SQLite, sin leer contenido de notas ni mensajes. */
    @Synchronized fun summary(): Summary {
        val counts = mutableMapOf<String, Int>()
        readableDatabase.rawQuery(
            "SELECT state, COUNT(*) FROM action_evidence GROUP BY state", null
        ).use { cursor ->
            while (cursor.moveToNext()) {
                counts[cursor.getString(0)] = cursor.getInt(1)
            }
        }
        return Summary(
            total = counts.values.sum(),
            verified = counts["VERIFICADA_LOCAL"] ?: 0,
            sentUnverified = counts["ENVIADA_SIN_VERIFICAR"] ?: 0,
            failed = counts["FALLIDA"] ?: 0,
            rejected = counts["RECHAZADA"] ?: 0,
            remoteResponse = counts["RESPUESTA_REMOTA_RECIBIDA"] ?: 0,
            unknown = counts["ESTADO_DESCONOCIDO"] ?: 0,
            authorized = counts["AUTORIZADA"] ?: 0
        )
    }

    fun recent(limit: Int = 30): List<Receipt> {
        val result = mutableListOf<Receipt>()
        readableDatabase.query("action_evidence",
            arrayOf("id","action","state","detail","created_at","event_id","operation_id"),
            null,null,null,null,"id DESC",limit.coerceIn(1,200).toString()).use { c ->
            while (c.moveToNext()) result.add(Receipt(c.getLong(0),c.getString(1),
                c.getString(2),c.getString(3),c.getLong(4),
                c.getString(5) ?: "legacy-" + c.getLong(0),
                c.getString(6) ?: "legacy-" + c.getLong(0)))
        }
        return result
    }

    fun deleteAll(): Int = writableDatabase.delete("action_evidence", null, null)

    companion object {
        fun normalized(raw: String): String = when (raw.uppercase()) {
            "AUTHORIZED", "AUTORIZADA" -> "AUTORIZADA"
            "SENT", "LAUNCHED", "REQUESTED" -> "ENVIADA_SIN_VERIFICAR"
            "VERIFIED_LOCAL" -> "VERIFICADA_LOCAL"
            "RECEIVED_RESPONSE" -> "RESPUESTA_REMOTA_RECIBIDA"
            "FAILED", "ERROR" -> "FALLIDA"
            "REJECTED", "CANCELLED" -> "RECHAZADA"
            else -> "ESTADO_DESCONOCIDO"
        }
    }
}
