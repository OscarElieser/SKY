package ni.sky.mobileagent

/**
 * La salida de un modelo, documento, web o servicio remoto nunca se convierte
 * en permiso para abrir aplicaciones o modificar datos en Android.
 * Esta autorización se evalúa ADEMÁS del control supervisado y del sistema.
 */
object SkyActionTrustBoundary {
    enum class Origin {
        OWNER_TYPED, OWNER_SPOKEN, MODEL_OUTPUT, DOCUMENT, WEB_PAGE,
        EXTERNAL_MESSAGE, REMOTE_SERVER
    }

    fun allowsLocalCommand(origin: Origin): Boolean =
        origin == Origin.OWNER_TYPED || origin == Origin.OWNER_SPOKEN
}
