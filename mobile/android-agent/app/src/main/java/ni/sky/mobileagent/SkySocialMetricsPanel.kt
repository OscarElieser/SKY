package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject

/** Local dashboard for metrics the user explicitly imports from their own accounts. */
class SkySocialMetricsPanel(
    private val host: Activity,
    private val prefs: SharedPreferences,
    private val onImportClick: () -> Unit,
    private val feedback: (String) -> Unit
) {
    private val storage = "metrics_rows_v1"

    fun records(): List<SkySocialMetrics.Record> = runCatching {
        val entries = JSONArray(prefs.getString(storage, "[]"))
        (0 until entries.length()).mapNotNull { i ->
            val j = entries.optJSONObject(i) ?: return@mapNotNull null
            SkySocialMetrics.Record(
                j.optString("platform"), j.optString("post"),
                j.optLong("views"), j.optLong("likes"),
                j.optLong("comments"), j.optLong("shares"),
                j.optLong("followers"), j.optString("date")
            )
        }
    }.getOrDefault(emptyList())

    fun show() {
        val all = records()
        val top = all.sortedByDescending { it.views }.take(6)
        val summary = SkySocialMetrics.analysis(all) + if (top.isEmpty()) "" else
            "\n\nMás vistas:\n" + top.joinToString("\n") { row ->
                row.platform + " · " + row.post.take(36) + " · " + row.views + " vistas"
            }
        AlertDialog.Builder(host)
            .setTitle("SKY · Estadísticas de mis redes")
            .setMessage(summary + "\n\nImportá un archivo CSV con columnas " +
                "Plataforma,Publicacion,Vistas,Likes,Comentarios,Compartidos,Seguidores,Fecha. " +
                "Copiá solo métricas propias obtenidas de las estadísticas de cada red; " +
                "los formatos originales varían y pueden necesitar adaptación. " +
                "Los datos permanecen en este teléfono, sin enviarse a Gemini.")
            .setPositiveButton("Importar CSV") { _, _ -> onImportClick() }
            .setNeutralButton("Borrar datos") { _, _ ->
                AlertDialog.Builder(host)
                    .setTitle("Borrar métricas locales")
                    .setMessage("¿Borrar todos los registros importados en SKY? " +
                        "No modifica los datos de tus redes sociales.")
                    .setPositiveButton("Borrar") { _, _ ->
                        prefs.edit().remove(storage).apply()
                        feedback("Métricas locales borradas.")
                    }
                    .setNegativeButton("Cancelar", null).show()
            }
            .setNegativeButton("Cerrar", null).show()
    }

    fun importCsv(uri: Uri) {
        try {
            val contents = host.contentResolver.openInputStream(uri)?.bufferedReader(
                Charsets.UTF_8)?.use { reader -> reader.readText() }
                ?: throw IllegalArgumentException("Android no pudo abrir el archivo.")
            val parsed = SkySocialMetrics.parseCsv(contents)
            val array = JSONArray()
            parsed.forEach { row ->
                array.put(JSONObject()
                    .put("platform", row.platform).put("post", row.post)
                    .put("views", row.views).put("likes", row.likes)
                    .put("comments", row.comments).put("shares", row.shares)
                    .put("followers", row.followers).put("date", row.date))
            }
            prefs.edit().putString(storage, array.toString()).apply()
            feedback("Importé " + parsed.size + " registros locales. " +
                "No accedí a tus cuentas ni envié los datos a otro servidor.")
            show()
        } catch (error: Exception) {
            AlertDialog.Builder(host)
                .setTitle("No se pudo importar el CSV")
                .setMessage(error.message ?: "Revisá las columnas y cifras del archivo.")
                .setPositiveButton("Entendido", null).show()
        }
    }

    fun chooseCsv() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "text/*"
            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf(
                "text/csv", "text/plain", "application/vnd.ms-excel", "application/csv"))
        }
        try {
            host.startActivityForResult(intent, 1640)
        } catch (_: Exception) {
            feedback("No se encontró selector de documentos para CSV.")
        }
    }
}
