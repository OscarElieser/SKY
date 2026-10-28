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
import android.widget.ImageView
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
    private val violet = Color.rgb(125, 98, 245)
    private lateinit var mainSurface: LinearLayout
    private val faceCaption = text("SKY ESTÁ AQUÍ · TOCÁ PARA HABLAR", 12f, Color.rgb(207, 200, 252)).apply {
        gravity = Gravity.CENTER
        letterSpacing = 0.07f
        contentDescription = "Estado actual de SKY"
    }
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
        background = GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
            intArrayOf(Color.rgb(35, 30, 87), Color.rgb(15, 20, 59))).apply {
            cornerRadius = dp(28).toFloat()
        }
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
                intArrayOf(Color.rgb(7, 11, 32), Color.rgb(21, 18, 61),
                    Color.rgb(13, 31, 67))
            )
            setPadding(dp(12), dp(10), dp(12), dp(18))
        }
        mainSurface = main
        root.addView(main, FrameLayout.LayoutParams(-1, -1))
        voicePanel.onVisualStatusChanged = { label -> faceCaption.text = label }
        val header = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val brand = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_VERTICAL
        }
        brand.addView(text("SKY IA", 25f, white).apply {
            typeface = Typeface.create("sans-serif-black", Typeface.BOLD)
            letterSpacing = 0.075f
        })
        brand.addView(text("INTELIGENCIA PERSONAL", 9.5f, Color.rgb(175, 171, 220)).apply {
            letterSpacing = 0.12f
        })
        header.addView(ImageView(host).apply {
            setImageResource(R.drawable.sky_brand_emblem)
            scaleType = ImageView.ScaleType.FIT_CENTER
            contentDescription = "Emblema oficial SKY IA"
        }, LinearLayout.LayoutParams(dp(52), dp(52)).apply { rightMargin = dp(8) })
        header.addView(brand, LinearLayout.LayoutParams(0, dp(58), 1f))
        header.addView(connected, LinearLayout.LayoutParams(dp(25), dp(54)))
        header.addView(pill("⚙", Color.rgb(55, 48, 115), onSettings).apply {
            contentDescription = "Abrir ajustes y permisos de SKY Android"
            textSize = 22f
        }, LinearLayout.LayoutParams(dp(49), dp(48)))
        main.addView(header)

        // El personaje ocupa la pantalla. No se muestran explicaciones largas,
        // botones técnicos, tarjetas ni módulos hasta una orden expresa.
        voicePanel.setMinimalFace()
        main.addView(voicePanel, LinearLayout.LayoutParams(-1, 0, 1f))
        main.addView(faceCaption, LinearLayout.LayoutParams(-1, dp(36)))

        val actions = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        actions.addView(pill("⌨", Color.rgb(42, 43, 95)) { openChat() }.apply {
            textSize = 23f
            contentDescription = "Abrir conversación por texto"
        }, LinearLayout.LayoutParams(dp(56), dp(56)).apply { rightMargin = dp(9) })
        actions.addView(pill("🎙  HABLAR", violet) { voicePanel.listen() }.apply {
            textSize = 16f
            typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
            contentDescription = "Activar micrófono para hablar con SKY"
        }, LinearLayout.LayoutParams(0, dp(56), 1f))
        actions.addView(pill("■", Color.rgb(42, 43, 95)) { voicePanel.stop() }.apply {
            textSize = 18f
            contentDescription = "Detener la escucha y la voz"
        }, LinearLayout.LayoutParams(dp(56), dp(56)).apply { leftMargin = dp(9) })
        main.addView(actions)
        buildPanel()
    }

    /** Avoid Android 15/16 three-button navigation overlap without hiding system controls. */
    fun applyNavigationInset(bottomPx: Int) {
        if (!::mainSurface.isInitialized) return
        mainSurface.setPadding(dp(12), dp(10), dp(12),
            maxOf(dp(18), bottomPx + dp(9)))
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
        header.addView(pill("Historial", Color.rgb(53, 56, 107)) { toggleHistory() }.apply {
            textSize = 12f
            contentDescription = "Mostrar o reducir historial de conversación"
        }, LinearLayout.LayoutParams(dp(86), dp(40)).apply { rightMargin = dp(7) })
        header.addView(pill("×", Color.rgb(60, 62, 119)) { closePanel() }.apply {
            textSize = 28f
            contentDescription = "Cerrar panel y volver a SKY"
        }, LinearLayout.LayoutParams(dp(47), dp(45)))
        panel.addView(header)
        panel.addView(panelSubtitle)
        val scroll = ScrollView(host).apply {
            isFillViewport = true
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
        footer.addView(pill("Acceso", Color.TRANSPARENT, onChatAccess),
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
        panelSubtitle.text = "Consultas con SKY Android · Internet opcional"
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

    private fun toggleHistory() {
        expandedHistory = !expandedHistory
        chatOutput.text = if (history.isEmpty()) "Todavía no hay mensajes en esta sesión."
            else history.takeLast(if (expandedHistory) 8 else 3)
                .joinToString("\n\n────────────\n\n")
    }

    fun setConnection(linked: Boolean, chatReady: Boolean, mobileCloud: Boolean = false) {
        connected.text = if (mobileCloud || chatReady) "●" else if (linked) "◉" else "○"
        connected.setTextColor(
            if (mobileCloud || chatReady) Color.rgb(139, 234, 191) else cyan
        )
        status.text = if (mobileCloud) "SKY Android lista"
            else if (linked) "SKY vinculada" else "SKY sin configurar"
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

    fun addExchange(question: String, answer: String, engine: String, revealPanel: Boolean = true) {
        history.add("Vos: " + question.take(350) + "\n\nSKY: " + answer.take(2500))
        if (history.size > 20) history.removeAt(0)
        val entries = if (expandedHistory) history.takeLast(8) else history.takeLast(3)
        chatOutput.text = entries.joinToString("\n\n────────────\n\n")
        if (revealPanel && !isPanelOpen()) openChat()
    }
}
