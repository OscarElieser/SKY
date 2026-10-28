package ni.sky.mobileagent

/**
 * Pure readiness model. A self-reported Creator account is NOT OAuth access.
 * No tokens or Instagram app secret may be embedded in the Android APK.
 */
object SkyInstagramPrerequisites {
    enum class Type { PERSONAL, CREATOR, BUSINESS, UNKNOWN }

    val basicScopes = listOf("instagram_business_basic")
    val analyticsScopes = basicScopes + "instagram_business_manage_insights"
    val publishingScopes = basicScopes + "instagram_business_content_publish"

    fun eligible(type: Type) = type == Type.CREATOR || type == Type.BUSINESS

    fun checklist(type: Type, metaAppConfigured: Boolean, secureBackend: Boolean): String {
        if (!eligible(type)) return "Convertí primero Instagram a Creador o Empresa. " +
            "Las cuentas personales no admiten la API profesional."
        if (!metaAppConfigured) return "Cuenta profesional indicada. Falta registrar " +
            "una aplicación Meta con Instagram API with Instagram Login."
        if (!secureBackend) return "Falta un servidor HTTPS para el intercambio " +
            "del código OAuth y la custodia del secreto de Meta."
        return "Requisitos técnicos preparados, pero todavía falta " +
            "autorizar desde Instagram y verificar el token y los permisos."
    }

    const val INSTAGRAM = "https://www.instagram.com/"
    const val META_DEVELOPERS = "https://developers.facebook.com/apps/"
}
