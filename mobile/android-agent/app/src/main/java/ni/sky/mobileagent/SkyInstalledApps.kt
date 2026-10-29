package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.text.Editable
import android.text.TextWatcher
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * Launcher universal limitado a actividades visibles y lanzables:
 * descubre aplicaciones actuales y futuras al consultar Android, sin
 * QUERY_ALL_PACKAGES y sin transmitir el inventario a servidores.
 */
class SkyInstalledApps(
    private val activity: Activity,
    private val say: (String) -> Unit
) {
    var onReceipt: ((String, String, String) -> Unit)? = null
    private fun receipt(action: String, status: String, detail: String) {
        onReceipt?.invoke(action, status, detail)
    }
    private val trusted = activity.getSharedPreferences(
        "sky_trusted_launcher_apps", android.content.Context.MODE_PRIVATE
    )

    data class Launchable(
        val name: String,
        val packageName: String,
        val className: String
    ) {
        fun asEntry() = SkyAppNameMatcher.Entry(name, packageName)
    }

    fun discover(): List<Launchable> {
        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val entries = activity.packageManager.queryIntentActivities(intent, 0)
            .mapNotNull { item ->
                val info = item.activityInfo ?: return@mapNotNull null
                if (info.packageName == activity.packageName || !info.enabled ||
                    !info.applicationInfo.enabled || !info.exported) return@mapNotNull null
                val name = item.loadLabel(activity.packageManager)?.toString()?.trim()
                    .orEmpty().ifEmpty { info.packageName.substringAfterLast('.') }
                Launchable(name, info.packageName, info.name)
            }
            .distinctBy { it.packageName to it.className }
        return entries.sortedWith(
            compareBy<Launchable> { SkyAppNameMatcher.norm(it.name) }.thenBy { it.packageName }
        )
    }

    fun requestLaunch(query: String) {
        val choices = discover()
        val matched = SkyAppNameMatcher.matches(query, choices.map { it.asEntry() })
        val available = matched.mapNotNull { entry ->
            choices.firstOrNull { it.packageName == entry.packageName && it.name == entry.label }
        }
        when (available.size) {
            0 -> say("No encontré «" + query.take(65) +
                "» entre las aplicaciones visibles. Podés revisar el catálogo en Ajustes.")
            1 -> {
                val app = available.first()
                if (trusted.getBoolean(app.packageName, false)) launchDirect(app)
                else confirm(app)
            }
            else -> {
                AlertDialog.Builder(activity)
                    .setTitle("SKY · ¿Cuál aplicación?")
                    .setItems(available.map { it.name }.toTypedArray()) { _, position ->
                        confirm(available[position])
                    }
                    .setNegativeButton("Cancelar", null)
                    .show()
            }
        }
    }

    /**
     * Enviar texto al menú de preparación de una app compatible. El usuario
     * decide posteriormente si publicarlo o enviarlo; SKY nunca pulsa Enviar.
     */
    fun requestShare(query: String, text: String) {
        val available = discover()
        val matched = SkyAppNameMatcher.matches(query, available.map { it.asEntry() })
            .mapNotNull { entry ->
                available.firstOrNull { it.packageName == entry.packageName && it.name == entry.label }
            }
        if (matched.isEmpty()) {
            say("No encontré esa aplicación instalada para compartir texto.")
            return
        }
        fun prepare(app: Launchable) {
            AlertDialog.Builder(activity)
                .setTitle("SKY · Compartir con " + app.name)
                .setMessage("¿Preparar este texto en " + app.name + "?\n\n" +
                    text.take(220) + "\n\nConfirmar la publicación es decisión tuya.")
                .setPositiveButton("Preparar") { _, _ ->
                    val shareIntent = Intent(Intent.ACTION_SEND).apply {
                        type = "text/plain"
                        setPackage(app.packageName)
                        putExtra(Intent.EXTRA_TEXT, text.take(1000))
                    }
                    try {
                        activity.startActivity(shareIntent)
                        say("Preparé el texto para " + app.name +
                            ". Revisá el resultado antes de publicarlo.")
                    } catch (_: Exception) {
                        say(app.name + " no admite este modo de compartir texto.")
                    }
                }
                .setNegativeButton("Cancelar", null)
                .show()
        }
        if (matched.size == 1) prepare(matched.first())
        else AlertDialog.Builder(activity)
            .setTitle("SKY · Elegí la aplicación")
            .setItems(matched.map { it.name }.toTypedArray()) { _, which ->
                prepare(matched[which])
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    fun showCatalog() {
        val all = discover()
        if (all.isEmpty()) {
            say("Android no encontró aplicaciones con icono de inicio disponibles.")
            return
        }
        val holder = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(28, 16, 28, 8)
        }
        val search = EditText(activity).apply {
            hint = "Buscar entre mis aplicaciones"
            setSingleLine(true)
            contentDescription = "Filtrar aplicaciones instaladas"
        }
        holder.addView(search)
        val list = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
        val scroll = ScrollView(activity).apply { addView(list) }
        holder.addView(scroll, LinearLayout.LayoutParams(-1,
            (activity.resources.displayMetrics.heightPixels * 0.52f).toInt()))
        val dialog = AlertDialog.Builder(activity)
            .setTitle("SKY · Aplicaciones (" + all.size + ")")
            .setView(holder)
            .setPositiveButton("Cerrar", null)
            .create()
        fun render(filter: String) {
            list.removeAllViews()
            val results = all.filter {
                SkyAppNameMatcher.norm(it.name)
                    .contains(SkyAppNameMatcher.norm(filter))
            }.take(100)
            for (app in results) {
                val row = TextView(activity).apply {
                    text = (if (trusted.getBoolean(app.packageName, false)) "★ " else "") +
                        app.name
                    textSize = 16f
                    setTextColor(Color.rgb(40, 45, 90))
                    setPadding(20, 18, 20, 18)
                    setOnClickListener {
                        dialog.dismiss()
                        confirm(app)
                    }
                }
                list.addView(row)
            }
        }
        search.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                render(s?.toString().orEmpty())
            }
            override fun afterTextChanged(s: Editable?) {}
        })
        render("")
        dialog.show()
    }

    private fun confirm(app: Launchable) {
        val isTrusted = trusted.getBoolean(app.packageName, false)
        AlertDialog.Builder(activity)
            .setTitle("SKY · " + app.name)
            .setMessage("¿Abrir esta aplicación?\n\n" +
                "Podés confiar en ella para que SKY la abra directamente " +
                "cuando VOS lo ordenés por voz o chat. " +
                "Confiar no autoriza leer contenido, escribir ni publicar.")
            .setPositiveButton("Abrir esta vez") { _, _ -> launchDirect(app) }
            .setNeutralButton(if (isTrusted) "Quitar confianza" else "Confiar y abrir") { _, _ ->
                if (isTrusted) {
                    trusted.edit().remove(app.packageName).apply()
                    say("SKY pedirá confirmación nuevamente para " + app.name + ".")
                } else {
                    trusted.edit().putBoolean(app.packageName, true).apply()
                    launchDirect(app)
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun launchDirect(app: Launchable) {
        try {
            // Revalidación necesaria: el catálogo es dinámico.
            val current = discover().firstOrNull {
                it.packageName == app.packageName && it.className == app.className
            }
            if (current == null) {
                trusted.edit().remove(app.packageName).apply()
                say("Esta aplicación ya no aparece instalada o visible.")
                receipt("Abrir " + app.name, "FAILED", "App no encontrada al verificar Android")
                return
            }
            val launchIntent = Intent(Intent.ACTION_MAIN)
                .addCategory(Intent.CATEGORY_LAUNCHER)
                .setComponent(ComponentName(current.packageName, current.className))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            activity.startActivity(launchIntent)
            receipt("Abrir " + current.name, "SENT",
                "Android aceptó startActivity; apertura completa no comprobada")
            say("Android recibió la orden para abrir " + current.name +
                ". No puedo confirmar que terminó de cargar.")
        } catch (_: Exception) {
            receipt("Abrir " + app.name, "FAILED", "Android rechazó la apertura")
            say("Android no permitió abrir " + app.name + ".")
        }
    }
}
