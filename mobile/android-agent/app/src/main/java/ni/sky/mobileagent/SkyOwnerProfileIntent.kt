package ni.sky.mobileagent

/** Explicit owner command; no files are read until Android picker grants access. */
internal object SkyOwnerProfileIntent {
    fun requestsImport(request: String): Boolean {
        val s = SkyAndroidCognition.normalize(request).removePrefix("sky ").trim()
        return s in setOf("importa mi perfil", "importar mi perfil",
            "carga mi perfil personal", "cargar mi perfil personal",
            "importa mi informacion personal", "quiero importar mi perfil",
            "importa mi perfil desde windows", "sincroniza mi perfil desde windows")
    }
}
