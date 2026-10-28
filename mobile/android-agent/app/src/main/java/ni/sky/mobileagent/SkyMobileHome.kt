package ni.sky.mobileagent

import android.app.Activity
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.CheckBox
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.text.InputFilter
import android.text.InputType
import android.text.TextUtils

/**
 * Inicio premium minimalista: solo ojos, voz, acceso a conversación y Ajustes.
 * Los paneles se crean una sola vez y permanecen ocultos hasta que el dueño
 * los solicita por voz, chat o toque. No arranca herramientas en segundo plano.
 */
class SkyMobileHome(
    private val host: Activity,
    val voicePanel: SkyEyeVoicePanel,
    private val onSend: () -> Unit,
    private val onSettings: () -> Unit,
    private val onChatAccess: () -> Unit,
    private val onDiagnostics: () -> Unit
) {
    private val white = Color.WHITE
    private val soft = Color.rgb(202, 208, 233)
    private val cyan = Color.rgb(132, 215, 245)
    private val violet = Color.rgb(117, 95, 229)
    private val history = ArrayList<String>()
    private var activeModule = ""
    private var expandedHistory = false

    private fun dp(v: Int) = (v * host.resources.displayMetrics.density + 0.5f).toInt()
    private fun bg(color: Int, radius: Int) = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(radius).toFloat()
    }
    private fun text(value: String, size: Float, color: Int) = TextView(host).apply {
        text = value
        textSize = size
        setTextColor(color)
        gravity = Gravity.CENTER_VERTICAL
    }
    private fun pill(value: String, color: Int, click: () -> Unit) = text(value, 15f, white).apply {
        gravity = Gravity.CENTER
        background = bg(color, 25)
        setPadding(dp(12), dp(10), dp(12), dp(10))
        isClickable = true
        isFocusable = true
        setOnClickListener { click() }
    }
    private fun moduleTitle(id: String): String = when(id) {
        "investigacion" -> "Investigación"
        "documentos" -> "Documentos"
        "codigo" -> "Programación"
        "docente" -> "SKY Docente"
        "creativo" -> "SKY Creativa"
        "metaverso" -> "Metaverso"
        "deportes" -> "Deportes"
        else -> "Conversación"
    }

    val root = FrameLayout(host)
    val status = text("SKY", 12f, soft).apply {
        visibility = View.GONE
    }
    private val connected = text("○", 13f, cyan)
    val chatInput = EditText(host).apply {
        hint = "Escribí o pedí un panel a SKY"
        setHintTextColor(Color.rgb(175, 180, 211))
        setTextColor(white)
        textSize = 15f
        background = null
        inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
        maxLines = 4
        minLines = 1
        filters = arrayOf(InputFilter.LengthFilter(4000))
        setPadding(dp(14), dp(8), dp(4), dp(8))
        setOnEditorActionListener { _, id, _ ->
            if (id == EditorInfo.IME_ACTION_SEND) {
                onSend()
                true
            } else false
        }
    }
    val chatOutput = text("Conversación con SKY", 14f, white).apply {
        setPadding(dp(9), dp(8), dp(9), dp(8))
    }
    val cloudConsent = CheckBox(host).apply {
        text = "Nube autorizada para ESTE mensaje e historial"
        textSize = 12.5f
        setTextColor(soft)
        buttonTintList = ColorStateList.valueOf(cyan)
        isChecked = false
    }
    val privateConsent = CheckBox(host).apply {
        text = "Enviar datos privados a la nube para ESTE mensaje"
        textSize = 12.5f
        setTextColor(soft)
        buttonTintList = ColorStateList.valueOf(cyan)
        isChecked = false
    }

    private val dialogBackdrop = FrameLayout(host).apply {
        setBackgroundColor(Color.argb(189, 4, 7, 28))
        visibility = View.GONE
        isClickable = true
        setOnClickListener { closePanel() }
    }
    private val panel = LinearLayout(host).apply {
        orientation = LinearLayout.VERTICAL
        background = bg(Color.rgb(28, 30, 74), 28)
        setPadding(dp(17), dp(12), dp(17), dp(16))
        isClickable = true
        elevation = dp(12).toFloat()
    }
    private val panelTitle = text("Conversación", 19f, white).apply {
        typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
    }
    private val panelSubtitle = text("", 12f, soft).apply { visibility = View.GONE }
    private val privacy = LinearLayout(host).apply {
        orientation = LinearLayout.VERTICAL
        visibility = View.GONE
        addView(cloudConsent)
        addView(privateConsent)
    }

    init {
        val main = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                intArrayOf(Color.rgb(10, 16, 42), Color.rgb(26, 29, 75),
                    Color.rgb(19, 37, 77))
            )
            setPadding(dp(18), dp(12), dp(18), dp(14))
        }
        root.addView(main, FrameLayout.LayoutParams(-1, -1))
        val header = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(text("SKY", 24f, white).apply {
            typeface = Typeface.create("sans-serif-black", Typeface.BOLD)
            letterSpacing = 0.06f
        }, LinearLayout.LayoutParams(0, dp(48), 1f))
        header.addView(connected, LinearLayout.LayoutParams(dp(24), dp(48)))
        header.addView(pill("⚙", Color.rgb(52, 55, 107), onSettings).apply {
            contentDescription = "Abrir ajustes y vinculación de SKY"
            textSize = 23f
        }, LinearLayout.LayoutParams(dp(48), dp(44)))
        main.addView(header)

        // El personaje ocupa la pantalla. No se muestran explicaciones largas,
        // botones técnicos, tarjetas ni módulos hasta una orden expresa.
        voicePanel.setMinimalFace()
        main.addView(voicePanel, LinearLayout.LayoutParams(-1, 0, 1f))
        main.addView(text("SKY", 14f, soft).apply {
            gravity = Gravity.CENTER
            letterSpacing = 0.2f
        }, LinearLayout.LayoutParams(-1, dp(30)))

        val actions = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        actions.addView(pill("⌨", Color.rgb(58, 62, 119)) { openChat() }.apply {
            textSize = 23f
            contentDescription = "Abrir panel de conversación"
        }, LinearLayout.LayoutParams(dp(60), dp(56)).apply { rightMargin = dp(14) })
        actions.addView(pill("🎙  Hablar", violet) { voicePanel.listen() }.apply {
            contentDescription = "Hablar con SKY por voz"
        }, LinearLayout.LayoutParams(0, dp(56), 1f))
        actions.addView(pill("■", Color.rgb(58, 62, 119)) { voicePanel.stop() }.apply {
            textSize = 20f
            contentDescription = "Detener voz de SKY"
        }, LinearLayout.LayoutParams(dp(60), dp(56)).apply { leftMargin = dp(14) })
        main.addView(actions)
        buildPanel()
    }

    private fun buildPanel() {
        val layout = FrameLayout.LayoutParams(-1, -1)
        root.addView(dialogBackdrop, layout)
        val panelLp = FrameLayout.LayoutParams(-1, -1, Gravity.BOTTOM).apply {
            topMargin = dp(104)
        }
        dialogBackdrop.addView(panel, panelLp)
        val header = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(panelTitle, LinearLayout.LayoutParams(0, dp(50), 1f))
        header.addView(pill("×", Color.rgb(60, 62, 119)) { closePanel() }.apply {
            textSize = 28f
            contentDescription = "Cerrar panel y volver a SKY"
        }, LinearLayout.LayoutParams(dp(47), dp(45)))
        panel.addView(header)
        panel.addView(panelSubtitle)
        val scroll = ScrollView(host).apply {
            fillViewport = true
            isVerticalScrollBarEnabled = false
            addView(chatOutput)
        }
        panel.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        val composer = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = bg(Color.rgb(52, 56, 109), 23)
        }
        composer.addView(chatInput, LinearLayout.LayoutParams(0, -2, 1f))
        composer.addView(pill("➤", violet, onSend).apply {
            contentDescription = "Enviar mensaje escrito a SKY"
            textSize = 24f
        }, LinearLayout.LayoutParams(dp(53), dp(50)))
        panel.addView(composer, LinearLayout.LayoutParams(-1, -2))
        val footer = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        footer.addView(pill("🎙", Color.TRANSPARENT) { voicePanel.listen() }.apply {
            contentDescription = "Dictar mensaje a SKY"
        }, LinearLayout.LayoutParams(0, dp(44), 1f))
        footer.addView(pill("Privacidad", Color.TRANSPARENT) {
            privacy.visibility = if (privacy.visibility == View.GONE) View.VISIBLE else View.GONE
        }, LinearLayout.LayoutParams(0, dp(44), 1f))
        footer.addView(pill("Motor", Color.TRANSPARENT, onDiagnostics),
            LinearLayout.LayoutParams(0, dp(44), 1f))
        footer.addView(pill("Chat", Color.TRANSPARENT, onChatAccess),
            LinearLayout.LayoutParams(0, dp(44), 1f))
        panel.addView(footer)
        panel.addView(privacy)
    }

    fun isPanelOpen() = dialogBackdrop.visibility == View.VISIBLE

    fun openChat() {
        activeModule = ""
        panelTitle.text = "Conversación"
        panelSubtitle.visibility = View.GONE
        dialogBackdrop.visibility = View.VISIBLE
    }

    fun openModule(id: String) {
        activeModule = id
        panelTitle.text = moduleTitle(id)
        panelSubtitle.text = "Panel solicitado · consultas con SKY Core"
        panelSubtitle.visibility = View.VISIBLE
        chatOutput.text = "¿Qué necesitas hacer en " + moduleTitle(id) + "?\n\n" +
            "SKY puede conversar sobre esta tarea. La ejecución de herramientas " +
            "requiere un servicio compatible y permisos del dispositivo."
        dialogBackdrop.visibility = View.VISIBLE
    }

    fun closePanel() {
        dialogBackdrop.visibility = View.GONE
        privacy.visibility = View.GONE
        chatInput.clearFocus()
        (host.getSystemService(Activity.INPUT_METHOD_SERVICE)
            as? android.view.inputmethod.InputMethodManager)
            ?.hideSoftInputFromWindow(chatInput.windowToken, 0)
    }

    fun setConnection(linked: Boolean, chatReady: Boolean) {
        connected.text = if (chatReady) "●" else if (linked) "◉" else "○"
        connected.setTextColor(
            if (chatReady) Color.rgb(139, 234, 191) else cyan
        )
        status.text = if (linked) "SKY vinculada" else "SKY sin vincular"
        connected.contentDescription = status.text
    }

    fun showMessage(s: String) {
        status.text = s
        if (isPanelOpen()) chatOutput.text = s
        else {
            // El estado se comunica sin saturar la portada minimalista.
            android.widget.Toast.makeText(host, s, android.widget.Toast.LENGTH_SHORT).show()
        }
    }

    fun addExchange(question: String, answer: String, engine: String) {
        history.add("Vos: " + question.take(350) + "\n\nSKY: " + answer.take(2500))
        if (history.size > 20) history.removeAt(0)
        val entries = if (expandedHistory) history.takeLast(8) else history.takeLast(3)
        chatOutput.text = entries.joinToString("\n\n────────────\n\n")
        if (!isPanelOpen()) openChat()
    }
}
