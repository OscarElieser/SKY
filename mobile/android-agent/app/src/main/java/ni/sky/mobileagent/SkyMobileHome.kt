package ni.sky.mobileagent

import android.app.Activity
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.text.InputFilter
import android.text.InputType
import android.text.TextUtils
import android.text.method.ScrollingMovementMethod

/** SKY inmersiva. El emparejamiento y los permisos permanecen en Ajustes. */
class SkyMobileHome(
    private val host: Activity,
    val voicePanel: SkyEyeVoicePanel,
    private val onSend: () -> Unit,
    private val onSettings: () -> Unit,
    private val onChatAccess: () -> Unit,
    private val onDiagnostics: () -> Unit
) {
    private val muted = Color.rgb(199, 202, 230)
    private val cyan = Color.rgb(133, 218, 248)
    private val violet = Color.rgb(126, 100, 236)
    private val history = ArrayList<String>()
    private var expanded = false

    private fun dp(n: Int) = (n * host.resources.displayMetrics.density + 0.5f).toInt()
    private fun bg(color: Int, radius: Int) = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(radius).toFloat()
    }
    private fun label(s: String, size: Float, color: Int) = TextView(host).apply {
        text = s
        textSize = size
        setTextColor(color)
        gravity = Gravity.CENTER_VERTICAL
    }
    private fun chip(s: String, color: Int, click: () -> Unit) = label(s, 12.5f, Color.WHITE).apply {
        gravity = Gravity.CENTER
        background = bg(color, 20)
        setPadding(dp(8), dp(9), dp(8), dp(9))
        isClickable = true
        isFocusable = true
        setOnClickListener { click() }
    }
    val root = LinearLayout(host).apply {
        orientation = LinearLayout.VERTICAL
        background = GradientDrawable(GradientDrawable.Orientation.TL_BR, intArrayOf(
            Color.rgb(12, 21, 51), Color.rgb(33, 31, 78), Color.rgb(25, 38, 79)))
        setPadding(dp(14), dp(6), dp(14), dp(5))
    }
    val status = label("Sin vincular", 13f, muted)
    private val online = label("○  SKY SIN VINCULAR", 11f, cyan)
    val chatInput = EditText(host).apply {
        hint = "Escribí a SKY..."
        setHintTextColor(Color.rgb(183, 184, 205))
        setTextColor(Color.WHITE)
        textSize = 15f
        inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
        minLines = 1
        maxLines = 3
        filters = arrayOf(InputFilter.LengthFilter(4000))
        background = null
        setPadding(dp(12), dp(7), dp(5), dp(7))
    }
    val chatOutput = label("¡Hola! Soy SKY 💜. Estoy lista para conversar.", 14f, Color.WHITE).apply {
        maxLines = 4
        ellipsize = TextUtils.TruncateAt.END
    }
    val cloudConsent = CheckBox(host).apply {
        text = "Permito nube para ESTE mensaje y su historial"
        textSize = 12.5f
        setTextColor(muted)
        buttonTintList = ColorStateList.valueOf(cyan)
        isChecked = false
    }
    val privateConsent = CheckBox(host).apply {
        text = "Permito datos privados en nube para ESTE mensaje"
        textSize = 12.5f
        setTextColor(muted)
        buttonTintList = ColorStateList.valueOf(cyan)
        isChecked = false
    }
    private val privacy = LinearLayout(host).apply {
        orientation = LinearLayout.VERTICAL
        background = bg(Color.rgb(44, 47, 97), 14)
        setPadding(dp(8), dp(2), dp(8), dp(2))
        addView(cloudConsent)
        addView(privateConsent)
        visibility = View.GONE
    }

    init {
        val header = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            minimumHeight = dp(52)
        }
        val logo = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            addView(label("SKY", 26f, Color.WHITE).apply {
                typeface = Typeface.create("sans-serif-black", Typeface.BOLD)
                letterSpacing = 0.07f
            })
            addView(online)
        }
        header.addView(logo, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(chip("⚙  Ajustes", Color.rgb(59, 61, 119), onSettings))
        root.addView(header)
        root.addView(label("Tu compañera inteligente", 14f, muted).apply {
            gravity = Gravity.CENTER
        })
        voicePanel.setImmersive()
        root.addView(voicePanel, LinearLayout.LayoutParams(-1, 0, 1f))
        val shortcuts = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        val ideas = arrayOf(
            "🔎 Investigar" to "Ayudame a investigar: ",
            "📄 Documentos" to "Ayudame a crear un documento sobre ",
            "💻 Código" to "Ayudame a programar y explicar: "
        )
        for ((name, prompt) in ideas) {
            shortcuts.addView(chip(name, Color.rgb(65, 58, 121)) {
                chatInput.setText(prompt)
                chatInput.setSelection(chatInput.length())
                chatInput.requestFocus()
            }, LinearLayout.LayoutParams(0, -2, 1f).apply {
                leftMargin = dp(2)
                rightMargin = dp(2)
            })
        }
        root.addView(shortcuts)
        val answerBox = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            background = bg(Color.rgb(49, 55, 108), 20)
            setPadding(dp(12), dp(8), dp(12), dp(9))
        }
        val answerHeader = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        answerHeader.addView(label("✦  Conversación", 13f, cyan), LinearLayout.LayoutParams(0, -2, 1f))
        answerHeader.addView(chip("Historial", Color.rgb(79, 79, 134)) { toggleHistory() })
        answerBox.addView(answerHeader)
        answerBox.addView(chatOutput, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(5)
        })
        root.addView(answerBox, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(7)
            bottomMargin = dp(7)
        })
        root.addView(privacy)
        val composer = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = bg(Color.rgb(52, 57, 102), 25)
            setPadding(dp(5), dp(2), dp(5), dp(2))
            minimumHeight = dp(53)
        }
        composer.addView(chatInput, LinearLayout.LayoutParams(0, -2, 1f))
        composer.addView(chip("➤ Enviar", violet, onSend).apply {
            contentDescription = "Enviar mensaje a SKY"
            minimumHeight = dp(43)
        })
        root.addView(composer)
        val footer = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            minimumHeight = dp(39)
        }
        footer.addView(chip("🔒 Privacidad", Color.TRANSPARENT) {
            privacy.visibility = if (privacy.visibility == View.GONE) View.VISIBLE else View.GONE
        }, LinearLayout.LayoutParams(0, -2, 1f))
        footer.addView(chip("☁ Motor", Color.TRANSPARENT, onDiagnostics),
            LinearLayout.LayoutParams(0, -2, 1f))
        footer.addView(chip("🔑 Chat", Color.TRANSPARENT, onChatAccess),
            LinearLayout.LayoutParams(0, -2, 1f))
        root.addView(footer)
    }

    fun setConnection(linked: Boolean, chatReady: Boolean) {
        online.text = when {
            !linked -> "○  SIN VINCULAR"
            !chatReady -> "◉  CONECTADO · ACTIVAR CHAT"
            else -> "●  SKY VINCULADA"
        }
        online.setTextColor(if (chatReady) Color.rgb(157, 233, 195) else cyan)
        status.text = when {
            !linked -> "Configurá SKY desde Ajustes."
            !chatReady -> "Activá la conversación en Ajustes."
            else -> "SKY conectada."
        }
    }

    fun showMessage(s: String) {
        status.text = s
        if (history.isEmpty()) chatOutput.text = s
    }

    fun addExchange(question: String, answer: String, engine: String) {
        val entry = "Vos: " + question.take(160) + "\nSKY (" + engine.take(20) + "): " +
            answer.take(1600)
        history.add(entry)
        if (history.size > 20) history.removeAt(0)
        chatOutput.maxLines = if (expanded) 9 else 4
        chatOutput.text = if (expanded) history.takeLast(6).joinToString("\n\n")
            else "SKY: " + answer
    }

    private fun toggleHistory() {
        expanded = !expanded
        chatOutput.maxLines = if (expanded) 9 else 4
        chatOutput.text = if (expanded && history.isNotEmpty()) {
            history.takeLast(6).joinToString("\n\n")
        } else history.lastOrNull() ?: "¡Hola! Soy SKY 💜."
        if (expanded) chatOutput.movementMethod = ScrollingMovementMethod()
    }
}
