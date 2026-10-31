package ni.sky.mobileagent

import android.content.Context
import android.media.AudioManager

/**
 * Read-only Android multimedia-volume checks. A positive media level is NOT
 * proof that YouTube/Spotify is audible: the video itself, audio route,
 * Bluetooth output or headphones can still be silent.
 */
internal object SkyMusicAudioRules {
    enum class State { ZERO_VOLUME, MUTED, LEVEL_PRESENT, UNAVAILABLE }

    fun state(level: Int?, muted: Boolean?): State = when {
        muted == true -> State.MUTED
        level == 0 -> State.ZERO_VOLUME
        level != null && level > 0 -> State.LEVEL_PRESENT
        else -> State.UNAVAILABLE
    }

    fun needsAttention(level: Int?, muted: Boolean?): Boolean =
        state(level, muted) in setOf(State.ZERO_VOLUME, State.MUTED)
}

internal object SkyMusicAudioCheck {
    data class Snapshot(
        val level: Int?,
        val maximum: Int?,
        val muted: Boolean?,
        val fixed: Boolean?
    ) {
        val state: SkyMusicAudioRules.State
            get() = SkyMusicAudioRules.state(level, muted)

        val silentBySystemSettings: Boolean
            get() = SkyMusicAudioRules.needsAttention(level, muted)

        fun evidence(): String {
            val amount = if (level != null && maximum != null)
                "volumen multimedia $level/$maximum" else "volumen multimedia no comprobable"
            val mute = when (muted) {
                true -> "Android informa silencio multimedia"
                false -> "Android no informa silencio multimedia"
                null -> "estado de silencio no comprobable"
            }
            return "$amount; $mute; audio audible no medido"
        }

        fun guidance(): String = when (state) {
            SkyMusicAudioRules.State.ZERO_VOLUME ->
                "Android tiene el volumen multimedia en cero. Revisá el control de volumen."
            SkyMusicAudioRules.State.MUTED ->
                "Android informa que el audio multimedia está silenciado. Revisá el control de volumen."
            SkyMusicAudioRules.State.LEVEL_PRESENT ->
                "El volumen multimedia tiene nivel, pero no puedo comprobar el sonido. " +
                    "Revisá si el video está silenciado o el audio sale por Bluetooth o auriculares."
            SkyMusicAudioRules.State.UNAVAILABLE ->
                "No pude consultar el volumen multimedia. Revisá el volumen, el silencio " +
                    "del video y la salida de audio de Android."
        }
    }

    fun read(context: Context): Snapshot {
        val audio = runCatching {
            context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        }.getOrNull() ?: return Snapshot(null, null, null, null)
        val stream = AudioManager.STREAM_MUSIC
        return Snapshot(
            level = runCatching { audio.getStreamVolume(stream) }.getOrNull(),
            maximum = runCatching { audio.getStreamMaxVolume(stream) }.getOrNull(),
            muted = runCatching { audio.isStreamMute(stream) }.getOrNull(),
            fixed = runCatching { audio.isVolumeFixed }.getOrNull()
        )
    }

    /** Show Android's standard volume panel only when muted/zero.
     * The owner chooses the actual volume; SKY never raises it automatically.
     */
    fun offerVolumePanel(context: Context, snapshot: Snapshot) {
        if (!snapshot.silentBySystemSettings || snapshot.fixed == true) return
        runCatching {
            val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            audio.adjustStreamVolume(AudioManager.STREAM_MUSIC,
                AudioManager.ADJUST_SAME, AudioManager.FLAG_SHOW_UI)
        }
    }
}
