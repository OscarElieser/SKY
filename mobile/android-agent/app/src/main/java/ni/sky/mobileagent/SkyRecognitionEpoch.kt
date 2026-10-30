package ni.sky.mobileagent

/**
 * Main-thread only guard for Android SpeechRecognizer callbacks.
 *
 * SpeechRecognizer.cancel()/destroy() may deliver a late onError or onResults.
 * Those callbacks must never change the state of a newer recognition session.
 * This guard owns no audio, raw transcript, network service or device permission.
 */
internal class SkyRecognitionEpoch {
    private var current: Long = 0L

    /** Retire any recognizer before cancel/destroy so its late callbacks are ignored. */
    fun invalidate() {
        current++
    }

    /** The recognizer must call begin() only after the previous one is retired. */
    fun begin(): Long {
        current++
        return current
    }

    fun accepts(epoch: Long, listening: Boolean): Boolean =
        listening && epoch == current
}
