package ni.sky.mobileagent

/** Public social handles only. Never store credentials, tokens, email or phone. */
object SkySocialProfileData {
    data class Profile(val platform: String, val handle: String, val displayName: String = "")

    val platforms = listOf("Instagram", "Threads", "TikTok", "Facebook", "YouTube",
        "X", "Snapchat", "Pinterest", "LinkedIn")

    fun cleanHandle(raw: String): String = raw.trim().removePrefix("@")

    fun validate(profile: Profile): String? {
        if (profile.platform !in platforms) return "Plataforma no admitida."
        val handle = cleanHandle(profile.handle)
        if (profile.displayName.length > 100 || profile.displayName.contains('\n'))
            return "Nombre visible demasiado largo."
        if (handle.isBlank()) {
            return if (profile.platform == "Facebook" && profile.displayName.isNotBlank())
                null else "Escribí el usuario público; no la contraseña ni el correo."
        }
        if (handle.length > 60 || handle.contains('\n') ||
            handle.contains('@') || handle.contains(':') || handle.contains('/'))
            return "Solo se permite el nombre público de usuario."
        val valid = when (profile.platform) {
            "Instagram", "Threads" -> Regex("[A-Za-z0-9._]{1,30}").matches(handle)
            "TikTok" -> Regex("[A-Za-z0-9._]{2,24}").matches(handle)
            "X" -> Regex("[A-Za-z0-9_]{1,15}").matches(handle)
            "YouTube" -> Regex("[A-Za-z0-9._-]{3,30}").matches(handle)
            "Snapchat" -> Regex("[A-Za-z0-9._-]{3,30}").matches(handle)
            "Pinterest" -> Regex("[A-Za-z0-9_]{3,30}").matches(handle)
            "LinkedIn", "Facebook" -> Regex("[A-Za-z0-9._-]{2,60}").matches(handle)
            else -> false
        }
        return if (valid) null else "El usuario no cumple el formato de " + profile.platform + "."
    }

    /** A display name is not a verified URL. Never guess a Facebook slug. */
    fun publicUrl(profile: Profile): String? {
        if (validate(profile) != null) return null
        val h = cleanHandle(profile.handle)
        if (h.isBlank()) return null
        return when (profile.platform) {
            "Instagram" -> "https://www.instagram.com/$h/"
            "Threads" -> "https://www.threads.net/@$h"
            "TikTok" -> "https://www.tiktok.com/@$h"
            "Facebook" -> "https://www.facebook.com/$h"
            "YouTube" -> "https://www.youtube.com/@$h"
            "X" -> "https://x.com/$h"
            "Snapchat" -> "https://www.snapchat.com/add/$h"
            "Pinterest" -> "https://www.pinterest.com/$h/"
            "LinkedIn" -> "https://www.linkedin.com/in/$h/"
            else -> null
        }
    }
}
