package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.view.Gravity
import android.widget.Button
import android.widget.ImageView
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
    private val control = SkySupervisedControl(activity)
    private val launchLimiter = SkyLocalActionLimiter()

    /** Solo autoriza órdenes locales explícitas; no incluye tareas remotas. */
    fun supervisedControlEnabled(): Boolean = control.isAuthorized()

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
            .distinctBy { it.packageName to SkyAppNameMatcher.norm(it.name) }
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
            0 -> {
                receipt("Abrir aplicación", "FAILED", "No se encontró aplicación visible coincidente")
                say("No encontré «" + query.take(65) +
                    "» entre las aplicaciones visibles. Podés revisar el catálogo en Ajustes.")
            }
            1 -> {
                val app = available.first()
                if (supervisedControlEnabled() || trusted.getBoolean(app.packageName, false)) launchDirect(app)
                else confirm(app)
            }
            else -> {
                AlertDialog.Builder(activity)
                    .setTitle("SKY · ¿Cuál aplicación?")
                    .setItems(available.map { it.name }.toTypedArray()) { _, position ->
                        val selected = available[position]
                        // Con autorización global solo se pregunta cuál app quiere abrir:
                        // no volver a solicitar confianza individual.
                        if (supervisedControlEnabled() ||
                            trusted.getBoolean(selected.packageName, false)) launchDirect(selected)
                        else confirm(selected)
                    }
                    .setNegativeButton("Cancelar") { _, _ ->
                        receipt("Abrir aplicación", "REJECTED", "Selección de aplicación cancelada")
                    }
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


    /**
     * Un único consentimiento local para abrir apps sin 82 confirmaciones.
     * No suplanta los permisos del sistema ni autoriza operaciones destructivas.
     */
    fun showControlAuthorization(onChanged: (() -> Unit)? = null) {
        if (supervisedControlEnabled()) {
            AlertDialog.Builder(activity)
                .setTitle("SKY IA · Control supervisado")
                .setMessage(
                    "La apertura directa de aplicaciones está autorizada para " +
                    "órdenes que vos dictés o escribás en SKY.\n\n" +
                    "¿Querés revocar esta confianza general? Las aplicaciones " +
                    "seguirán instaladas y tus datos no se modificarán."
                )
                .setPositiveButton("REVOCAR AUTORIZACIÓN") { _, _ ->
                    if (control.setAuthorized(false)) {
                        receipt("Control supervisado", "VERIFIED_LOCAL",
                            "Revocación de confianza local guardada en Android")
                        say("Revocaste la apertura general de aplicaciones en SKY.")
                        onChanged?.invoke()
                    } else say("No pude guardar la revocación en el teléfono.")
                }
                .setNegativeButton("Conservar", null)
                .show()
            return
        }
        AlertDialog.Builder(activity)
            .setTitle("SKY IA · Tu autorización")
            .setMessage(
                "Autorizo a SKY a abrir las aplicaciones actuales y futuras " +
                "de mi teléfono cuando YO lo indique por voz o texto, sin " +
                "confirmaciones individuales de apertura.\n\n" +
                "SKY actuará únicamente bajo mis órdenes. Podré revocar " +
                "este consentimiento desde Configuración.\n\n" +
                "Esto NO concede acceso automático a contraseñas, mensajes, " +
                "archivos ni al contenido de otras aplicaciones. Para escribir, " +
                "modificar o eliminar, SKY necesita una función compatible y, " +
                "cuando corresponda, los permisos de Android y confirmación " +
                "de la operación. Las órdenes remotas nunca heredan este permiso."
            )
            .setPositiveButton("ACEPTO · CONTROL SUPERVISADO") { _, _ ->
                if (control.setAuthorized(true)) {
                    receipt("Control supervisado", "VERIFIED_LOCAL",
                        "Consentimiento local guardado; no incluye control remoto ni permisos Android")
                    say("Control supervisado autorizado. Ya podés decirme qué aplicación abrir.")
                    onChanged?.invoke()
                } else say("No pude guardar tu autorización; no se activó.")
            }
            .setNegativeButton("Ahora no", null)
            .show()
    }

    /** Catálogo oscuro premium con búsqueda y un único control de confianza. */
    fun showCatalog() {
        val all = discover()
        if (all.isEmpty()) {
            say("Android no encontró aplicaciones con icono de inicio disponibles.")
            return
        }
        val dp: (Int) -> Int = { SkyPremiumUi.dp(activity, it) }
        val root = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(20), dp(20), dp(14))
            background = SkyPremiumUi.shape(activity, SkyPremiumUi.background, 23)
        }
        val header = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val heading = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
        }
        heading.addView(SkyPremiumUi.label(activity, "✦  MIS APLICACIONES",
            20f, SkyPremiumUi.white, true))
        heading.addView(SkyPremiumUi.label(activity,
            "SKY detectó " + all.size + " aplicaciones disponibles",
            12f, SkyPremiumUi.muted))
        header.addView(heading, LinearLayout.LayoutParams(0, -2, 1f))
        val exit = SkyPremiumUi.label(activity, "✕", 22f, SkyPremiumUi.white).apply {
            gravity = Gravity.CENTER
            background = SkyPremiumUi.shape(activity, SkyPremiumUi.elevated, 16)
            contentDescription = "Cerrar aplicaciones"
        }
        header.addView(exit, LinearLayout.LayoutParams(dp(46), dp(46)))
        root.addView(header)

        val state = SkyPremiumUi.label(activity, "", 13f, SkyPremiumUi.muted).apply {
            setPadding(0, dp(14), 0, dp(8))
        }
        root.addView(state)
        val authorization = Button(activity).apply {
            isAllCaps = false
            textSize = 13f
            minHeight = dp(54)
            setTextColor(SkyPremiumUi.background)
            typeface = Typeface.DEFAULT_BOLD
        }
        root.addView(authorization, LinearLayout.LayoutParams(-1, dp(56)))
        root.addView(SkyPremiumUi.label(activity,
            "Para escribir, modificar o eliminar en otras apps se requieren " +
            "funciones compatibles, permisos adicionales y supervisión.",
            11.5f, SkyPremiumUi.muted).apply {
            setPadding(0, dp(10), 0, dp(11))
        })
        val search = EditText(activity).apply {
            hint = "Buscar entre mis aplicaciones"
            setSingleLine(true)
            contentDescription = "Filtrar aplicaciones instaladas"
            textSize = 14f
            setTextColor(SkyPremiumUi.white)
            setHintTextColor(SkyPremiumUi.muted)
            setPadding(dp(15), dp(10), dp(15), dp(10))
            background = SkyPremiumUi.shape(activity, SkyPremiumUi.card, 15)
        }
        root.addView(search, LinearLayout.LayoutParams(-1, dp(52)))
        val list = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(12), 0, 0)
        }
        val scroll = ScrollView(activity).apply {
            isVerticalScrollBarEnabled = false
            addView(list)
        }
        root.addView(scroll, LinearLayout.LayoutParams(-1,
            (activity.resources.displayMetrics.heightPixels * 0.46f).toInt()))
        val dialog = AlertDialog.Builder(activity).setView(root).create()
        exit.setOnClickListener { dialog.dismiss() }
        fun render(filter: String) {
            list.removeAllViews()
            val results = all.filter {
                SkyAppNameMatcher.norm(it.name)
                    .contains(SkyAppNameMatcher.norm(filter))
            }
            if (results.isEmpty()) {
                list.addView(SkyPremiumUi.label(activity, "No encontré aplicaciones con ese nombre.",
                    14f, SkyPremiumUi.muted))
            }
            for (app in results) {
                val row = LinearLayout(activity).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    background = SkyPremiumUi.shape(activity, SkyPremiumUi.card, 14)
                    setPadding(dp(12), dp(10), dp(12), dp(10))
                    isClickable = true
                    isFocusable = true
                    contentDescription = "Abrir " + app.name
                    setOnClickListener {
                        dialog.dismiss()
                        if (supervisedControlEnabled() ||
                            trusted.getBoolean(app.packageName, false)) launchDirect(app)
                        else confirm(app)
                    }
                }
                row.addView(ImageView(activity).apply {
                    setImageDrawable(runCatching {
                        activity.packageManager.getApplicationIcon(app.packageName)
                    }.getOrNull())
                    scaleType = ImageView.ScaleType.FIT_CENTER
                }, LinearLayout.LayoutParams(dp(36), dp(36)))
                val texts = LinearLayout(activity).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(dp(13), 0, 0, 0)
                }
                texts.addView(SkyPremiumUi.label(activity, app.name, 15f,
                    SkyPremiumUi.white, true))
                texts.addView(SkyPremiumUi.label(activity,
                    if (supervisedControlEnabled()) "Apertura autorizada"
                    else if (trusted.getBoolean(app.packageName, false)) "Confiable"
                    else "Requiere autorización",
                    11f, SkyPremiumUi.muted))
                row.addView(texts, LinearLayout.LayoutParams(0, -2, 1f))
                row.addView(SkyPremiumUi.label(activity, "›", 22f, SkyPremiumUi.cyan))
                list.addView(row, LinearLayout.LayoutParams(-1, -2).apply {
                    bottomMargin = dp(7)
                })
            }
        }
        fun refresh() {
            val enabled = supervisedControlEnabled()
            state.text = if (enabled)
                "●  ACTIVADO · SKY puede abrir las apps cuando se lo ordenés."
                else "○  DESACTIVADO · SKY te pedirá confianza para abrir apps."
            state.setTextColor(if (enabled) SkyPremiumUi.cyan else SkyPremiumUi.muted)
            authorization.text = if (enabled) "REVOCAR CONTROL SUPERVISADO"
                else "ACEPTO · CONTROL SUPERVISADO"
            authorization.background = SkyPremiumUi.shape(activity,
                if (enabled) SkyPremiumUi.elevated else SkyPremiumUi.cyan, 15)
            authorization.setTextColor(if (enabled) SkyPremiumUi.white
                else SkyPremiumUi.background)
            render(search.text?.toString().orEmpty())
        }
        authorization.setOnClickListener { showControlAuthorization { refresh() } }
        search.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                render(s?.toString().orEmpty())
            }
            override fun afterTextChanged(s: Editable?) {}
        })
        refresh()
        SkyPremiumUi.showDialog(activity, dialog, 0.87)
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
            .setNegativeButton("Cancelar") { _, _ ->
                receipt("Abrir " + app.name, "REJECTED", "El propietario canceló la apertura")
            }
            .show()
    }

    private fun launchDirect(app: Launchable) {
        if (!launchLimiter.allow("launch:" + app.packageName)) {
            receipt("Abrir " + app.name, "REJECTED",
                "Límite local por órdenes duplicadas o demasiado frecuentes")
            say("Recibí varias órdenes seguidas. Esperá un momento para evitar aperturas duplicadas.")
            return
        }
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
