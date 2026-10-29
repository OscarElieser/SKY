package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyEmotionLexiconTest {
    @Test fun interpretaOrdenesConYSinTildes() {
        assertEquals(SkyEmotionLexicon.Mood.CRYING, SkyEmotionLexicon.requested("Llorá"))
        assertEquals(SkyEmotionLexicon.Mood.ANGRY, SkyEmotionLexicon.requested("Enojada"))
        assertEquals(SkyEmotionLexicon.Mood.SHY, SkyEmotionLexicon.requested("Vergüenza"))
        assertEquals(SkyEmotionLexicon.Mood.SLEEPY, SkyEmotionLexicon.requested("Dormida"))
        assertEquals(SkyEmotionLexicon.Mood.HAPPY, SkyEmotionLexicon.requested("Sonríe"))
    }

    @Test fun conversacionSinGestoForzado() {
        assertNull(SkyEmotionLexicon.dialogue("¿Cuántos archivos puedo adjuntar?"))
        assertEquals(SkyEmotionLexicon.Mood.HAPPY, SkyEmotionLexicon.dialogue("¡Hola!"))
        assertEquals(SkyEmotionLexicon.Mood.SAD, SkyEmotionLexicon.dialogue("Lo siento mucho"))
        assertEquals(SkyEmotionLexicon.Mood.LOVING, SkyEmotionLexicon.dialogue("Te quiero"))
    }

    @Test fun mensajeParaCadaExpresion() {
        SkyEmotionLexicon.Mood.values().forEach {
            assertFalse(SkyEmotionLexicon.message(it).isBlank())
        }
    }
}
