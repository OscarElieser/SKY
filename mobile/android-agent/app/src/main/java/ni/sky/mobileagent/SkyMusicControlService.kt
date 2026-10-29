package ni.sky.mobileagent

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.media.AudioManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Toast
import java.text.Normalizer
import java.util.Locale

/**
 * ONLY a user-requested music command, in one of three authorized players.
 * Runs an explicit, short, deterministic search -> exact title -> click sequence.
 * Never reads chats, sends messages, taps ads, or executes arbitrary model plans.
 *
 * Opt-in accessibility access must be enabled manually in Android settings.
 * App interfaces vary; failures are reported instead of pretending playback.
 */
class SkyMusicControlService : AccessibilityService() {
    private enum class Phase { OPEN_SEARCH, FILL_SEARCH, SUBMIT_SEARCH, FIND_SONG, VERIFY_PLAY }
    private data class Pending(
        val packageName: String,
        val query: String,
        val expiresAt: Long,
        var phase: Phase = Phase.OPEN_SEARCH,
        var changedAt: Long = 0L,
        var selectedAt: Long = 0L,
        var lastActionAt: Long = 0L,
        val callback: (String) -> Unit
    )

    companion object {
        private const val MAX_RUNTIME_MS = 35000L
        private val PACKAGES = setOf(
            "com.google.android.apps.youtube.music",
            "com.google.android.youtube",
            "com.spotify.music"
        )
        @Volatile private var instance: SkyMusicControlService? = null
        @Volatile private var pending: Pending? = null

        fun enabled(): Boolean {
            val service = instance ?: return false
            return service.getSharedPreferences("sky_music_access", Context.MODE_PRIVATE)
                .getBoolean("consent", false)
        }

        @Synchronized fun arm(
            pkg: String, title: String, callback: (String) -> Unit
        ): Boolean {
            val service = instance ?: return false
            if (!enabled() || pkg !in PACKAGES || title.trim().length !in 2..180 ||
                title.contains('\n')) return false
            val now = SystemClock.elapsedRealtime()
            pending = Pending(pkg, title.trim(), now + MAX_RUNTIME_MS, callback = callback)
            service.handler.post { service.checkPending() }
            return true
        }

        @Synchronized fun cancelPending() {
            pending = null
        }
    }

    private val handler = Handler(Looper.getMainLooper())
    private val evaluate = Runnable { checkPending() }

