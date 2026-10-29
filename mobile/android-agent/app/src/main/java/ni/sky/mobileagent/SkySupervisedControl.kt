package ni.sky.mobileagent

import android.content.Context

/**
 * Consentimiento único, persistente y revocable del propietario para comandos
 * LOCALES explícitos. No es un permiso de Android, no delega control remoto,
 * no concede accesibilidad ni aprueba eliminación de datos o envíos.
 */
class SkySupervisedControl(context: Context) {
    private val prefs = context.getSharedPreferences(
        "sky_trusted_launcher_apps", Context.MODE_PRIVATE
    )

    fun isAuthorized(): Boolean = prefs.getBoolean("global_supervised_control", false)

    /** commit permite reportar error de almacenamiento en vez de fingir éxito. */
    fun setAuthorized(enabled: Boolean): Boolean =
        prefs.edit().putBoolean("global_supervised_control", enabled).commit()
}
