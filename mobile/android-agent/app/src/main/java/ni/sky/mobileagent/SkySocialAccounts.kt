package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.text.InputFilter
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import java.io.ByteArrayOutputStream
import org.json.JSONArray
import org.json.JSONObject

/**
 * On-device catalog for user-provided PUBLIC profiles.
 * Identified != OAuth connected != published. Never stores passwords or tokens.
 */
class SkySocialAccounts(
    private val host: Activity,
    private val prefs: SharedPreferences,
    private val chooseImport: () -> Unit,
    private val createContent: (String) -> Unit,
    private val feedback: (String) -> Unit
) {
    private val key = "public_profiles_v1"

    fun list(): List<SkySocialProfileData.Profile> = runCatching {
        val array = JSONArray(prefs.getString(key, "[]"))
        (0 until array.length()).mapNotNull { index ->
            val entry = array.optJSONObject(index) ?: return@mapNotNull null
            val p = SkySocialProfileData.Profile(
                entry.optString("platform"), entry.optString("handle"),
                entry.optString("display_name"))
            if (SkySocialProfileData.validate(p) == null) p else null
        }
    }.getOrDefault(emptyList())

    private fun save(profiles: List<SkySocialProfileData.Profile>) {
        val array = JSONArray()
        profiles.take(25).forEach { p ->
            array.put(JSONObject().put("platform", p.platform)
                .put("handle", SkySocialProfileData.cleanHandle(p.handle))
                .put("display_name", p.displayName))
        }
        prefs.edit().putString(key, array.toString()).apply()
    }

    private fun padding(value: Int): Int =
        (value * host.resources.displayMetrics.density + .5f).toInt()

    fun show() {
        val profiles = list()
        val labels = profiles.map { p ->
            p.platform + " · " +
                (if (p.handle.isNotBlank()) "@" + p.handle else p.displayName) +
                " · identificada, sin autorización OAuth"
        }
        val actions = labels + listOf("＋ Agregar una red", "↓ Importar perfiles JSON")
        AlertDialog.Builder(host)
            .setTitle("SKY · Mis redes personales")
            .setMessage("Estos perfiles se guardan solo en este teléfono. " +
                "No están conectados a sus estadísticas ni a publicación automática. " +
                "Para conectar una cuenta necesitaremos autorización oficial.")
            .setItems(actions.toTypedArray()) { _, index ->
                when (index) {
                    profiles.size -> showEditor()
                    profiles.size + 1 -> chooseImport()
                    else -> showProfile(profiles[index])
                }
            }
            .setNegativeButton("Cerrar", null)
            .show()
    }

    private fun showProfile(profile: SkySocialProfileData.Profile) {
        val url = SkySocialProfileData.publicUrl(profile)
        val label = if (profile.handle.isNotBlank()) "@" + profile.handle else profile.displayName
        val choices = arrayOf("Abrir perfil público", "Crear contenido para esta red",
            "Editar identificador", "Quitar de SKY") +
            if (profile.platform == "Instagram")
                arrayOf("Conexión segura con Instagram", "Guía de cuenta Creador") else emptyArray<String>()
        AlertDialog.Builder(host)
            .setTitle(profile.platform + " · " + label)
            .setMessage("Perfil identificado localmente. Sin acceso a estadísticas, " +
                "publicación automática o mensajes privados. " +
                "SKY no tiene sesión OAuth de esta cuenta.")
            .setItems(choices) { _, which ->
                when (which) {
                    0 -> if (url == null) feedback("Necesito el usuario o enlace público exacto de este perfil.") else {
                        try { host.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
                        catch (_: Exception) { feedback("No pude abrir el perfil público.") }
                    }
                    1 -> createContent(profile.platform)
                    2 -> showEditor(profile)
                    3 -> AlertDialog.Builder(host)
                        .setTitle("Quitar perfil")
                        .setMessage("¿Quitar " + profile.platform + " de SKY? No cambia tu cuenta en esa red.")
                        .setPositiveButton("Quitar") { _, _ ->
                            val items = list().toMutableList()
                            items.remove(profile)
                            save(items)
                            feedback("Perfil retirado de SKY.")
                        }
                        .setNegativeButton("Cancelar", null).show()
                    4 -> if (profile.platform == "Instagram")
                        SkyInstagramMobileLink(host, feedback).show()
                    5 -> if (profile.platform == "Instagram")
                        showInstagramPreparation(profile)
                }
            }
            .setNegativeButton("Cerrar", null).show()
    }

    /**
     * Pre-OAuth guidance. No third-party session is opened inside SKY and
     * a Creator declaration is never represented as an API connection.
     */
    private fun showInstagramPreparation(profile: SkySocialProfileData.Profile) {
        val handle = SkySocialProfileData.cleanHandle(profile.handle)
        val preferenceKey = "instagram_creator_declared_" + handle.lowercase(java.util.Locale.ROOT)
        val declared = prefs.getBoolean(preferenceKey, false)
        val type = if (declared) SkyInstagramPrerequisites.Type.CREATOR
                   else SkyInstagramPrerequisites.Type.UNKNOWN
        val current = SkyInstagramPrerequisites.checklist(type, false, false)
        val options = arrayOf(
            "1 · Abrir Instagram para cambiar a Creador",
            "2 · Ya cambié a Creador (marcar solo como declarado)",
            "3 · Abrir Meta for Developers",
            "4 · Consultar permisos y pasos de conexión"
        )
        AlertDialog.Builder(host)
            .setTitle("SKY · Preparar Instagram")
            .setMessage("@" + handle + "\n\n" + current +
                "\n\nTu cuenta y tus publicaciones siguen bajo tu control. " +
                "Una cuenta profesional normalmente será pública. " +
                "SKY NO tiene aún permiso OAuth para métricas ni publicaciones.")
            .setItems(options) { _, index ->
                when (index) {
                    0 -> {
                        AlertDialog.Builder(host)
                            .setTitle("Pasar a cuenta de Creador")
                            .setMessage("En Instagram: Perfil → ☰ → Tipo de cuenta y herramientas " +
                                "→ Cambiar a cuenta profesional → Creador. " +
                                "Tus publicaciones y seguidores se conservan, " +
                                "pero el perfil profesional será público. " +
                                "Revisá la privacidad antes de confirmar.")
                            .setPositiveButton("ABRIR INSTAGRAM") { _, _ ->
                                try {
                                    host.startActivity(Intent(Intent.ACTION_VIEW,
                                        Uri.parse("https://www.instagram.com/" + handle + "/")))
                                } catch (_: Exception) {
                                    feedback("No pude abrir Instagram.")
                                }
                            }
                            .setNegativeButton("Cancelar", null).show()
                    }
                    1 -> AlertDialog.Builder(host)
                        .setTitle("Confirmá el cambio manual")
                        .setMessage("¿Ya terminaste en Instagram el cambio a Creador " +
                            "o Empresa? SKY guardará únicamente tu declaración. " +
                            "NO significa que Meta haya autorizado la cuenta.")
                        .setPositiveButton("Sí, lo cambié") { _, _ ->
                            prefs.edit().putBoolean(preferenceKey, true).apply()
                            feedback("Tipo profesional declarado. Falta configurar la " +
                                "app en Meta y completar OAuth seguro.")
                        }
                        .setNegativeButton("Todavía no", null).show()
                    2 -> {
                        try {
                            host.startActivity(Intent(Intent.ACTION_VIEW,
                                Uri.parse(SkyInstagramPrerequisites.META_DEVELOPERS)))
                        } catch (_: Exception) {
                            feedback("No pude abrir Meta for Developers.")
                        }
                    }
                    3 -> AlertDialog.Builder(host)
                        .setTitle("Instagram · autorización real")
                        .setMessage("1. Convertí tu cuenta a Creador.\n\n" +
                            "2. Registrá una aplicación en Meta for Developers y " +
                            "habilitá Instagram API with Instagram Login.\n\n" +
                            "3. Para leer estadísticas necesitaremos " +
                            "instagram_business_basic y " +
                            "instagram_business_manage_insights. " +
                            "Publicar requiere también instagram_business_content_publish.\n\n" +
                            "4. Falta un backend HTTPS que guarde el secreto de Meta, " +
                            "valide OAuth y entregue el estado a SKY. " +
                            "No introduzcás secretos en Android ni GitHub.\n\n" +
                            "Este botón NO solicita autorización todavía.")
                        .setPositiveButton("Entendido", null).show()
                }
            }
            .setNegativeButton("Cerrar", null)
            .show()
    }

    private fun showEditor(old: SkySocialProfileData.Profile? = null) {
        val layout = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding(20), padding(10), padding(20), padding(10))
        }
        layout.addView(TextView(host).apply {
            text = "Identificador público únicamente. No ingresés claves, correo, " +
                "número de WhatsApp ni códigos de acceso."
        })
        val platform = Spinner(host)
        platform.adapter = ArrayAdapter(host, android.R.layout.simple_spinner_dropdown_item,
            SkySocialProfileData.platforms)
        platform.setSelection(SkySocialProfileData.platforms.indexOf(old?.platform ?: "Instagram")
            .coerceAtLeast(0))
        layout.addView(platform)
        val handle = EditText(host).apply {
            hint = "@usuario (en Facebook puede quedar vacío)"
            setSingleLine(true)
            filters = arrayOf(InputFilter.LengthFilter(60))
            setText(old?.handle.orEmpty())
        }
        layout.addView(handle)
        val display = EditText(host).apply {
            hint = "Nombre visible (opcional)"
            setSingleLine(true)
            filters = arrayOf(InputFilter.LengthFilter(100))
            setText(old?.displayName.orEmpty())
        }
        layout.addView(display)
        AlertDialog.Builder(host)
            .setTitle(if (old == null) "Agregar perfil público" else "Editar perfil")
            .setView(layout)
            .setPositiveButton("Guardar") { _, _ ->
                val next = SkySocialProfileData.Profile(platform.selectedItem.toString(),
                    SkySocialProfileData.cleanHandle(handle.text.toString()),
                    display.text.toString().trim())
                val error = SkySocialProfileData.validate(next)
                if (error != null) { feedback(error); return@setPositiveButton }
                val items = list().toMutableList()
                if (old != null) items.remove(old)
                if (items.any {
                    it.platform == next.platform &&
                    it.handle.equals(next.handle, ignoreCase = true)
                }) {
                    feedback("Ya tenés registrado ese usuario en esta red.")
                    return@setPositiveButton
                }
                if (items.size >= 25) { feedback("Máximo 25 perfiles."); return@setPositiveButton }
                items.add(next)
                save(items)
                feedback("Perfil guardado localmente. Todavía no hay autorización OAuth.")
            }
            .setNegativeButton("Cancelar", null).show()
    }

    fun chooseJson() {
        try {
            host.startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "*/*"
                putExtra(Intent.EXTRA_MIME_TYPES, arrayOf(
                    "application/json", "text/plain", "application/octet-stream"))
            }, 1655)
        } catch (_: Exception) {
            feedback("Android no encontró un selector de archivos JSON.")
        }
    }

    fun importJson(uri: Uri) {
        try {
            val bytes = host.contentResolver.openInputStream(uri)?.use {
                it.readNBytesCompat(20_001)
            } ?: error("No se pudo abrir el archivo.")
            require(bytes.size <= 20_000) { "El archivo supera 20 KB." }
            val root = JSONObject(String(bytes, Charsets.UTF_8).removePrefix("\uFEFF"))
            require(root.optInt("sky_profiles_version") == 1) {
                "Este archivo no tiene el formato de perfiles SKY."
            }
            val array = root.optJSONArray("profiles") ?: error("No hay perfiles.")
            require(array.length() in 1..25) { "El archivo necesita entre 1 y 25 perfiles." }
            val additions = (0 until array.length()).map { index ->
                val obj = array.getJSONObject(index)
                val p = SkySocialProfileData.Profile(obj.getString("platform"),
                    obj.optString("handle"), obj.optString("display_name"))
                val error = SkySocialProfileData.validate(p)
                require(error == null) { "Perfil " + (index + 1) + ": " + error }
                p
            }
            val existing = list().toMutableList()
            var added = 0
            additions.forEach { profile ->
                if (existing.none {
                    it.platform == profile.platform &&
                    it.handle.equals(profile.handle, ignoreCase = true)
                } && existing.size < 25) {
                    existing.add(profile)
                    added++
                }
            }
            save(existing)
            feedback("Importé " + added + " perfiles públicos al teléfono. " +
                "No importé contraseñas ni conecté las cuentas por OAuth.")
            show()
        } catch (error: Exception) {
            AlertDialog.Builder(host)
                .setTitle("No se pudieron importar los perfiles")
                .setMessage(error.message ?: "Revisá el archivo JSON.")
                .setPositiveButton("Entendido", null).show()
        }
    }

    private fun java.io.InputStream.readNBytesCompat(limit: Int): ByteArray {
        val buffer = ByteArrayOutputStream()
        val data = ByteArray(2048)
        while (buffer.size() < limit) {
            val len = read(data, 0, minOf(data.size, limit - buffer.size()))
            if (len < 0) break
            buffer.write(data, 0, len)
        }
        return buffer.toByteArray()
    }
}
