package ni.sky.mobileagent

/**
 * Standard distribution: deliberately NO Android AccessibilityService.
 * Safe no-op compatibility surface for the optional assistive feature.
 * The actual implementation belongs exclusively to the assistive variant.
 */
object SkyTextAssistService {
    fun enabled(): Boolean = false
    fun arm(pkg: String, text: String): Boolean = false
    fun cancelPending() = Unit
}
