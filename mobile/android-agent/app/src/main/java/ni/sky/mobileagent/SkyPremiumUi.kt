package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.HorizontalScrollView
import android.widget.ScrollView

/** Identidad visual SKY: sin librerías de pago ni reemplazo de funciones existentes. */
object SkyPremiumUi {
    data class SectionSpec(val key: String, val title: String, val description: String, val icon: String)
    val background: Int = Color.rgb(8, 13, 34)
    val card: Int = Color.rgb(24, 34, 67)
    val elevated: Int = Color.rgb(31, 43, 81)
    val muted: Int = Color.rgb(179, 194, 222)
    val white: Int = Color.rgb(247, 249, 255)
    val cyan: Int = Color.rgb(94, 223, 247)
    val violet: Int = Color.rgb(139, 111, 247)
    val border: Int = Color.rgb(70, 83, 132)

    fun dp(activity: Activity, value: Int) =
        (activity.resources.displayMetrics.density * value + 0.5f).toInt()

    fun shape(activity: Activity, fill: Int = card, radius: Int = 19,
              stroke: Int = border): GradientDrawable = GradientDrawable().apply {
        setColor(fill)
        cornerRadius = dp(activity, radius).toFloat()
        if (stroke != Color.TRANSPARENT) setStroke(dp(activity, 1), stroke)
    }

    fun label(activity: Activity, value: String, size: Float = 14f,
              color: Int = white, bold: Boolean = false): TextView =
        TextView(activity).apply {
            text = value
            textSize = size
            setTextColor(color)
            includeFontPadding = true
            if (bold) typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
        }

