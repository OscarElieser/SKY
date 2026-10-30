package ni.sky.mobileagent

/**
 * Only the latest queued TTS utterance may resume microphone recognition.
 * Called from the Service's main-thread Handler, not from Android's TTS worker.
 * No speech content is retained here.
 */
internal class SkySpeechTurnGuard {
    private var nextId = 0L
    private var active: String? = null

    fun begin(): String {
        val id = "sky-service-" + (++nextId)
        active = id
        return id
    }

    fun invalidate() {
        active = null
    }

    /** Returns true once for the currently active utterance only. */
    fun finish(utteranceId: String?): Boolean {
        if (utteranceId == null || utteranceId != active) return false
        active = null
        return true
    }
}
