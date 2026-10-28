package ni.sky.mobileagent

import android.app.Activity
import android.app.SearchManager
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.provider.MediaStore

/**
 * Android media action with a truthful fallback.
 * Playback depends on whether the installed streaming app handles the intent.
 */
class SkyMusicLauncher(
    private val host: Activity,
    private val prefs: SharedPreferences,
    private val tell: (String) -> Unit
) {
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
        val chosen = request.service ?: preferred()
        val title = SkyMusicCommand.label(chosen)
        val pkg = packageName(chosen)
        val player = Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH).apply {
            setPackage(pkg)
            addCategory(Intent.CATEGORY_DEFAULT)
            putExtra(MediaStore.EXTRA_MEDIA_FOCUS, "vnd.android.cursor.item/*")
            putExtra(SearchManager.QUERY, request.query)
        }
        val launched = try {
            host.startActivity(player)
            true
        } catch (_: ActivityNotFoundException) { false
        } catch (_: SecurityException) { false
        } catch (_: IllegalArgumentException) { false }
        if (launched) {
            tell("Le pedí a $title que reproduzca «${request.query}». " +
                "Verificá en la aplicación si comenzó a sonar.")
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
            tell("Abrí la búsqueda de «${request.query}» en $title. " +
                "Tocá la canción para reproducirla.")
        } catch (_: Exception) {
            tell("No encontré una aplicación compatible para abrir música.")
        }
    }
}
