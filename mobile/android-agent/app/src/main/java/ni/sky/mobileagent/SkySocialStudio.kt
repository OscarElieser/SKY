package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.view.Gravity
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.ArrayAdapter
import android.widget.TextView

/**
 * SKY Creator Studio. Every generation is user initiated.
 * Publishing/authentication stays inside the official social applications.
 */
class SkySocialStudio(
    private val host: Activity,
    private val feedback: (String) -> Unit
) {
    private fun dp(value: Int) =
        (value * host.resources.displayMetrics.density + 0.5f).toInt()

    fun showCreatorMenu(onGenerate: (SkySocialCommand.Request) -> Unit) {
        val content = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(21), dp(12), dp(21), dp(12))
        }
        val help = TextView(host).apply {
            text = "SKY prepara ideas, guiones, descripciones y planes para crecer " +
                "de manera orgánica. No tenés que mostrar tu rostro. " +
                "La publicación final la autorizás vos."
            textSize = 15f
        }
        content.addView(help)
        content.addView(TextView(host).apply {
            text = "Elegí una red social"
            textSize = 15f
            setPadding(0, dp(13), 0, dp(4))
        })
        val platform = Spinner(host)
        platform.adapter = ArrayAdapter(host,
            android.R.layout.simple_spinner_dropdown_item, SkySocialCommand.platforms)
        content.addView(platform)
        val topic = EditText(host).apply {
            hint = "¿Sobre qué querés publicar? Ej.: rincones de Nicaragua"
            minLines = 2
            maxLines = 4
        }
        content.addView(topic)
        val faceless = CheckBox(host).apply {
            text = "Sin mostrar mi rostro (recomendado)"
            isChecked = true
        }
        content.addView(faceless)
        val scroll = ScrollView(host).apply { addView(content) }
        fun getRequest(kind: SkySocialCommand.Kind): SkySocialCommand.Request? {
            val value = topic.text.toString().trim()
            if (value.isBlank()) {
                feedback("Decime un tema para que SKY prepare contenido original.")
                return null
            }
            return SkySocialCommand.Request(
                platform.selectedItem.toString(), value.take(220), kind, faceless.isChecked
            )
        }
        AlertDialog.Builder(host)
            .setTitle("SKY · Estudio Creativo")
            .setView(scroll)
            .setPositiveButton("Crear publicación") { _, _ ->
                getRequest(SkySocialCommand.Kind.POST)?.let(onGenerate)
            }
            .setNeutralButton("Plan de 7 días") { _, _ ->
                getRequest(SkySocialCommand.Kind.WEEKLY_PLAN)?.let(onGenerate)
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    fun showPreview(request: SkySocialCommand.Request, generated: String) {
        val editor = EditText(host).apply {
            setText(generated.take(5000))
            textSize = 15f
            minLines = 8
            maxLines = 22
            gravity = Gravity.TOP
            setHorizontallyScrolling(false)
            contentDescription = "Guion y descripción creados por SKY, editables"
        }
        val container = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(10), dp(20), dp(8))
        }
        container.addView(TextView(host).apply {
            text = "Revisá el borrador antes de compartir. Puede requerir video, " +
                "fotos o audio que vos agregás dentro de " + request.platform + ". " +
                "SKY no publica automáticamente ni garantiza viralidad."
            textSize = 13f
        })
        container.addView(editor, LinearLayout.LayoutParams(-1,
            (host.resources.displayMetrics.heightPixels * 0.50f).toInt()))
        val scroll = ScrollView(host).apply { addView(container) }
        AlertDialog.Builder(host)
            .setTitle("SKY · Borrador para " + request.platform)
            .setView(scroll)
            .setPositiveButton("Compartir texto") { _, _ ->
                val send = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, editor.text.toString().take(5000))
                }
                try {
                    host.startActivity(Intent.createChooser(send, "Elegí dónde compartir"))
                    feedback("Abrí el menú para compartir. " +
                        "Revisá y confirmá la publicación dentro de la red social.")
                } catch (_: Exception) {
                    feedback("Android no encontró una aplicación compatible. " +
                        "Usá «Copiar texto» y pegalo manualmente en la red elegida.")
                }
            }
            .setNeutralButton("Copiar texto") { _, _ ->
                val clipboard = host.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText(
                    "Borrador SKY · " + request.platform, editor.text.toString().take(5000)))
                feedback("Borrador copiado. Pegalo donde vayas a publicar y revisalo primero.")
            }
            .setNegativeButton("Cerrar", null)
            .show()
    }
}