    fun cardRow(activity: Activity, title: String, detail: String,
                icon: String, click: () -> Unit): LinearLayout {
        val row = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = shape(activity)
            setPadding(dp(activity, 15), dp(activity, 13),
                dp(activity, 12), dp(activity, 13))
            isClickable = true
            isFocusable = true
            elevation = dp(activity, 2).toFloat()
            contentDescription = title + ". " + detail
            setOnClickListener { click() }
        }
        row.addView(label(activity, icon, 23f, cyan),
            LinearLayout.LayoutParams(dp(activity, 40), -2))
        val column = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
        column.addView(label(activity, title, 15f, white, true))
        column.addView(label(activity, detail, 12f, muted).apply { maxLines = 3 })
        row.addView(column, LinearLayout.LayoutParams(0, -2, 1f))
        row.addView(label(activity, "›", 24f, muted))
        return row
    }

    fun addRow(parent: LinearLayout, row: View, activity: Activity) {
        parent.addView(row, LinearLayout.LayoutParams(-1, -2).apply {
            bottomMargin = dp(activity, 9)
        })
    }

    fun section(activity: Activity, title: String, description: String,
                symbol: String): LinearLayout {
        val wrapper = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(activity, 16), 0, dp(activity, 8))
            tag = SectionSpec(title, title, description, symbol)
        }
        wrapper.addView(label(activity, "$symbol  $title", 18f, white, true))
        wrapper.addView(label(activity, description, 12.5f, muted))
        return wrapper
    }

    fun styleChildren(activity: Activity, root: ViewGroup) {
        for (i in 0 until root.childCount) {
            val child = root.getChildAt(i)
            if (child.tag is SectionSpec) continue
            when (child) {
                is Button -> {
                    child.isAllCaps = false
                    child.textSize = 14f
                    child.setTextColor(white)
                    child.background = shape(activity, elevated, 15)
                    child.minHeight = dp(activity, 50)
                    child.setPadding(dp(activity, 15), dp(activity, 11),
                        dp(activity, 15), dp(activity, 11))
                    child.gravity = Gravity.CENTER_VERTICAL or Gravity.START
                    child.typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
                    val lp = child.layoutParams as? ViewGroup.MarginLayoutParams
                    if (lp != null) {
                        lp.bottomMargin = dp(activity, 7)
                        child.layoutParams = lp
                    }
                }
                is CheckBox -> {
                    child.textSize = 13.5f
                    child.setTextColor(white)
                    child.buttonTintList = ColorStateList.valueOf(cyan)
                    child.background = shape(activity, card, 14)
                    child.setPadding(dp(activity, 11), dp(activity, 10),
                        dp(activity, 11), dp(activity, 10))
                    child.minimumHeight = dp(activity, 52)
                }
                is EditText -> {
                    child.textSize = 15f
                    child.setTextColor(white)
                    child.setHintTextColor(muted)
                    child.background = shape(activity, card, 13)
                    child.setPadding(dp(activity, 14), dp(activity, 12),
                        dp(activity, 14), dp(activity, 12))
                }
                is TextView -> {
                    child.textSize = 13.5f
                    child.setTextColor(muted)
                    child.setPadding(dp(activity, 5), dp(activity, 9),
                        dp(activity, 5), dp(activity, 9))
                }
            }
            if (child is ViewGroup) styleChildren(activity, child)
        }
    }

    /**
     * Convierte los antiguos controles reales en paneles navegables.
     * Cada vista se mueve una sola vez; no recrea claves, permisos ni listeners.
     */
    fun settingsShell(activity: Activity, original: LinearLayout, onClose: () -> Unit): View {
        val elements = (0 until original.childCount).map { original.getChildAt(it) }
        original.removeAllViews()
        val tabs = LinkedHashMap<String, Pair<SectionSpec, LinearLayout>>()
        var current: LinearLayout? = null
        elements.forEach { child ->
            val spec = child.tag as? SectionSpec
            if (spec != null) {
                val group = LinearLayout(activity).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(dp(activity, 13), dp(activity, 12),
                        dp(activity, 13), dp(activity, 16))
                    background = shape(activity, SkyPremiumUi.background, 20)
                }
                group.addView(child)
                tabs[spec.key] = spec to group
                current = group
            } else {
                if (current == null) {
                    val fallback = SectionSpec("Inicio", "Inicio", "", "✦")
                    val group = LinearLayout(activity).apply {
                        orientation = LinearLayout.VERTICAL
                        background = shape(activity, SkyPremiumUi.background, 20)
                    }
                    tabs[fallback.key] = fallback to group
                    current = group
                }
                current?.addView(child)
            }
        }
        tabs.values.forEach { (_, group) -> styleChildren(activity, group) }
        val shell = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            background = shape(activity, SkyPremiumUi.background, 25)
            setPadding(dp(activity, 14), dp(activity, 15),
                dp(activity, 14), dp(activity, 10))
        }
        val titleRow = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val identity = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
        identity.addView(label(activity, "✦  SKY IA", 23f, white, true))
        identity.addView(label(activity, "CENTRO DE CONFIGURACIÓN  ·  ANDROID",
            11f, cyan, true).apply { letterSpacing = 0.08f })
        titleRow.addView(identity, LinearLayout.LayoutParams(0, -2, 1f))
        titleRow.addView(label(activity, "✕", 22f, white).apply {
            gravity = Gravity.CENTER
            background = shape(activity, elevated, 18)
            contentDescription = "Cerrar configuración"
            isClickable = true
            isFocusable = true
            setOnClickListener { onClose() }
        }, LinearLayout.LayoutParams(dp(activity, 48), dp(activity, 48)))
        shell.addView(titleRow)
        shell.addView(label(activity,
            "Elegí una categoría. Tus permisos y datos se mantienen como estaban.",
            12.5f, muted).apply { setPadding(0, dp(activity, 7), 0, dp(activity, 10)) })
        val tabRow = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL }
        val sectionHolder = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
        val scroll = ScrollView(activity).apply {
            isFillViewport = true
            isVerticalScrollBarEnabled = false
            addView(sectionHolder)
        }
        shell.addView(HorizontalScrollView(activity).apply {
            isHorizontalScrollBarEnabled = false
            addView(tabRow)
        })
        shell.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        var active = tabs.keys.firstOrNull().orEmpty()
        fun select(key: String) {
            active = key
            tabRow.removeAllViews()
            tabs.forEach { (name, pair) ->
                val selected = name == active
                val chip = label(activity, pair.first.icon + " " + name, 13f,
                    if (selected) background else white, selected).apply {
                    gravity = Gravity.CENTER
                    setPadding(dp(activity, 15), dp(activity, 11),
                        dp(activity, 15), dp(activity, 11))
                    this.background = shape(activity,
                        if (selected) cyan else elevated, 18,
                        if (selected) cyan else border)
                    setOnClickListener { select(name) }
                    isClickable = true
                    isFocusable = true
                    contentDescription = "Abrir sección " + name
                }
                tabRow.addView(chip, LinearLayout.LayoutParams(-2, -2).apply {
                    rightMargin = dp(activity, 8)
                    bottomMargin = dp(activity, 10)
                })
            }
            sectionHolder.removeAllViews()
            val group = tabs[key]?.second
            if (group != null) {
                (group.parent as? ViewGroup)?.removeView(group)
                sectionHolder.addView(group, LinearLayout.LayoutParams(-1, -2))
            }
            scroll.post { scroll.scrollTo(0, 0) }
        }
        if (active.isNotEmpty()) select(active)
        return shell
    }

    /** Pinta oscuro también el contenedor del diálogo: no deja marco blanco. */
    fun showDialog(activity: Activity, dialog: AlertDialog, heightPercent: Double = 0.88) {
        dialog.show()
        dialog.window?.apply {
            setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
            val width = (activity.resources.displayMetrics.widthPixels -
                dp(activity, 24)).coerceAtLeast(dp(activity, 280))
            val height = (activity.resources.displayMetrics.heightPixels *
                heightPercent.coerceIn(0.45, 0.96)).toInt()
            setLayout(width, height)
            setGravity(Gravity.CENTER)
            setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
        }
    }
}
