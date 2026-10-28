package ni.sky.mobileagent

import android.accessibilityservice.AccessibilityService
import android.os.Bundle
import android.os.SystemClock
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Toast

/**
 * Escritura asistida estrictamente dirigida por la persona propietaria.
 * Se habilita MANUALMENTE en Ajustes de Android después de una explicación.
 * No extrae mensajes, no explora ventanas, no pulsa "Enviar", no inicia
 * planes autónomos y no registra el contenido del texto.
 *
 * El usuario debe enfocar una caja de texto VACÍA de WhatsApp o Gmail en
 * menos de 45 segundos tras aprobar una solicitud en SKY.
 */
class SkyTextAssistService : AccessibilityService() {
    private data class Pending(val pkg: String, val text: String, val deadline: Long)

    companion object {
        @Volatile private var instance: SkyTextAssistService? = null
        @Volatile private var pending: Pending? = null
        private const val MAX_LENGTH = 1000
        private const val TIMEOUT_MS = 45000L
        private val ALLOWED = setOf("com.whatsapp", "com.google.android.gm")

        fun enabled(): Boolean = instance != null

        @Synchronized fun arm(pkg: String, text: String): Boolean {
            if (instance == null || pkg !in ALLOWED || text.isBlank() || text.length > MAX_LENGTH) {
                return false
            }
            pending = Pending(pkg, text, SystemClock.elapsedRealtime() + TIMEOUT_MS)
            return true
        }

        @Synchronized fun cancelPending() {
            pending = null
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val current = pending ?: return
        if (SystemClock.elapsedRealtime() > current.deadline) {
            cancelPending()
            return
        }
        if (event?.eventType != AccessibilityEvent.TYPE_VIEW_FOCUSED ||
            event.packageName?.toString() != current.pkg) return

        val source = event.source ?: return
        try {
            // Nunca escribir en contraseñas, campos con texto previo, ni UI ajena.
            if (!source.isEditable || !source.isFocused || source.isPassword ||
                !source.text.isNullOrEmpty()) return

            val args = Bundle().apply {
                putCharSequence(
                    AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                    current.text
                )
            }
            // Consumir antes de escribir evita duplicados por eventos concurrentes.
            synchronized(Companion) {
                if (pending !== current) return
                pending = null
            }
            val accepted = source.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
            // Un true indica que Android aceptó la acción, no garantiza envío.
            Toast.makeText(applicationContext,
                if (accepted) "SKY escribió el texto solicitado. Revisá antes de enviar."
                else "SKY no pudo escribir en ese campo.",
                Toast.LENGTH_LONG).show()
        } finally {
            source.recycle()
        }
    }

    override fun onInterrupt() {
        cancelPending()
    }

    override fun onDestroy() {
        cancelPending()
        instance = null
        super.onDestroy()
    }

    override fun onUnbind(intent: android.content.Intent?): Boolean {
        cancelPending()
        instance = null
        return super.onUnbind(intent)
    }
}
