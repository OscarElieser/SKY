package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.view.Gravity
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.text.InputFilter

/** Explorador privado, paginado y accesible. Toda consulta usa la base SQLite local. */
class SkyPremiumHistory(
    private val host: Activity,
    private val archive: SkyConversationArchive,
    private val onOpenChat: (SkyConversationArchive.Entry) -> Unit,
    private val onExportEntry: (SkyConversationArchive.Entry) -> Unit,
    private val onExportAll: () -> Unit,
    private val onHistoryChanged: () -> Unit
) {
    private val ui = SkyPremiumUi
    private fun gap(size: Int): View = View(host).apply {
        layoutParams = LinearLayout.LayoutParams(1, ui.dp(host, size))
    }
    private fun button(title: String, selected: Boolean = false, click: () -> Unit): TextView =
        ui.label(host, title, 13f, if (selected) ui.background else ui.white, true).apply {
            gravity = Gravity.CENTER
            setPadding(ui.dp(host, 13), ui.dp(host, 11), ui.dp(host, 13), ui.dp(host, 11))
            background = ui.shape(host, if (selected) ui.cyan else ui.elevated, 16,
                if (selected) ui.cyan else ui.border)
            setOnClickListener { click() }
            isClickable = true
            isFocusable = true
            contentDescription = title
        }

    fun show(initialQuery: String = "", beforeId: Long? = null): AlertDialog {
        val filters = listOf("Todos", "Hoy", "Ayer", "Groq", "Gemini", "Favoritos")
        var activeFilter = "Todos"
        var cursor = beforeId
        var query = initialQuery.take(100)
        val root = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            background = ui.shape(host, ui.background, 26, ui.border)
            setPadding(ui.dp(host, 17), ui.dp(host, 15), ui.dp(host, 17), ui.dp(host, 14))
        }
        lateinit var dialog: AlertDialog
        lateinit var refresh: () -> Unit
        lateinit var updateChips: () -> Unit
        val top = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val name = LinearLayout(host).apply { orientation = LinearLayout.VERTICAL }
        name.addView(ui.label(host, "✦  Historial SKY", 22f, ui.white, true))
        name.addView(ui.label(host, "Consultas privadas · guardadas en este teléfono",
            12f, ui.muted))
        top.addView(name, LinearLayout.LayoutParams(0, -2, 1f))
        top.addView(button("✕") { dialog.dismiss() })
        root.addView(top)
        root.addView(gap(16))
        val searchRow = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val searchInput = EditText(host).apply {
            hint = "Buscar título, pregunta o respuesta"
            setText(query)
            setSingleLine(true)
            textSize = 14f
            imeOptions = EditorInfo.IME_ACTION_SEARCH
            filters = arrayOf(InputFilter.LengthFilter(100))
            setHintTextColor(ui.muted)
            setTextColor(ui.white)
            background = ui.shape(host)
            setPadding(ui.dp(host, 13), ui.dp(host, 11), ui.dp(host, 9), ui.dp(host, 11))
        }
        searchRow.addView(searchInput, LinearLayout.LayoutParams(0, -2, 1f))
        val runSearch = button("⌕ Buscar") {
            query = searchInput.text.toString().trim()
            cursor = null
            refresh()
        }
        searchRow.addView(runSearch, LinearLayout.LayoutParams(-2, -2).apply {
            leftMargin = ui.dp(host, 7)
        })
        root.addView(searchRow)
        root.addView(gap(11))

        val chipContainer = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val chips = HorizontalScrollView(host).apply {
            isHorizontalScrollBarEnabled = false
            addView(chipContainer)
        }
        root.addView(chips)
        val counter = ui.label(host, "", 12f, ui.muted).apply {
            setPadding(ui.dp(host, 2), ui.dp(host, 10), 0, ui.dp(host, 8))
        }
        root.addView(counter)
        val list = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, ui.dp(host, 1), 0, ui.dp(host, 9))
        }
        root.addView(ScrollView(host).apply {
            isFillViewport = true
            isVerticalScrollBarEnabled = false
            addView(list)
        }, LinearLayout.LayoutParams(-1, 0, 1f))
        val footer = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        footer.addView(button("⬇  Exportar todo") { onExportAll() },
            LinearLayout.LayoutParams(0, -2, 1f))
        footer.addView(button("Cerrar") { dialog.dismiss() },
            LinearLayout.LayoutParams(0, -2, 1f).apply { leftMargin = ui.dp(host, 8) })
        root.addView(footer)

        fun openDetail(item: SkyConversationArchive.Entry) {
            val body = LinearLayout(host).apply {
                orientation = LinearLayout.VERTICAL
                background = ui.shape(host, ui.background, 24)
                setPadding(ui.dp(host, 18), ui.dp(host, 18), ui.dp(host, 18), ui.dp(host, 18))
            }
            body.addView(ui.label(host, item.title, 20f, ui.white, true))
            body.addView(ui.label(host, item.localTime() + "  ·  " + item.engine,
                12f, ui.cyan))
            body.addView(gap(12))
            val conversation = ScrollView(host).apply {
                isVerticalScrollBarEnabled = false
                addView(ui.label(host, "VOS\n" + item.question +
                    "\n\nSKY IA\n" + item.answer, 15f, ui.white).apply {
                    setPadding(ui.dp(host, 7), ui.dp(host, 10),
                        ui.dp(host, 7), ui.dp(host, 10))
                })
            }
            body.addView(conversation, LinearLayout.LayoutParams(-1, 0, 1f))
            val actions = LinearLayout(host).apply { orientation = LinearLayout.VERTICAL }
            lateinit var detail: AlertDialog
            ui.addRow(actions, button("↗  Abrir en conversación") {
                detail.dismiss()
                dialog.dismiss()
                onOpenChat(item)
            }, host)
            ui.addRow(actions, button(if (item.favorite) "★ Quitar de favoritos"
                else "☆ Añadir a favoritos") {
                archive.setFavorite(item.id, !item.favorite)
                detail.dismiss()
                refresh()
            }, host)
            ui.addRow(actions, button("✎  Renombrar título") {
                detail.dismiss()
                val editor = EditText(host).apply {
                    setText(item.title)
                    filters = arrayOf(InputFilter.LengthFilter(100))
                    setSingleLine(true)
                }
                AlertDialog.Builder(host).setTitle("Renombrar consulta")
                    .setView(editor)
                    .setPositiveButton("Guardar") { _, _ ->
                        if (runCatching { archive.rename(item.id, editor.text.toString()) }
                                .getOrDefault(false)) {
                            onHistoryChanged()
                            refresh()
                        }
                    }.setNegativeButton("Cancelar", null).show()
            }, host)
            ui.addRow(actions, button("⬇  Exportar respuesta") {
                detail.dismiss()
                onExportEntry(item)
            }, host)
            ui.addRow(actions, button("Eliminar esta consulta") {
                detail.dismiss()
                AlertDialog.Builder(host).setTitle("Eliminar consulta")
                    .setMessage("Se eliminará solo esta consulta del teléfono. Esta acción no se puede deshacer.")
                    .setPositiveButton("Eliminar") { _, _ ->
                        if (archive.delete(item.id)) {
                            onHistoryChanged()
                            refresh()
                        }
                    }.setNegativeButton("Cancelar", null).show()
            }, host)
            body.addView(actions)
            detail = AlertDialog.Builder(host).setView(body).create()
            ui.showDialog(host, detail, 0.82)
        }

        updateChips = {
            chipContainer.removeAllViews()
            filters.forEach { filter ->
                chipContainer.addView(button(filter, filter == activeFilter) {
                    activeFilter = filter
                    cursor = null
                    updateChips()
                    refresh()
                }, LinearLayout.LayoutParams(-2, -2).apply {
                    rightMargin = ui.dp(host, 8)
                })
            }
        }

        refresh = {
            list.removeAllViews()
            val entries = archive.page(query, cursor, 26, activeFilter)
            val shown = entries.take(25)
            counter.text = "●  " + activeFilter + "  ·  " + shown.size +
                (if (entries.size > 25) "+ resultados" else " resultados") +
                "  ·  Hora local"
            if (shown.isEmpty()) {
                ui.addRow(list, ui.label(host,
                    "Todavía no hay consultas para este filtro.\nProbá otra palabra o categoría.",
                    15f, ui.muted).apply {
                        setPadding(ui.dp(host, 18), ui.dp(host, 25),
                            ui.dp(host, 18), ui.dp(host, 25))
                        background = ui.shape(host)
                    }, host)
            }
            shown.forEach { entry ->
                val details = entry.localTime() + "   •   " + entry.engine.take(30)
                val label = (if (entry.favorite) "★  " else "") + entry.title.take(75)
                ui.addRow(list, ui.cardRow(host, label, details +
                    "\n" + entry.answer.replace("\n", " ").take(92), "◉") {
                    openDetail(entry)
                }, host)
            }
            if (entries.size > 25 && shown.isNotEmpty()) {
                ui.addRow(list, button("Ver consultas anteriores  ↓") {
                    cursor = shown.last().id
                    refresh()
                }, host)
            }
            if (cursor != null) {
                ui.addRow(list, button("← Volver a las más recientes") {
                    cursor = null
                    refresh()
                }, host)
            }
        }

        // Funciones locales pueden referirse entre sí, sin iniciar búsquedas remotas.
        searchInput.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_SEARCH) {
                query = searchInput.text.toString().trim()
                cursor = null
                refresh()
                true
            } else false
        }
        dialog = AlertDialog.Builder(host).setView(root).create()
        updateChips()
        refresh()
        ui.showDialog(host, dialog, 0.90)
        return dialog
    }
}
