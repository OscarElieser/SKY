package ni.sky.mobileagent

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Tests de protocolo Android sin hacer llamadas cobrables ni usar llaves reales.
 * No sustituyen las pruebas físicas de imágenes y videos con una cuenta autorizada.
 */
@RunWith(AndroidJUnit4::class)
class SkyRealMediaProtocolTest {
    @Test fun imageRequestTargetsRealImageModel() {
        val json = SkyGeneratedImage.requestPayload("Una fotografía artística de Managua al amanecer", "16:9")
        assertEquals("16:9",
            json.getJSONObject("generationConfig").getJSONObject("imageConfig")
                .getString("aspectRatio"))
        assertEquals("IMAGE",
            json.getJSONObject("generationConfig").getJSONArray("responseModalities")
                .getString(0))
        assertTrue(SkyGeneratedImage.ENDPOINT.contains("generativelanguage.googleapis.com"))
        assertTrue(SkyGeneratedImage.ENDPOINT.contains("gemini-nano-banana-2.1"))
    }

    @Test fun imageDoesNotCreateFakeDataWhenEmpty() {
        try {
            SkyGeneratedImage.parse(JSONObject())
            throw AssertionError("Nunca devolver una imagen vacía como si fuera real")
        } catch (expected: IllegalStateException) {
            assertTrue(expected.message.orEmpty().contains("no devolvió una imagen"))
        }
    }

    @Test fun paidVideoRequestRequiresRealVideoProvider() {
        val json = SkyAiVideo.payload(
            "Plano cinematográfico de un lago de Nicaragua con nubes al amanecer.", "9:16")
        assertEquals(SkyAiVideo.MODEL, json.getString("model"))
        assertEquals("video", json.getJSONObject("response_format").getString("type"))
        assertEquals("360p", json.getJSONObject("response_format").getString("resolution"))
    }

    @Test fun paidVideoRefusesTextResponse() {
        try {
            SkyAiVideo.videoBytes(JSONObject().put("output_text", "imagen imaginaria"))
            throw AssertionError("Nunca devolver un vídeo simulado")
        } catch (expected: IllegalStateException) {
            assertTrue(expected.message.orEmpty().contains("no entregó un video"))
        }
    }
}
