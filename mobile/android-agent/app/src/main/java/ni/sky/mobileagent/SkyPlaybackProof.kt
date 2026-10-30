package ni.sky.mobileagent

import android.app.NotificationManager
import android.content.ComponentName
import android.content.Context
import android.media.MediaMetadata
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.Build
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.text.Normalizer
import java.util.Locale

/**
 * Only checks the exact requested title, authorized player and PLAYING state.
 * A media session is Android evidence of playback, not proof of audible output.
 * Other apps' session data are NEVER logged, uploaded or persisted.
 */
internal object SkyPlaybackProofRules {
    val players = setOf("com.spotify.music", "com.google.android.youtube",
        "com.google.android.apps.youtube.music")

    fun normalized(input: String): String = Normalizer
        .normalize(input.lowercase(Locale.ROOT), Normalizer.Form.NFD)
        .replace(Regex("""\p{M}+"""), "")
        .replace(Regex("""[^a-z0-9]+"""), " ")
        .trim().replace(Regex("""\s+"""), " ")

    fun sameTrack(request: String, title: String): Boolean {
        val requested = normalized(request)
        val actual = normalized(title)
        if (actual.length < 4 || requested.length < 4) return false
        if (actual == requested) return true
        // "November Rain de Guns N Roses" is valid when the player metadata
        // reports the title "November Rain". Don't accept unrelated titles.
        return requested.startsWith("$actual de ") || requested.startsWith("$actual by ")
    }

    fun verified(request: String, title: String, actualPackage: String,
                 expectedPackage: String, playbackState: Int): Boolean =
        expectedPackage in players && actualPackage == expectedPackage &&
            playbackState == PlaybackState.STATE_PLAYING && sameTrack(request, title)
}

/**
 * Consent-bound listener for Android's MediaSessionManager.
 * It deliberately ignores notifications and their contents.
 * Android grants broader notification access at the OS level; the user
 * must enable/revoke that access manually in Settings.
 */
class SkyPlaybackProofListener : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification?) = Unit
    override fun onNotificationRemoved(sbn: StatusBarNotification?) = Unit
}

internal object SkyPlaybackProof {
    private fun component(context: Context) =
        ComponentName(context, SkyPlaybackProofListener::class.java)

    fun available(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < 27) return false
        return runCatching {
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE)
                as NotificationManager
            manager.isNotificationListenerAccessGranted(component(context))
        }.getOrDefault(false)
    }

    fun playing(context: Context, playerPackage: String, requestedTrack: String): Boolean {
        if (!available(context) || playerPackage !in SkyPlaybackProofRules.players) return false
        return runCatching {
            val sessions = (context.getSystemService(Context.MEDIA_SESSION_SERVICE)
                as MediaSessionManager).getActiveSessions(component(context))
            sessions.any { session ->
                if (session.packageName != playerPackage) return@any false
                val title = session.metadata?.getString(MediaMetadata.METADATA_KEY_TITLE)
                    ?: session.metadata?.getString(MediaMetadata.METADATA_KEY_DISPLAY_TITLE)
                    ?: return@any false
                SkyPlaybackProofRules.verified(requestedTrack, title,
                    session.packageName, playerPackage,
                    session.playbackState?.state ?: PlaybackState.STATE_NONE)
            }
        }.getOrDefault(false)
    }
}
