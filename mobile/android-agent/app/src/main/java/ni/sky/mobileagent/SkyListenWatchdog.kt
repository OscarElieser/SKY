package ni.sky.mobileagent

/**
 * Detects a recognizer cycle that has remained stuck without onResults/onError.
 * This is best-effort recovery, never a guarantee that Android keeps the
 * microphone active with the screen locked or the process suspended.
 */
internal object SkyListenWatchdog {
    const val MAX_CYCLE_MS = 90_000L

    fun needsRecovery(serviceActive: Boolean, recognizerListening: Boolean,
                      speechSuspended: Boolean, cycleAgeMs: Long): Boolean =
        serviceActive && recognizerListening && !speechSuspended &&
            cycleAgeMs >= MAX_CYCLE_MS
}
