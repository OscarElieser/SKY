package ni.sky.mobileagent

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.WebResourceRequest
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.text.Editable
import android.text.TextWatcher
import android.widget.CheckBox
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.HorizontalScrollView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
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
    private val onDiagnostics: () -> Unit,
    private val onStopHandsFree: () -> Unit
) {
    private val white = Color.WHITE
    private val soft = Color.rgb(202, 208, 233)
    private val cyan = Color.rgb(132, 215, 245)
    private val violet = Color.rgb(125, 98, 245)
    private lateinit var mainSurface: LinearLayout
    private lateinit var manualTalkButton: View
    private var handsFreeActive = false
    private val faceCaption = text("SKY LISTA · TOCÁ PARA HABLAR", 12f, Color.rgb(207, 200, 252)).apply {
        gravity = Gravity.CENTER
        letterSpacing = 0.07f
        contentDescription = "Estado actual de SKY"
    }
    private data class Exchange(
        val question: String,
        val answer: String,
        val engine: String,
        val sources: List<SkyPhoneCloud.Source>,
        val googleSearchHtml: String
    )
    private val history = ArrayList<Exchange>()
    private var activeModule = ""
    private var expandedHistory = false
    private var keyboardVisible = false
    private var pendingQuestion: String? = null
    private var pendingInfo: String? = null
    private lateinit var conversationScroll: ScrollView
    private lateinit var conversationRows: LinearLayout
    private lateinit var footerBar: LinearLayout
    private lateinit var suggestionBar: HorizontalScrollView
    private lateinit var sendButton: TextView
    private lateinit var panelLayout: FrameLayout.LayoutParams
    private val progressLabel = text("SKY lista para conversar", 11f, soft).apply {
        gravity = Gravity.CENTER_VERTICAL
        setPadding(dp(6), dp(4), dp(6), dp(7))
        contentDescription = "Estado de conversación"
    }

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
        hint = "Escribile a SKY..."
        setHintTextColor(Color.rgb(175, 180, 211))
        setTextColor(white)
        textSize = 15f
        background = null
        inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or
            InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        imeOptions = EditorInfo.IME_ACTION_SEND
        maxLines = 4
        minLines = 1
        filters = arrayOf(InputFilter.LengthFilter(4000))
        setPadding(dp(15), dp(10), dp(7), dp(10))
        addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                if (::sendButton.isInitialized) updateSendButton()
                if (::suggestionBar.isInitialized) updateSuggestions()
            }
            override fun afterTextChanged(s: Editable?) = Unit
        })
        setOnEditorActionListener { _, id, _ ->
            if (id == EditorInfo.IME_ACTION_SEND) {
                onSend()
                true
            } else false
        }
    }
    val chatOutput = text("¿En qué te ayudo hoy?\n\nEscribí tu mensaje o hablame con naturalidad.", 15f, soft).apply {
        gravity = Gravity.CENTER
        setPadding(dp(15), dp(24), dp(15), dp(24))
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
        manualTalkButton = pill("🎙  HABLAR", violet) { voicePanel.listen() }.apply {
            textSize = 16f
            typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
            contentDescription = "Activar micrófono para hablar con SKY"
        }
        actions.addView(manualTalkButton, LinearLayout.LayoutParams(0, dp(56), 1f))
        actions.addView(pill("■", Color.rgb(42, 43, 95)) {
            if (handsFreeActive) onStopHandsFree() else voicePanel.stop()
        }.apply {
            textSize = 18f
            contentDescription = "Detener la escucha y la voz"
        }, LinearLayout.LayoutParams(dp(56), dp(56)).apply { leftMargin = dp(9) })
        main.addView(actions)
        buildPanel()
    }

    fun setHandsFreeActive(enabled: Boolean) {
        handsFreeActive = enabled
        voicePanel.setHandsFreeActive(enabled)
        if (::manualTalkButton.isInitialized) manualTalkButton.visibility =
            if (enabled) View.GONE else View.VISIBLE
        faceCaption.text = if (enabled) "SKY DURMIENDO · DECÍ SKY" else "SKY LISTA · TOCÁ PARA HABLAR"
    }

    /**
     * Insets are handled by the root, not by stacking a navigation inset below
     * the IME. On Android 15/16 the composer must move with the software keyboard.
     */
    fun applyWindowInsets(topPx: Int, bottomPx: Int, imeVisible: Boolean) {
        root.setPadding(0, topPx, 0, bottomPx)
        keyboardVisible = imeVisible
        if (::panelLayout.isInitialized) {
            val margin = dp(if (imeVisible) 4 else 104)
            if (panelLayout.topMargin != margin) {
                panelLayout.topMargin = margin
                panel.layoutParams = panelLayout
            }
        }
        if (::footerBar.isInitialized) footerBar.visibility =
            if (imeVisible) View.GONE else View.VISIBLE
        panel.setPadding(dp(17), dp(if (imeVisible) 8 else 12),
            dp(17), dp(if (imeVisible) 8 else 16))
        updateSuggestions()
    }

    private fun updateSuggestions() {
        if (!::suggestionBar.isInitialized) return
        suggestionBar.visibility = if (keyboardVisible || history.isNotEmpty() ||
            pendingQuestion != null || chatInput.text.isNotBlank()) View.GONE else View.VISIBLE
    }

    private fun updateSendButton() {
        if (!::sendButton.isInitialized) return
        val canSend = chatInput.text.isNotBlank() && pendingQuestion == null
        sendButton.alpha = if (canSend) 1f else 0.46f
        sendButton.contentDescription = if (pendingQuestion != null)
            "SKY está procesando un mensaje" else "Enviar mensaje escrito a SKY"
    }

    private fun makeBubble(value: String, mine: Boolean): LinearLayout {
        val item = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            gravity = if (mine) Gravity.END else Gravity.START
            setPadding(dp(4), dp(5), dp(4), dp(5))
        }
        val speaker = text(if (mine) "VOS" else "SKY IA", 10f,
            if (mine) Color.rgb(185, 169, 255) else cyan).apply {
            typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
            letterSpacing = 0.12f
            setPadding(dp(9), dp(2), dp(9), dp(5))
        }
        item.addView(speaker)
        val bubble = text(value, 15f, white).apply {
            gravity = Gravity.START
            setLineSpacing(dp(3).toFloat(), 1f)
            setTextIsSelectable(true)
            background = GradientDrawable(GradientDrawable.Orientation.TL_BR,
                if (mine) intArrayOf(Color.rgb(97, 72, 205), Color.rgb(62, 62, 150))
                else intArrayOf(Color.rgb(36, 52, 92), Color.rgb(32, 42, 76))).apply {
                cornerRadius = dp(20).toFloat()
            }
            setPadding(dp(15), dp(12), dp(15), dp(12))
            setOnLongClickListener {
                val clipboard = host.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText("SKY IA", value))
                Toast.makeText(host, "Mensaje copiado", Toast.LENGTH_SHORT).show()
                true
            }
        }
        item.addView(bubble, LinearLayout.LayoutParams(-2, -2).apply {
            width = LinearLayout.LayoutParams.WRAP_CONTENT
        })
        return item
    }

    private fun addVerifiedSources(exchange: Exchange) {
        if (exchange.sources.isEmpty()) return
        val sourceColumn = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(4), dp(12), dp(8))
        }
        sourceColumn.addView(text("FUENTES CONSULTADAS EN INTERNET", 10f, cyan).apply {
            letterSpacing = 0.07f
            typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
        })
        exchange.sources.forEachIndexed { index, source ->
            val link = text("${index + 1}. ${source.title}", 12f, soft).apply {
                setPadding(dp(3), dp(6), dp(3), dp(5))
                paintFlags = paintFlags or android.graphics.Paint.UNDERLINE_TEXT_FLAG
                isClickable = true
                contentDescription = "Abrir fuente de Internet: " + source.title
                setOnClickListener {
                    runCatching { host.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(source.url))) }
                        .onFailure { Toast.makeText(host, "No se pudo abrir la fuente.", Toast.LENGTH_SHORT).show() }
                }
            }
            sourceColumn.addView(link)
        }
        conversationRows.addView(sourceColumn)
    }

    private fun showGoogleSearchSuggestions(html: String) {
        if (html.isBlank()) return
        // Google requires displaying its original Search Suggestions.
        // Never grant JavaScript or local file access to rendered web markup.
        val view = WebView(host).apply {
            settings.javaScriptEnabled = false
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            setBackgroundColor(Color.TRANSPARENT)
            isVerticalScrollBarEnabled = false
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                    val uri = request?.url ?: return true
                    if (uri.scheme == "https" || uri.scheme == "http") {
                        runCatching { host.startActivity(Intent(Intent.ACTION_VIEW, uri)) }
                    }
                    return true
                }
            }
            loadDataWithBaseURL("https://www.google.com", html, "text/html", "UTF-8", null)
        }
        conversationRows.addView(view, LinearLayout.LayoutParams(-1, dp(68)))
    }

    private fun renderConversation() {
        if (!::conversationRows.isInitialized) return
        conversationRows.removeAllViews()
        // Keep the empty-state view attached after re-rendering the conversation.
        conversationRows.addView(chatOutput)
        chatOutput.visibility = if (history.isEmpty() && pendingQuestion == null &&
            pendingInfo == null) View.VISIBLE else View.GONE
        val entries = if (expandedHistory) history.toList() else history.takeLast(6)
        entries.forEachIndexed { index, exchange ->
            conversationRows.addView(makeBubble(exchange.question, true))
            conversationRows.addView(makeBubble(exchange.answer, false))
            addVerifiedSources(exchange)
            if (index == entries.lastIndex) showGoogleSearchSuggestions(exchange.googleSearchHtml)
        }
        pendingQuestion?.let { question ->
            conversationRows.addView(makeBubble(question, true))
            conversationRows.addView(makeBubble("Un momento, estoy preparando tu respuesta…", false))
        }
        pendingInfo?.let { info -> conversationRows.addView(makeBubble(info, false)) }
        progressLabel.text = when {
            pendingQuestion != null -> "● SKY está pensando…"
            history.isEmpty() -> "● SKY lista para conversar"
            else -> "● Conversación activa · mantené presionado para copiar"
        }
        updateSendButton()
        updateSuggestions()
        conversationScroll.post { conversationScroll.fullScroll(View.FOCUS_DOWN) }
    }

    fun beginSending(message: String) {
        pendingQuestion = message
        pendingInfo = null
        chatInput.setText("")
        renderConversation()
    }

    fun failSending(reason: String, original: String) {
        pendingQuestion = null
        pendingInfo = "No pude enviar el mensaje. $reason"
        if (chatInput.text.isBlank()) chatInput.setText(original)
        renderConversation()
    }

    private fun buildPanel() {
        root.addView(dialogBackdrop, FrameLayout.LayoutParams(-1, -1))
        panelLayout = FrameLayout.LayoutParams(-1, -1, Gravity.BOTTOM).apply {
            topMargin = dp(104)
        }
        dialogBackdrop.addView(panel, panelLayout)
        val header = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(panelTitle, LinearLayout.LayoutParams(0, dp(50), 1f))
        header.addView(pill("Historial", Color.rgb(53, 56, 107)) { toggleHistory() }.apply {
            textSize = 12f
            contentDescription = "Mostrar o reducir historial de conversación"
        }, LinearLayout.LayoutParams(dp(90), dp(40)).apply { rightMargin = dp(8) })
        header.addView(pill("×", Color.rgb(60, 62, 119)) { closePanel() }.apply {
            textSize = 28f
            contentDescription = "Cerrar panel y volver a SKY"
        }, LinearLayout.LayoutParams(dp(47), dp(45)))
        panel.addView(header)
        panel.addView(panelSubtitle)

        conversationRows = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(1), dp(6), dp(1), dp(8))
            addView(chatOutput)
        }
        conversationScroll = ScrollView(host).apply {
            isFillViewport = true
            isVerticalScrollBarEnabled = false
            clipToPadding = false
            addView(conversationRows)
        }
        panel.addView(conversationScroll, LinearLayout.LayoutParams(-1, 0, 1f))
        panel.addView(progressLabel, LinearLayout.LayoutParams(-1, -2))

        val suggestions = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        listOf("¿Qué podés hacer?", "Ayudame a investigar", "Abrí YouTube").forEach { sample ->
            suggestions.addView(pill(sample, Color.rgb(40, 49, 100)) {
                chatInput.setText(sample)
                chatInput.setSelection(chatInput.text.length)
                chatInput.requestFocus()
                (host.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager)
                    .showSoftInput(chatInput, InputMethodManager.SHOW_IMPLICIT)
            }.apply {
                textSize = 12f
                setTextColor(Color.rgb(223, 227, 252))
            }, LinearLayout.LayoutParams(-2, -2).apply { rightMargin = dp(8) })
        }
        suggestionBar = HorizontalScrollView(host).apply {
            isHorizontalScrollBarEnabled = false
            setPadding(0, dp(4), 0, dp(9))
            addView(suggestions)
        }
        panel.addView(suggestionBar, LinearLayout.LayoutParams(-1, -2))

        val composer = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.BOTTOM
            background = GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT,
                intArrayOf(Color.rgb(44, 52, 100), Color.rgb(59, 56, 116))).apply {
                cornerRadius = dp(23).toFloat()
                setStroke(dp(1), Color.rgb(96, 102, 161))
            }
            setPadding(dp(2), dp(3), dp(4), dp(3))
        }
        composer.addView(chatInput, LinearLayout.LayoutParams(0, -2, 1f))
        sendButton = pill("➤", violet) {
            if (chatInput.text.isNotBlank() && pendingQuestion == null) onSend()
        }.apply {
            textSize = 23f
            contentDescription = "Enviar mensaje escrito a SKY"
            elevation = dp(3).toFloat()
        }
        composer.addView(sendButton, LinearLayout.LayoutParams(dp(52), dp(50)))
        panel.addView(composer, LinearLayout.LayoutParams(-1, -2))
        footerBar = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        footerBar.addView(pill("🎙", Color.TRANSPARENT) { voicePanel.listen() }.apply {
            contentDescription = "Dictar mensaje a SKY"
        }, LinearLayout.LayoutParams(0, dp(44), 1f))
        footerBar.addView(pill("Privacidad", Color.TRANSPARENT) {
            privacy.visibility = if (privacy.visibility == View.GONE) View.VISIBLE else View.GONE
        }, LinearLayout.LayoutParams(0, dp(44), 1f))
        footerBar.addView(pill("Motor", Color.TRANSPARENT, onDiagnostics),
            LinearLayout.LayoutParams(0, dp(44), 1f))
        footerBar.addView(pill("Acceso", Color.TRANSPARENT, onChatAccess),
            LinearLayout.LayoutParams(0, dp(44), 1f))
        panel.addView(footerBar)
        panel.addView(privacy)
        updateSendButton()
        updateSuggestions()
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
        pendingInfo = "¿Qué necesitás hacer en " + moduleTitle(id) + "? Puedo conversar " +
            "sobre esta tarea; algunas acciones requieren permisos del dispositivo."
        renderConversation()
        dialogBackdrop.visibility = View.VISIBLE
    }

    fun closePanel() {
        dialogBackdrop.visibility = View.GONE
        privacy.visibility = View.GONE
        chatInput.clearFocus()
        (host.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager)
            ?.hideSoftInputFromWindow(chatInput.windowToken, 0)
    }

    private fun toggleHistory() {
        expandedHistory = !expandedHistory
        renderConversation()
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
        if (isPanelOpen()) {
            pendingInfo = s
            renderConversation()
        } else {
            Toast.makeText(host, s, Toast.LENGTH_SHORT).show()
        }
    }

    fun addExchange(
        question: String,
        answer: String,
        engine: String,
        revealPanel: Boolean = true,
        sources: List<SkyPhoneCloud.Source> = emptyList(),
        googleSearchHtml: String = ""
    ) {
        pendingQuestion = null
        pendingInfo = null
        history.add(Exchange(question.take(4000), answer.take(4000), engine,
            sources, googleSearchHtml))
        if (history.size > 30) history.removeAt(0)
        renderConversation()
        if (revealPanel && !isPanelOpen()) openChat()
    }
}
