package ni.sky.mobileagent

import android.app.Activity
import android.app.role.RoleManager
import android.content.Context
import android.os.Build

/**
 * Permite que el usuario ELIJA SKY desde el selector oficial de Android.
 * No concede el rol, activa el micrófono, lee el contexto ni cambia ajustes
 * por su cuenta. ACTION_ASSIST solo ofrece una entrada a nuestra Activity.
 */
object SkyAssistantRole {
    const val REQUEST_CODE = 1686

    enum class State { NOT_SUPPORTED, UNAVAILABLE, AVAILABLE, SELECTED }

    fun state(context: Context): State {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return State.NOT_SUPPORTED
        val manager = context.getSystemService(RoleManager::class.java)
            ?: return State.UNAVAILABLE
        if (!manager.isRoleAvailable(RoleManager.ROLE_ASSISTANT)) return State.UNAVAILABLE
        return if (manager.isRoleHeld(RoleManager.ROLE_ASSISTANT))
            State.SELECTED else State.AVAILABLE
    }

    fun request(activity: Activity): Boolean {
        if (state(activity) != State.AVAILABLE) return false
        val manager = activity.getSystemService(RoleManager::class.java) ?: return false
        return try {
            activity.startActivityForResult(
                manager.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT),
                REQUEST_CODE
            )
            true
        } catch (_: Exception) {
            false
        }
    }

    fun description(state: State): String = when (state) {
        State.NOT_SUPPORTED -> "Esta versión de Android no ofrece el selector de rol de asistente."
        State.UNAVAILABLE -> "Android no ofrece el rol de asistente en este dispositivo."
        State.AVAILABLE -> "SKY puede solicitar ser tu asistente predeterminada. Vos elegís en Android."
        State.SELECTED -> "Android confirma que SKY es tu asistente predeterminada."
    }
}
