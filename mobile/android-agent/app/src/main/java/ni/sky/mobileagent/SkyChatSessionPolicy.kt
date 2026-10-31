package ni.sky.mobileagent

/**
 * A fresh conversation is a non-destructive view/context boundary.
 * Every completed exchange remains in the private SQLite archive and can
 * still be accessed from the full History browser.
 */
internal object SkyChatSessionPolicy {
    fun visible(entryId: Long, afterId: Long): Boolean =
        entryId > afterId.coerceAtLeast(0L)

    /** The highest persisted ID becomes the exclusive boundary for a new chat. */
    fun newBoundary(latestSavedId: Long?): Long =
        (latestSavedId ?: 0L).coerceAtLeast(0L)
}
