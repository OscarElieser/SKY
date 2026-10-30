package ni.sky.mobileagent

import android.app.Activity
import android.app.SearchManager
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.provider.MediaStore
import android.os.Handler
import android.os.Looper

/**
 * Android media action with a truthful fallback.
 * Playback depends on whether the installed streaming app handles the intent.
 */
class SkyMusicLauncher(
    private val host: Activity,
    private val prefs: SharedPreferences,
    private val tell: (String) -> Unit,
    private val onNeedMusicPermission: (SkyMusicCommand.Request) -> Unit
) {
    var onReceipt: ((String, String, String, String) -> Unit)? = null
    private var operationId = java.util.UUID.randomUUID().toString()
    private val verificationHandler = Handler(Looper.getMainLooper())
    private var playbackRequestId = 0

    /** Prevent stale Activity callbacks from reporting a result after closing SKY. */
    fun close() {
        playbackRequestId++
        verificationHandler.removeCallbacksAndMessages(null)
    }

    /** Check actual player metadata only after explicit Android notification access. */
    private fun checkPlayback(request: SkyMusicCommand.Request,
                              playerPackage: String, label: String,
                              requestId: Int, operation: String, step: Int = 0) {
        if (requestId != playbackRequestId) return
        if (SkyPlaybackProof.playing(host, playerPackage, request.query)) {
            receipt(request.query, "VERIFIED_LOCAL",
                "Android MediaSession confirmó PLAYING y metadatos de canción coincidentes en $label; audio audible no medido", operation)
            tell("Android confirmó que $label está reproduciendo «${request.query}».")
            return
        }
        if (step < 12) {
            verificationHandler.postDelayed({
                checkPlayback(request, playerPackage, label, requestId, operation, step + 1)
            }, 1000L)
        } else {
            receipt(request.query, "ESTADO_DESCONOCIDO",
                "No se detectó una MediaSession PLAYING con el título exacto en $label " +
                    "tras 12 comprobaciones; no se confirma reproducción ni audio audible", operation)
            tell("Android recibió la orden para «${request.query}» en $label, " +
                "pero no pude confirmar la canción en reproducción. Revisá el reproductor.")
        }
    }

    private fun receipt(song: String, status: String, detail: String,
                        operation: String = operationId) {
        onReceipt?.invoke("Música: " + song.take(100), status, detail, operation)
    }
    companion object {
        private const val MUSIC_PREF = "preferred_music"
    }
    private fun packageName(service: SkyMusicCommand.Service) = when (service) {
        SkyMusicCommand.Service.SPOTIFY -> "com.spotify.music"
        SkyMusicCommand.Service.YOUTUBE_MUSIC -> "com.google.android.apps.youtube.music"
        SkyMusicCommand.Service.YOUTUBE -> "com.google.android.youtube"
    }
    fun preferred(): SkyMusicCommand.Service = runCatching {
        SkyMusicCommand.Service.valueOf(prefs.getString(MUSIC_PREF, "") ?: "")
    }.getOrDefault(SkyMusicCommand.Service.YOUTUBE_MUSIC)

    fun savePreferred(value: SkyMusicCommand.Service) {
        prefs.edit().putString(MUSIC_PREF, value.name).apply()
    }
    fun play(request: SkyMusicCommand.Request) {
        operationId = java.util.UUID.randomUUID().toString()
        playbackRequestId++
        // Distributable standard build never asks for accessibility privileges.
        // It requests playback via Android's documented music intent instead.
        if (!BuildConfig.ENABLE_TEXT_ASSIST) {
            playViaAndroidIntent(request)
            return
        }
        val chosen = request.service ?: preferred()
        val title = SkyMusicCommand.label(chosen)
        val pkg = packageName(chosen)
        if (!SkyMusicControlService.enabled()) {
            onNeedMusicPermission(request)
            return
        }
        if (!SkyMusicControlService.arm(pkg, request.query, tell)) {
            tell("No pude preparar el control musical. Revisá su autorización en Ajustes.")
            return
        }
        try {
            val launch = host.packageManager.getLaunchIntentForPackage(pkg)
                ?: throw ActivityNotFoundException("La aplicación no está instalada")
            host.startActivity(launch)
            receipt(request.query, "SENT", "Android abrió reproductor; reproducción pendiente de verificación")
            tell("Estoy buscando «${request.query}» en $title, pero aún no he confirmado la reproducción.")
        } catch (_: Exception) {
            SkyMusicControlService.cancelPending()
            receipt(request.query, "FAILED", "No pudo abrir reproductor")
            tell("No pude abrir $title. Verificá que esté instalado y disponible.")
        }
    }

    /** Official Android action retained as a user-selected fallback. */
    fun playViaAndroidIntent(request: SkyMusicCommand.Request) {
        operationId = java.util.UUID.randomUUID().toString()
        val requestId = ++playbackRequestId
        val chosen = request.service ?: preferred()
        val title = SkyMusicCommand.label(chosen)
        val pkg = packageName(chosen)
        val player = Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH).apply {
            setPackage(pkg)
            addCategory(Intent.CATEGORY_DEFAULT)
            // Android documentation specifies this song-specific search mode;
            // Audio.Media.ENTRY_CONTENT_TYPE is a provider MIME type, not this action's focus.
            putExtra(MediaStore.EXTRA_MEDIA_FOCUS, "vnd.android.cursor.item/audio")
            putExtra(MediaStore.EXTRA_MEDIA_TITLE, request.query)
            putExtra(SearchManager.QUERY, request.query)
        }
        val launched = try {
            host.startActivity(player)
            true
        } catch (_: ActivityNotFoundException) { false
        } catch (_: SecurityException) { false
        } catch (_: IllegalArgumentException) { false }
        if (launched) {
            receipt(request.query, "SENT", "Intent de reproducción aceptado; audio no verificado")
            tell("Solicité reproducir «${request.query}» en $title. " +
                "La aplicación decidirá si puede iniciar esa canción. " +
                "Todavía no he comprobado que esté sonando.")
            if (SkyPlaybackProof.available(host)) {
                checkPlayback(request, pkg, title, requestId, operationId)
            }
            return
        }
        // Deep links are for SEARCH, not evidence of successful playback.
        val link = when (chosen) {
            SkyMusicCommand.Service.SPOTIFY ->
                "https://open.spotify.com/search/" + Uri.encode(request.query)
            SkyMusicCommand.Service.YOUTUBE_MUSIC ->
                "https://music.youtube.com/search?q=" + Uri.encode(request.query)
            SkyMusicCommand.Service.YOUTUBE ->
                "https://www.youtube.com/results?search_query=" + Uri.encode(request.query)
        }
        try {
            host.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(link)))
            receipt(request.query, "SENT", "Solo búsqueda abierta; reproducción no verificada")
            tell("Abrí la búsqueda de «${request.query}» en $title, " +
                "pero esa app no aceptó la reproducción directa por Android.")
        } catch (_: Exception) {
            receipt(request.query, "FAILED", "Android no abrió búsqueda musical")
            tell("No encontré una aplicación compatible para abrir música.")
        }
    }
}
