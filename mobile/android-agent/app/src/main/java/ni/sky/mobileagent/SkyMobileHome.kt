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
    private val onNewChat: () -> Unit,
    private val onSettings: () -> Unit,
    private val onChatAccess: () -> Unit,
    private val onAttach: () -> Unit,
    private val onRemoveAttachment: () -> Unit,
    private val onCancelUpload: () -> Unit,
    private val onHistory: () -> Unit,
    private val onTeach: () -> Unit,
    private val archive: SkyConversationArchive,
    private val onDiagnostics: () -> Unit,
    private val onStopHandsFree: () -> Unit
) {
    private val white = Color.WHITE
    private val soft = Color.rgb(202, 208, 233)
    private val cyan = Color.rgb(132, 215, 245)
    private val violet = Color.rgb(125, 98, 245)
    private lateinit var mainSurface: LinearLayout
    private var handsFreeActive = false
    private val faceCaption = text("SKY LISTA · TOCÁ LOS OJOS O ACTIVÁ MANOS LIBRES", 12f, Color.rgb(207, 200, 252)).apply {
        gravity = Gravity.CENTER
        letterSpacing = 0.07f
        contentDescription = "Estado actual de SKY"
    }
    private data class Exchange(
        val question: String,
        val answer: String,
        val engine: String,
        val sources: List<SkyPhoneCloud.Source>,
        val googleSearchHtml: String,
        val title: String = SkyConversationArchive.titleFor(question),
        val dateLabel: String = ""
    )
    private var sessionAfterId = host.getSharedPreferences(
        "sky_chat_session", Context.MODE_PRIVATE).getLong("after_id", 0L)
    private val history = ArrayList<Exchange>().apply {
        archive.recent(150).filter { SkyChatSessionPolicy.visible(it.id, sessionAfterId) }.forEach { saved ->
            add(Exchange(saved.question, saved.answer, saved.engine,
                emptyList(), "", saved.title, saved.localTime()))
        }
    }
    private var activeModule = ""
    private var expandedHistory = false
    private var keyboardVisible = false
    private var pendingQuestion: String? = null
    private var pendingInfo: String? = null
    private var noticeRevision = 0

    private fun clearTransientNotice() {
        noticeRevision++
        pendingInfo = null
    }

    /** Transient notices never linger after another request or panel dismissal. */
    private fun showTransientNotice(info: String) {
        clearTransientNotice()
        pendingInfo = info
        val revision = noticeRevision
        if (::conversationRows.isInitialized) {
            conversationRows.postDelayed({
                if (revision == noticeRevision && pendingQuestion == null) {
                    clearTransientNotice()
                    renderConversation()
                }
            }, 8000L)
        }
    }
    private lateinit var conversationScroll: ScrollView
    private lateinit var conversationRows: LinearLayout
    private lateinit var footerBar: LinearLayout
    private lateinit var suggestionBar: HorizontalScrollView
    private lateinit var sendButton: TextView
    private var uploadingFiles = false
    private val cancelUploadButton = pill("Cancelar carga de archivos", Color.rgb(106, 48, 80)) {
        onCancelUpload()
    }.apply {
        visibility = View.GONE
        contentDescription = "Cancelar el envío de archivos a Gemini"
    }
    private val attachmentLabel = text("", 12f, cyan).apply {
        visibility = View.GONE
        setPadding(dp(12), dp(6), dp(12), dp(6))
        contentDescription = "Archivo adjunto. Tocar para quitar de la consulta."
        isClickable = true
        setOnClickListener { onRemoveAttachment() }
    }
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
        // Reject oversized prompts explicitly on Send. InputFilter would
        // silently truncate pasted instructions, which is unsafe for long tasks.
        filters = emptyArray()
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
        actions.addView(pill("■", Color.rgb(42, 43, 95)) {
            if (handsFreeActive) onStopHandsFree() else voicePanel.stop()
        }.apply {
            textSize = 18f
            contentDescription = "Detener escucha manos libres y voz"
        }, LinearLayout.LayoutParams(dp(56), dp(56)))
        main.addView(actions)
        buildPanel()
    }

    fun setHandsFreeActive(enabled: Boolean) {
        handsFreeActive = enabled
        voicePanel.setHandsFreeActive(enabled)
        faceCaption.text = if (enabled) "SKY DURMIENDO · DECÍ SKY" else
            "SKY LISTA · TOCÁ LOS OJOS O ACTIVÁ MANOS LIBRES"
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
        val canSend = (chatInput.text.isNotBlank() ||
            attachmentLabel.visibility == View.VISIBLE) && pendingQuestion == null
        sendButton.alpha = if (canSend) 1f else 0.46f
        sendButton.contentDescription = if (pendingQuestion != null)
            "SKY está procesando un mensaje" else "Enviar mensaje escrito a SKY"
    }

    /**
     * Long scientific answers can exceed Android's single-view height limit.
     * Open them in their own scrollable, offline viewer instead of truncating.
     */
    /** Accessible full-screen offline reader; the original text is never truncated. */
    private fun openFullResponse(answer: String) {
        val viewer = WebView(host).apply {
            settings.javaScriptEnabled = false
            settings.domStorageEnabled = false
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.blockNetworkLoads = true
            isVerticalScrollBarEnabled = true
            setBackgroundColor(Color.rgb(14, 26, 52))
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(
                    view: WebView?, request: WebResourceRequest?
                ) = true
            }
        }
        val container = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            background = bg(Color.rgb(13, 23, 51), 22)
            setPadding(dp(12), dp(14), dp(12), dp(10))
        }
        container.addView(text("SKY IA · LECTURA COMPLETA", 18f, white).apply {
            typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
            setPadding(dp(4), dp(3), dp(4), dp(4))
        })
        container.addView(text(
            "Contenido íntegro · ${answer.length} caracteres · Deslizá para leer",
            12f, soft).apply { setPadding(dp(4), dp(2), dp(4), dp(11)) })
        container.addView(viewer, LinearLayout.LayoutParams(-1, 0, 1f))
        val actions = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(12), 0, 0)
        }
        val dialog = android.app.AlertDialog.Builder(host).setView(container).create()
        actions.addView(pill("Copiar todo", Color.rgb(36, 83, 116)) {
            copyMessage(answer)
        }.apply { textSize = 13f }, LinearLayout.LayoutParams(0, dp(49), 1f).apply {
            rightMargin = dp(8)
        })
        actions.addView(pill("Cerrar", Color.rgb(92, 72, 169)) {
            dialog.dismiss()
        }.apply { textSize = 13f }, LinearLayout.LayoutParams(0, dp(49), 1f))
        container.addView(actions)
        dialog.setOnDismissListener {
            container.removeView(viewer)
            viewer.stopLoading()
            viewer.destroy()
        }
        SkyPremiumUi.showDialog(host, dialog, 0.94)
        viewer.loadDataWithBaseURL(null, SkyScientificMarkup.toHtml(answer),
            "text/html", "UTF-8", null)
    }

    private fun copyMessage(value: String) {
        val clipboard = host.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("SKY IA", value))
        Toast.makeText(host, "Texto copiado", Toast.LENGTH_SHORT).show()
    }

    /**
     * Native, selectable text: no clipped 56dp WebViews nor late height probes.
     * Complex MathML, tables and large documents use the dedicated offline reader.
     */
    private fun makeBubble(value: String, mine: Boolean): LinearLayout {
        val item = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            gravity = if (mine) Gravity.END else Gravity.START
            setPadding(dp(2), dp(7), dp(2), dp(10))
        }
        item.addView(text(if (mine) "VOS" else "SKY IA", 11f,
            if (mine) Color.rgb(192, 180, 255) else cyan).apply {
            typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
            letterSpacing = 0.08f
            setPadding(dp(11), dp(2), dp(9), dp(7))
        })
        val preview = SkyReadableAnswer.preview(value, mine)
        val bubble = text("", if (mine) 15f else 15.5f, white).apply {
            text = if (mine) preview.text else SkyReadableAnswer.styled(preview.text)
            gravity = Gravity.START
            includeFontPadding = true
            setLineSpacing(dp(4).toFloat(), 1.1f)
            setTextIsSelectable(true)
            setPadding(dp(16), dp(14), dp(16), dp(15))
            background = GradientDrawable(GradientDrawable.Orientation.TL_BR,
                if (mine) intArrayOf(Color.rgb(79, 62, 162), Color.rgb(56, 56, 120))
                else intArrayOf(Color.rgb(30, 46, 82), Color.rgb(22, 38, 69))).apply {
                cornerRadius = dp(18).toFloat()
                setStroke(dp(1), if (mine) Color.rgb(111, 100, 187)
                    else Color.rgb(66, 91, 127))
            }
            setOnLongClickListener {
                copyMessage(value)
                true
            }
        }
        item.addView(bubble, LinearLayout.LayoutParams(
            if (mine) LinearLayout.LayoutParams.WRAP_CONTENT
                else LinearLayout.LayoutParams.MATCH_PARENT, -2))
        if (preview.needsReader) {
            item.addView(text(
                "Vista previa · ${preview.totalChars} caracteres en total",
                11f, soft).apply { setPadding(dp(12), dp(9), dp(12), dp(3)) })
        }
        if (preview.needsReader || preview.rich) {
            val controls = LinearLayout(host).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            controls.addView(pill(
                if (preview.needsReader) "Leer completo" else "Ver formato",
                Color.rgb(39, 88, 125)) { openFullResponse(value) }.apply {
                textSize = 13f
                contentDescription = "Abrir texto íntegro con fórmulas, tablas y código"
            }, LinearLayout.LayoutParams(0, dp(43), 1f).apply {
                rightMargin = dp(8)
            })
            controls.addView(pill("Copiar", Color.rgb(48, 56, 105)) {
                copyMessage(value)
            }.apply { textSize = 13f },
                LinearLayout.LayoutParams(dp(95), dp(43)))
            item.addView(controls, LinearLayout.LayoutParams(-1, -2).apply {
                topMargin = dp(8)
            })
        }
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

    private fun renderConversation(autoScrollToEnd: Boolean = false) {
        if (!::conversationRows.isInitialized) return
        // WebViews must be detached and explicitly destroyed on redraw.
        // Otherwise every new question leaves an obsolete Chromium instance.
        val outdated = mutableListOf<WebView>()
        fun collect(view: View) {
            if (view is WebView) outdated.add(view)
            else if (view is android.view.ViewGroup) {
                for (index in 0 until view.childCount) collect(view.getChildAt(index))
            }
        }
        for (index in 0 until conversationRows.childCount) collect(conversationRows.getChildAt(index))
        conversationRows.removeAllViews()
        outdated.forEach { it.stopLoading(); it.destroy() }
        // Keep the empty-state view attached after re-rendering the conversation.
        conversationRows.addView(chatOutput)
        chatOutput.visibility = if (history.isEmpty() && pendingQuestion == null &&
            pendingInfo == null) View.VISIBLE else View.GONE
        val entries = if (expandedHistory) history.toList() else history.takeLast(6)
        entries.forEachIndexed { index, exchange ->
            conversationRows.addView(text(
                exchange.title + if (exchange.dateLabel.isNotBlank()) " · " + exchange.dateLabel else "",
                11f, cyan
            ).apply { setPadding(dp(10), dp(14), dp(7), dp(3)) })
            conversationRows.addView(makeBubble(exchange.question, true))
            conversationRows.addView(makeBubble(exchange.answer, false))
            addVerifiedSources(exchange)
            if (index == entries.lastIndex) showGoogleSearchSuggestions(exchange.googleSearchHtml)
        }
        pendingQuestion?.let { question ->
            conversationRows.addView(makeBubble(question, true))
            conversationRows.addView(makeBubble("Un momento, estoy preparando tu respuesta…", false))
        }
        pendingInfo?.let { info ->
            val notice = LinearLayout(host).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                background = bg(Color.rgb(47, 52, 90), 16)
                setPadding(dp(12), dp(10), dp(8), dp(10))
            }
            notice.addView(text(info, 13f, soft).apply {
                setLineSpacing(dp(2).toFloat(), 1f)
            }, LinearLayout.LayoutParams(0, -2, 1f))
            notice.addView(pill("×", Color.rgb(77, 77, 119)) {
                clearTransientNotice()
                renderConversation()
            }.apply { contentDescription = "Descartar aviso temporal de SKY" },
                LinearLayout.LayoutParams(dp(42), dp(42)).apply {
                    leftMargin = dp(8)
                })
            conversationRows.addView(notice)
        }
        progressLabel.text = when {
            pendingQuestion != null -> "● SKY está pensando…"
            history.isEmpty() -> "● SKY lista para conversar"
            else -> "● Conversación activa · mantené presionado para copiar"
        }
        updateSendButton()
        updateSuggestions()
        if (autoScrollToEnd) {
            conversationScroll.post {
                if (conversationScroll.isAttachedToWindow)
                    conversationScroll.fullScroll(View.FOCUS_DOWN)
            }
        }
    }

    fun beginSending(message: String) {
        clearTransientNotice()
        pendingQuestion = message
        chatInput.setText("")
        renderConversation(autoScrollToEnd = true)
    }

    fun failSending(reason: String, original: String) {
        pendingQuestion = null
        showTransientNotice("No pude enviar el mensaje. $reason")
        if (chatInput.text.isBlank()) chatInput.setText(original)
        renderConversation(autoScrollToEnd = true)
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
        header.addView(pill("×", Color.rgb(60, 62, 119)) { closePanel() }.apply {
            textSize = 28f
            contentDescription = "Cerrar panel y volver a SKY"
        }, LinearLayout.LayoutParams(dp(47), dp(45)))
        panel.addView(header)
        val chatToolbar = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.END or Gravity.CENTER_VERTICAL
            setPadding(0, dp(2), 0, dp(5))
        }
        chatToolbar.addView(pill("＋ Nuevo chat", Color.rgb(47, 107, 146), onNewChat).apply {
            textSize = 12f
            contentDescription = "Iniciar un nuevo chat sin borrar las conversaciones guardadas"
        }, LinearLayout.LayoutParams(dp(126), dp(40)).apply { rightMargin = dp(8) })
        chatToolbar.addView(pill("Enseñar", Color.rgb(54, 81, 133), onTeach).apply {
            textSize = 12f
            contentDescription = "Corregir y enseñarle una respuesta a SKY"
        }, LinearLayout.LayoutParams(dp(85), dp(40)))
        panel.addView(chatToolbar)
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
        panel.addView(cancelUploadButton, LinearLayout.LayoutParams(-1, dp(42)))

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
        composer.addView(pill("＋", Color.rgb(49, 64, 117), onAttach).apply {
            textSize = 24f
            contentDescription = "Adjuntar archivo para analizar con SKY"
        }, LinearLayout.LayoutParams(dp(46), dp(50)))
        composer.addView(chatInput, LinearLayout.LayoutParams(0, -2, 1f))
        sendButton = pill("➤", violet) {
            if ((chatInput.text.isNotBlank() || attachmentLabel.visibility == View.VISIBLE) &&
                pendingQuestion == null) onSend()
        }.apply {
            textSize = 23f
            contentDescription = "Enviar mensaje escrito a SKY"
            elevation = dp(3).toFloat()
        }
        composer.addView(sendButton, LinearLayout.LayoutParams(dp(52), dp(50)))
        panel.addView(attachmentLabel, LinearLayout.LayoutParams(-1, -2))
        panel.addView(composer, LinearLayout.LayoutParams(-1, -2))
        // Privacidad, Motor, Acceso, Enseñar e Historial viven en Configuración.
        // Los permisos para la siguiente consulta permanecen en los CheckBox
        // originales, solo se presentan desde Ajustes.
        updateSendButton()
        updateSuggestions()
        // Volver a dibujar las consultas restauradas al crear la pantalla.
        renderConversation()
    }

    fun setAttachmentLabel(filename: String?) {
        attachmentLabel.text = if (filename.isNullOrBlank()) "" else
            "Adjuntos: " + filename.take(135) + " · TOCÁ PARA GESTIONAR"
        attachmentLabel.visibility = if (filename.isNullOrBlank()) View.GONE else View.VISIBLE
        updateSendButton()
    }

    fun showUploadProgress(progress: String?) {
        uploadingFiles = progress != null
        cancelUploadButton.visibility = if (uploadingFiles) View.VISIBLE else View.GONE
        if (progress != null) progressLabel.text = "● " + progress.take(130)
        else renderConversation()
    }

    fun clearHistory() {
        archive.deleteAll()
        history.clear()
        expandedHistory = false
        renderConversation()
    }

    /** New chat clears only the active screen and draft. SQLite history survives. */
    fun startNewChat(afterId: Long) {
        sessionAfterId = afterId.coerceAtLeast(0L)
        history.clear()
        pendingQuestion = null
        clearTransientNotice()
        expandedHistory = false
        activeModule = ""
        chatInput.setText("")
        panelTitle.text = "Conversación nueva"
        panelSubtitle.visibility = View.GONE
        renderConversation()
        dialogBackdrop.visibility = View.VISIBLE
    }

    /** Abrir una consulta histórica sin volver a guardarla ni perder su texto. */
    fun openSavedExchange(entry: SkyConversationArchive.Entry) {
        history.clear()
        history.add(Exchange(entry.question, entry.answer, entry.engine,
            emptyList(), "", entry.title, entry.localTime()))
        expandedHistory = true
        openChat()
        renderConversation()
        conversationScroll.post { conversationScroll.scrollTo(0, 0) }
    }

    /** Recargar historial tras editar, borrar o renombrar; no toca la base. */
    fun reloadHistory() {
        history.clear()
        archive.recent(150).filter { SkyChatSessionPolicy.visible(it.id, sessionAfterId) }.forEach { entry ->
            history.add(Exchange(entry.question, entry.answer, entry.engine,
                emptyList(), "", entry.title, entry.localTime()))
        }
        renderConversation()
    }

    fun isPanelOpen() = dialogBackdrop.visibility == View.VISIBLE

    fun openChat() {
        if (pendingQuestion == null && pendingInfo != null) {
            clearTransientNotice()
            renderConversation()
        }
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
        showTransientNotice("¿Qué necesitás hacer en " + moduleTitle(id) +
            "? Algunas acciones requieren permisos del dispositivo.")
        renderConversation()
        dialogBackdrop.visibility = View.VISIBLE
    }

    fun closePanel() {
        clearTransientNotice()
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
            showTransientNotice(s)
            renderConversation(autoScrollToEnd = true)
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
        clearTransientNotice()
        // Persistir solamente consultas completadas, en el almacenamiento privado.
        val saved = archive.append(question, answer, engine)
        history.add(Exchange(saved.question, saved.answer, saved.engine,
            sources, googleSearchHtml, saved.title, saved.localTime()))
        if (history.size > 150) history.removeAt(0)
        renderConversation(autoScrollToEnd = true)
        if (revealPanel && !isPanelOpen()) openChat()
    }
}
