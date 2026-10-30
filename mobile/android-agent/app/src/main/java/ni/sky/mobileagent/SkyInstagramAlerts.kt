package ni.sky.mobileagent

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.security.keystore.KeyProperties
import android.util.Base64
import java.net.HttpURLConnection
import java.net.URL
import java.security.KeyStore
import java.time.OffsetDateTime
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import org.json.JSONArray
import org.json.JSONObject

/**
 * Read-only proactive Instagram assistant. Uses only the revocable credential
 * already stored by SKY with Android Keystore. No message bodies stored locally.
 * Polling runs while the Activity or opt-in hands-free service is alive.
 */
internal object SkyInstagramAlerts {
    const val EXTRA_READ = "ni.sky.mobileagent.READ_INSTAGRAM"
    private const val BASE =
        "https://jojzuaeqmjgnqikpnfxk.supabase.co/functions/v1/sky-instagram"
    private const val PREFS = "sky_instagram_alerts_v1"
    private const val CHANNEL = "sky_instagram_notice"
    private const val NOTIFICATION = 4210

    enum class Command { READ, ENABLE, DISABLE, NONE }
    data class Message(val key: String, val sender: String, val body: String, val at: Long)
    data class Snapshot(val profileId: String, val messages: List<Message>)
    data class Update(val newCount: Int, val firstSync: Boolean)

    fun command(raw: String): Command {
        val s = SkyVoicePresence.normalized(raw).replace(
            Regex("^(?:hola )?(?:sky ia|sky|esky|escai|esquai)\\s*"), "")
        if (!Regex("\\b(instagram|insta)\\b").containsMatchIn(s)) return Command.NONE
        if (Regex("\\b(desactiva|apaga|silencia|deten|para)\\b").containsMatchIn(s) &&
            Regex("\\b(aviso|avisos|notificaciones|alertas)\\b").containsMatchIn(s))
            return Command.DISABLE
        if (Regex("\\b(activa|enciende|avisa|notificame|alertame)\\b").containsMatchIn(s) &&
            Regex("\\b(mensaje|mensajes|avisos|notificaciones|alertas)\\b").containsMatchIn(s))
            return Command.ENABLE
        if (Regex("\\b(mensaje|mensajes|bandeja|chats|directos|dm)\\b").containsMatchIn(s) &&
            Regex("\\b(lee|leeme|leer|revisa|revisar|dime|decime|cuenta|contame|tengo|llego|llegaron|nuevos|que|mostra|mostrar|abre|abrir)\\b").containsMatchIn(s))
            return Command.READ
        return Command.NONE
    }

