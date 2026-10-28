package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * Contextual replies only for contacts whose names the user explicitly approves.
 * No READ_CONTACTS, notification interception, automated sends or auto-cloud upload.
 */
class SkyReplyStudio(
    private val host: Activity,
    private val prefs: SharedPreferences,
    private val feedback: (String) -> Unit
) {
    private val key = "reply_allowed_names"
    private fun dp(i: Int) = (host.resources.displayMetrics.density * i + .5f).toInt()

    fun isApproved(name: String): Boolean =
        prefs.getStringSet(key, emptySet()).orEmpty().any {
            SkyContextReply.normalizedName(it) == SkyContextReply.normalizedName(name)
        }

    fun showSettings(onCreate: (SkyContextReply.Request) -> Unit) {
        val wrap = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(8), dp(18), dp(8))
        }
        val approved = prefs.getStringSet(key, emptySet()).orEmpty().toList().sorted()
        wrap.addView(TextView(host).apply {
            text = "Contactos habilitados manualmente: " +
                if (approved.isEmpty()) "ninguno" else approved.joinToString(", ")
            textSize = 14f
        })
        val name = EditText(host).apply {
            hint = "Nombre exacto del contacto (sin números)"
            setSingleLine(true)
            maxLengthCompat(100)
        }
        wrap.addView(name)
        val incoming = EditText(host).apply {
            hint = "Pegá el mensaje recibido que querés responder"
            minLines = 3
            maxLines = 5
            maxLengthCompat(1200)
        }
        wrap.addView(incoming)
        val consent = CheckBox(host).apply {
            text = "Autorizo compartir con Gemini solo este mensaje y nombre para crear el borrador."
        }
        wrap.addView(consent)
        val scroller = ScrollView(host).apply { addView(wrap) }
        AlertDialog.Builder(host)
            .setTitle("SKY · Respuestas con contexto")
            .setView(scroller)
            .setPositiveButton("Preparar respuesta") { _, _ ->
                val contact = name.text.toString().trim()
                val fragment = incoming.text.toString().trim()
                if (contact.length !in 2..100 || fragment.length !in 2..1200) {
                    feedback("Ingresá un contacto y el mensaje que querés responder.")
                } else if (!isApproved(contact)) {
                    feedback("Primero habilitá ese contacto desde la opción «Autorizar contacto».")
                } else if (!consent.isChecked) {
                    feedback("Autorizá el envío de este fragmento a Gemini antes de generar.")
                } else {
                    onCreate(SkyContextReply.Request(contact, fragment))
                }
            }
            .setNeutralButton("Autorizar contacto") { _, _ ->
                val contact = name.text.toString().trim()
                if (contact.length !in 2..100 || contact.any { it == '\n' || it == '@' }) {
                    feedback("Escribí un nombre de 2 a 100 letras para habilitarlo.")
                } else {
                    val current = prefs.getStringSet(key, emptySet()).orEmpty().toMutableSet()
                    if (current.size >= 20 && !isApproved(contact)) {
                        feedback("Límite de 20 contactos habilitados. Revisá o borrá la lista.")
                    } else {
                        current.add(contact)
                        prefs.edit().putStringSet(key, current).apply()
                        feedback("Contacto «" + contact + "» habilitado. " +
                            "SKY no puede leer mensajes ni responder automáticamente desde WhatsApp.")
                    }
                }
            }
            .setNegativeButton("Cerrar", null)
            .show()
    }

    fun manageContacts() {
        val names = prefs.getStringSet(key, emptySet()).orEmpty().toList().sorted()
        if (names.isEmpty()) {
            feedback("No hay contactos autorizados.")
            return
        }
        AlertDialog.Builder(host)
            .setTitle("SKY · Contactos autorizados")
            .setItems(names.toTypedArray()) { _, idx ->
                AlertDialog.Builder(host)
                    .setTitle("Quitar autorización")
                    .setMessage("¿Dejar de preparar respuestas para «" + names[idx] + "»?")
                    .setPositiveButton("Quitar") { _, _ ->
                        val saved = prefs.getStringSet(key, emptySet()).orEmpty().toMutableSet()
                        saved.remove(names[idx])
                        prefs.edit().putStringSet(key, saved).apply()
                        feedback("Autorización retirada.")
                    }
                    .setNegativeButton("Cancelar", null).show()
            }
            .setNegativeButton("Cerrar", null).show()
    }

    fun preview(request: SkyContextReply.Request, body: String) {
        val editor = EditText(host).apply {
            setText(body.take(1000))
            minLines = 5
            maxLines = 12
            setPadding(dp(20), dp(20), dp(20), dp(20))
            contentDescription = "Borrador editable de respuesta a contacto autorizado"
        }
        AlertDialog.Builder(host)
            .setTitle("Respuesta para " + request.contact)
            .setMessage("Revisá el texto. SKY no conoce ni confirma la identidad del chat: " +
                "seleccioná el contacto correcto antes de pulsar Enviar.")
            .setView(editor)
            .setPositiveButton("Abrir WhatsApp") { _, _ ->
                try {
                    val intent = Intent(Intent.ACTION_SEND).apply {
                        type = "text/plain"
                        setPackage("com.whatsapp")
                        putExtra(Intent.EXTRA_TEXT, editor.text.toString().take(1000))
                    }
                    host.startActivity(intent)
                    feedback("Abrí WhatsApp con el borrador. Elegí el chat correcto y enviá si querés.")
                } catch (_: Exception) {
                    feedback("No pude abrir WhatsApp. Usá la opción Copiar texto.")
                }
            }
            .setNeutralButton("Copiar texto") { _, _ ->
                val clip = host.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clip.setPrimaryClip(ClipData.newPlainText(
                    "Respuesta SKY", editor.text.toString().take(1000)))
                feedback("Borrador copiado. Podés pegarlo en el chat elegido.")
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun EditText.maxLengthCompat(length: Int) {
        filters = arrayOf(android.text.InputFilter.LengthFilter(length))
    }
}
