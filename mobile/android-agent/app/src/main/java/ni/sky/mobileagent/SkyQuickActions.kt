package ni.sky.mobileagent

import android.app.Activity
import android.app.KeyguardManager
import android.content.Context
import android.media.AudioManager
import android.os.Build
import android.view.KeyEvent

/**
 * Foreground, user-initiated controls. These use Android media keys and
 * system volume; no surveillance of other app contents is necessary.
 *
 * A request to unlock never removes PIN/biometric authentication.
 */
class SkyQuickActions(
    private val host: Activity,
    private val feedback: (String) -> Unit
) {
    var onReceipt: ((String, String, String) -> Unit)? = null
    private fun receipt(action: SkyQuickCommand.Action, state: String, detail: String) {
        onReceipt?.invoke("Control Android " + action.name, state, detail)
    }

    private val audio: AudioManager
        get() = host.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    fun execute(action: SkyQuickCommand.Action) {
        if (action == SkyQuickCommand.Action.REQUEST_UNLOCK) {
            requestUnlock()
            return
        }
        try {
            when (action) {
                SkyQuickCommand.Action.VOLUME_UP,
                SkyQuickCommand.Action.VOLUME_DOWN -> {
                    if (audio.isVolumeFixed) {
                        receipt(action, "REJECTED", "El dispositivo informa volumen fijo")
                        feedback("El volumen es fijo en este dispositivo.")
                        return
                    }
                    val direction = if (action == SkyQuickCommand.Action.VOLUME_UP)
                        AudioManager.ADJUST_RAISE else AudioManager.ADJUST_LOWER
                    val before = audio.getStreamVolume(AudioManager.STREAM_MUSIC)
                    audio.adjustStreamVolume(AudioManager.STREAM_MUSIC,
                        direction, AudioManager.FLAG_SHOW_UI)
                    val after = audio.getStreamVolume(AudioManager.STREAM_MUSIC)
                    receipt(action, if (after != before) "VERIFIED_LOCAL" else "REJECTED",
                        "Volumen multimedia observado antes=$before, despues=$after")
                    feedback(if (after != before) {
                        if (action == SkyQuickCommand.Action.VOLUME_UP)
                            "Subí un nivel el volumen multimedia."
                        else "Bajé un nivel el volumen multimedia."
                    } else "El volumen no cambió; revisá el límite del dispositivo.")
                }

                else -> {
                    val keyCode = when (action) {
                        SkyQuickCommand.Action.NEXT -> KeyEvent.KEYCODE_MEDIA_NEXT
                        SkyQuickCommand.Action.PREVIOUS -> KeyEvent.KEYCODE_MEDIA_PREVIOUS
                        SkyQuickCommand.Action.RESTART -> KeyEvent.KEYCODE_MEDIA_PREVIOUS
                        SkyQuickCommand.Action.PAUSE -> KeyEvent.KEYCODE_MEDIA_PAUSE
                        SkyQuickCommand.Action.PLAY -> KeyEvent.KEYCODE_MEDIA_PLAY
                        else -> return
                    }
                    val time = android.os.SystemClock.uptimeMillis()
                    audio.dispatchMediaKeyEvent(KeyEvent(time, time,
                        KeyEvent.ACTION_DOWN, keyCode, 0))
                    audio.dispatchMediaKeyEvent(KeyEvent(time, time,
                        KeyEvent.ACTION_UP, keyCode, 0))
                    receipt(action, "SENT",
                        "Android recibió teclas multimedia; reproducción o salto no verificados")
                    feedback(when (action) {
                        SkyQuickCommand.Action.NEXT ->
                            "Pedí pasar a la siguiente canción. Comprobá el reproductor."
                        SkyQuickCommand.Action.PREVIOUS ->
                            "Pedí volver a la canción anterior. Comprobá el reproductor."
                        SkyQuickCommand.Action.RESTART ->
                            "Pedí volver al inicio. Según el reproductor, podría cambiar a la canción anterior."
                        SkyQuickCommand.Action.PAUSE ->
                            "Pedí pausar la música. Comprobá si se detuvo."
                        SkyQuickCommand.Action.PLAY ->
                            "Pedí reanudar la música. Comprobá si comenzó."
                        else -> "Orden multimedia solicitada."
                    })
                }
            }
        } catch (_: SecurityException) {
            receipt(action, "FAILED", "Android denegó permiso para la acción multimedia")
            feedback("Android no autorizó este control multimedia.")
        } catch (_: RuntimeException) {
            receipt(action, "FAILED", "Android lanzó un error al procesar el control multimedia")
            feedback("El reproductor no permitió completar la orden.")
        }
    }

    private fun requestUnlock() {
        try {
            val manager = host.getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
            if (!manager.isKeyguardLocked) {
                receipt(SkyQuickCommand.Action.REQUEST_UNLOCK, "VERIFIED_LOCAL",
                    "Android informa que Keyguard no está bloqueado")
                feedback("El teléfono ya está desbloqueado.")
                return
            }
            // Android may present PIN, pattern or biometric. SKY never knows it.
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
                host.setTurnScreenOn(true)
            }
            manager.requestDismissKeyguard(
                host, object : KeyguardManager.KeyguardDismissCallback() {
                    override fun onDismissSucceeded() {
                        receipt(SkyQuickCommand.Action.REQUEST_UNLOCK, "VERIFIED_LOCAL",
                            "Android confirmó que se desestimó Keyguard")
                        feedback("Android confirmó el desbloqueo.")
                    }
                    override fun onDismissCancelled() {
                        receipt(SkyQuickCommand.Action.REQUEST_UNLOCK, "REJECTED",
                            "El propietario canceló la solicitud de desbloqueo")
                        feedback("Desbloqueo cancelado. La pantalla sigue protegida.")
                    }
                    override fun onDismissError() {
                        receipt(SkyQuickCommand.Action.REQUEST_UNLOCK, "FAILED",
                            "Android no presentó el desbloqueo seguro")
                        feedback("No pude mostrar el desbloqueo desde esta pantalla. " +
                            "Usá huella, PIN o la pantalla de bloqueo del Samsung.")
                    }
                }
            )
            receipt(SkyQuickCommand.Action.REQUEST_UNLOCK, "SENT",
                "Solicitud presentada a Android; confirmación pendiente")
            feedback("Solicité mostrar el desbloqueo seguro de Android.")
        } catch (_: Exception) {
            receipt(SkyQuickCommand.Action.REQUEST_UNLOCK, "FAILED",
                "No se pudo solicitar el desbloqueo seguro a Android")
            feedback("No pude solicitar el desbloqueo seguro. " +
                "Usá la huella o el PIN del Samsung.")
        }
    }
}