    private fun notifyResult(request: Pending, text: String) {
        synchronized(Companion) {
            if (pending !== request) return
            pending = null
        }
        handler.removeCallbacks(evaluate)
        request.callback(text)
        Toast.makeText(applicationContext, text, Toast.LENGTH_LONG).show()
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val request = pending ?: return
        if (event?.packageName?.toString() != request.packageName) return
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED ||
            event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||
            event.eventType == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED) {
            handler.removeCallbacks(evaluate)
            handler.postDelayed(evaluate, 220)
        }
    }

    private fun normalize(text: String): String = Normalizer
        .normalize(text.lowercase(Locale.ROOT), Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "")
        .replace(Regex("[^a-z0-9]+"), " ")
        .replace(Regex("\\s+"), " ")
        .trim()

    private fun nodes(root: AccessibilityNodeInfo): List<AccessibilityNodeInfo> {
        val output = ArrayList<AccessibilityNodeInfo>()
        val queue = ArrayDeque<AccessibilityNodeInfo>()
        queue.add(root)
        while (queue.isNotEmpty() && output.size < 240) {
            val current = queue.removeFirst()
            output.add(current)
            for (i in 0 until minOf(current.childCount, 32)) {
                current.getChild(i)?.let { queue.add(it) }
            }
        }
        return output
    }

    private fun label(node: AccessibilityNodeInfo): String =
        listOfNotNull(node.text?.toString(), node.contentDescription?.toString())
            .joinToString(" ").trim()

    private fun click(node: AccessibilityNodeInfo): Boolean {
        var target: AccessibilityNodeInfo? = node
        repeat(5) {
            val item = target ?: return false
            if (item.isClickable && item.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
            target = item.parent
        }
        return false
    }

    private fun findSearchButton(items: List<AccessibilityNodeInfo>): AccessibilityNodeInfo? {
        return items.firstOrNull { node ->
            val t = normalize(label(node))
            (t == "search" || t == "buscar" || t == "busqueda" ||
                t == "search youtube music" || t == "buscar en youtube music") &&
                (node.isClickable || node.parent?.isClickable == true)
        }
    }

    private fun editable(items: List<AccessibilityNodeInfo>): AccessibilityNodeInfo? =
        items.firstOrNull { it.isEditable && !it.isPassword && it.isEnabled }

    private fun matchingSong(items: List<AccessibilityNodeInfo>, query: String): AccessibilityNodeInfo? {
        val expected = normalize(query)
        if (expected.length < 2) return null
        // Match text nodes to the complete requested title, never arbitrary
        // first-result positions, unrelated content or sponsored rows.
        return items.firstOrNull { node ->
            !node.isEditable && node.isVisibleToUser &&
                normalize(label(node)) == expected &&
                (node.isClickable || node.parent?.isClickable == true ||
                    node.parent?.parent?.isClickable == true)
        }
    }

    private fun checkPending() {
        val request = pending ?: return
        val now = SystemClock.elapsedRealtime()
        if (now > request.expiresAt) {
            notifyResult(request,
                "No logré iniciar «${request.query}» automáticamente. El reproductor no mostró un resultado verificable.")
            return
        }
        val root = rootInActiveWindow
        if (root == null || root.packageName?.toString() != request.packageName) {
            handler.postDelayed(evaluate, 400)
            return
        }
        val items = nodes(root)
        if (now - request.lastActionAt < 550) {
            handler.postDelayed(evaluate, 300)
            return
        }
        if (request.phase == Phase.VERIFY_PLAY) {
            val audio = getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val active = audio.isMusicActive
            // A visible song title combined with active multimedia playback
            // is a stronger signal than merely launching another app.
            val titleVisible = items.any { normalize(label(it)).contains(normalize(request.query)) }
            if (active && titleVisible) {
                notifyResult(request, "SKY detectó reproducción activa de «${request.query}» en el reproductor.")
                return
            }
            if (now - request.selectedAt > 9000) {
                notifyResult(request, "Seleccioné «${request.query}», pero Android no confirmó que esté sonando.")
                return
            }
            handler.postDelayed(evaluate, 500)
            return
        }
        // If the title is already in a results list, skip searching again.
        val song = matchingSong(items, request.query)
        if (song != null && request.phase != Phase.FILL_SEARCH &&
            request.phase != Phase.SUBMIT_SEARCH) {
            if (click(song)) {
                request.phase = Phase.VERIFY_PLAY
                request.selectedAt = now
                request.lastActionAt = now
                handler.postDelayed(evaluate, 750)
                return
            }
        }
        when (request.phase) {
            Phase.OPEN_SEARCH -> {
                val field = editable(items)
                if (field != null) {
                    request.phase = Phase.FILL_SEARCH
                } else {
                    val search = findSearchButton(items)
                    if (search != null && click(search)) {
                        request.phase = Phase.FILL_SEARCH
                        request.lastActionAt = now
                    }
                }
            }
            Phase.FILL_SEARCH -> {
                val field = editable(items)
                if (field != null && field.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,
                        Bundle().apply {
                            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                                request.query)
                        })) {
                    request.phase = Phase.SUBMIT_SEARCH
                    request.changedAt = now
                    request.lastActionAt = now
                }
            }
            Phase.SUBMIT_SEARCH -> {
                val field = editable(items)
                if (field != null && field.performAction(
                        AccessibilityNodeInfo.AccessibilityAction.ACTION_IME_ENTER.id)) {
                    request.phase = Phase.FIND_SONG
                    request.lastActionAt = now
                } else if (now - request.changedAt > 900) {
                    // Some players show live results as soon as text is entered.
                    request.phase = Phase.FIND_SONG
                }
            }
            Phase.FIND_SONG -> {
                val result = matchingSong(items, request.query)
                if (result != null && click(result)) {
                    request.phase = Phase.VERIFY_PLAY
                    request.selectedAt = now
                    request.lastActionAt = now
                }
            }
            Phase.VERIFY_PLAY -> Unit
        }
        handler.removeCallbacks(evaluate)
        handler.postDelayed(evaluate, 500)
    }

    override fun onInterrupt() {
        cancelPending()
        handler.removeCallbacks(evaluate)
    }

    override fun onDestroy() {
        cancelPending()
        instance = null
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
