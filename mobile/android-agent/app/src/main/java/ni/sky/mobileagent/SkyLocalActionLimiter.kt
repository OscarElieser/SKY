package ni.sky.mobileagent

/**
 * Último límite local contra repetición accidental de órdenes por voz,
 * pulsaciones múltiples y bucles de agentes. Funciona sin red ni permisos.
 *
 * Un contador en el teléfono no sustituye límites centralizados del backend.
 */
class SkyLocalActionLimiter(
    private val nowMs: () -> Long = { System.nanoTime() / 1_000_000L },
    private val maxPerMinute: Int = 30,
    private val duplicateWindowMs: Long = 1500L
) {
    private val recent = ArrayDeque<Long>()
    private var lastAction = ""
    private var lastAt = Long.MIN_VALUE

    @Synchronized
    fun allow(action: String): Boolean {
        if (action.isBlank() || action.length > 180) return false
        val now = nowMs()
        // El tiempo monotónico evita que los cambios de reloj alteren el límite.
        while (recent.isNotEmpty() && now - recent.first() >= 60_000L) {
            recent.removeFirst()
        }
        if (recent.size >= maxPerMinute) return false
        if (action == lastAction && lastAt != Long.MIN_VALUE &&
            now >= lastAt && now - lastAt < duplicateWindowMs) return false
        recent.addLast(now)
        lastAction = action
        lastAt = now
        return true
    }
}