    fun paired(ctx: Context): Boolean =
        ctx.getSharedPreferences("sky_instagram_mobile_v1", Context.MODE_PRIVATE)
            .contains("credential")
    fun enabled(ctx: Context): Boolean =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean("enabled", true)
    fun setEnabled(ctx: Context, enabled: Boolean) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean("enabled", enabled).apply()
        if (!enabled) (ctx.getSystemService(Context.NOTIFICATION_SERVICE)
            as NotificationManager).cancel(NOTIFICATION)
    }

    private fun credential(ctx: Context): String = try {
        val prefs = ctx.getSharedPreferences("sky_instagram_mobile_v1", Context.MODE_PRIVATE)
        val iv = prefs.getString("iv", null) ?: return ""
        val value = prefs.getString("credential", null) ?: return ""
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val key = ks.getKey("sky_instagram_device_v1", null) as? SecretKey ?: return ""
        require(key.algorithm == KeyProperties.KEY_ALGORITHM_AES)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key,
            GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
        String(cipher.doFinal(Base64.decode(value, Base64.NO_WRAP)), Charsets.UTF_8)
    } catch (_: Exception) { "" }

    private fun get(path: String, token: String): JSONObject {
        require(path == "/mobile-profile" || path == "/mobile-events")
        val conn = URL(BASE + path).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "GET"
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 8000
            conn.readTimeout = 10000
            conn.setRequestProperty("Accept", "application/json")
            conn.setRequestProperty("Cache-Control", "no-store")
            conn.setRequestProperty("Authorization", "Bearer " + token)
            val status = conn.responseCode
            if (status == 401 || status == 403) error("Volvé a vincular Instagram en SKY.")
            if (status !in 200..299) error("Servidor Instagram HTTP " + status)
            val data = conn.inputStream.bufferedReader().use { it.readText().take(700001) }
            require(data.length <= 700000) { "Respuesta demasiado grande." }
            return JSONObject(data)
        } finally { conn.disconnect() }
    }

    /** Must run on a worker thread. No simulated events or fake sender names. */
    fun fetch(ctx: Context): Snapshot {
        val token = credential(ctx)
        require(token.isNotBlank()) { "Este teléfono no está vinculado con Instagram." }
        val identity = get("/mobile-profile", token)
        require(identity.optBoolean("token_valid") && identity.optBoolean("profile_verified")) {
            "La identidad de Instagram necesita verificación con Meta."
        }
        val id = identity.optString("profile_id")
        require(id.matches(Regex("[0-9]{5,30}"))) { "Perfil de Meta no válido." }
        val events = get("/mobile-events", token).optJSONArray("events") ?: JSONArray()
        val messages = (0 until events.length()).mapNotNull { i ->
            val v = events.optJSONObject(i) ?: return@mapNotNull null
            if (v.optString("event_type") != "message" ||
                !SkyInstagramInboxRules.belongsToProfile(id, v.optString("ig_account_id")) ||
                !SkyInstagramInboxRules.isIncoming(id, v.optString("actor_id")))
                return@mapNotNull null
            val key = v.optString("event_key").take(120)
            if (key.isBlank()) return@mapNotNull null
            val at = try {
                OffsetDateTime.parse(v.optString("received_at")).toInstant().toEpochMilli()
            } catch (_: Exception) { return@mapNotNull null }
            Message(key, v.optString("actor_id"),
                SkyInstagramInboxRules.preview(v.optString("message_text"), 500), at)
        }.sortedWith(compareByDescending<Message> { it.at }.thenBy { it.key })
        return Snapshot(id, messages)
    }

    /** Shared high-water mark prevents duplicate announcements after restarts. */
    @Synchronized fun observe(ctx: Context, snapshot: Snapshot): Update {
        val p = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val first = !p.getBoolean("seen", false) ||
            p.getString("profile", "") != snapshot.profileId
        val last = if (first) 0L else p.getLong("last_time", 0L)
        val edge = if (first) emptySet() else
            p.getString("edge", "")!!.split("|").filter { it.isNotBlank() }.toSet()
        val newer = if (first) emptyList() else snapshot.messages.filter {
            it.at > last || (it.at == last && it.key !in edge)
        }
        val highest = maxOf(last, snapshot.messages.maxOfOrNull { it.at } ?: 0L)
        val highKeys = (if (highest == last) edge else emptySet()) +
            snapshot.messages.filter { it.at == highest }.map { it.key }
        p.edit().putBoolean("seen", true).putString("profile", snapshot.profileId)
            .putLong("last_time", highest).putString("edge", highKeys.take(50).joinToString("|"))
            .commit()
        return Update(newer.size, first)
    }

    fun summary(snapshot: Snapshot): String {
        if (snapshot.messages.isEmpty())
            return "No encontré mensajes recibidos en el historial reciente de Instagram."
        val excerpts = snapshot.messages.take(3).mapIndexed { i, m ->
            "Mensaje " + (i + 1) + ": " +
                SkyInstagramInboxRules.preview(m.body, 140)
        }
        return "En Instagram encontré " + snapshot.messages.size +
            " mensajes recibidos recientemente. " +
            excerpts.joinToString(". ") + ". No he enviado respuestas."
    }

    /** Privacy: no message text, sender ID or full account name on lock screen. */
    fun notifyNew(ctx: Context, count: Int) {
        if (count <= 0 || !enabled(ctx)) return
        val manager = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(NotificationChannel(CHANNEL,
            "Instagram · SKY", NotificationManager.IMPORTANCE_DEFAULT))
        if (Build.VERSION.SDK_INT >= 33 &&
            ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED) return
        val intent = Intent(ctx, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(EXTRA_READ, true)
        }
        val pending = PendingIntent.getActivity(ctx, NOTIFICATION, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        manager.notify(NOTIFICATION, Notification.Builder(ctx, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_dialog_email)
            .setContentTitle("SKY IA · Instagram")
            .setContentText(if (count == 1) "Llegó un mensaje nuevo"
                else "Llegaron " + count + " mensajes nuevos")
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            .setAutoCancel(true).setContentIntent(pending).build())
    }
}
