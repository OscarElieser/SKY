package ni.sky.mobileagent

/**
 * Public standard SKY APK: no AccessibilityService or screen-reading access.
 * Music still uses documented Android media intents and player controls.
 * The experimental opt-in UI controller remains isolated in assistive flavor.
 */
object SkyMusicControlService {
    fun enabled(): Boolean = false
    fun arm(pkg: String, title: String, callback: (String) -> Unit): Boolean = false
    fun cancelPending() = Unit
}
