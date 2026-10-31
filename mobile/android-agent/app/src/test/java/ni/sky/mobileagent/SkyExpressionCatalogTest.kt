package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyExpressionCatalogTest {
    @Test fun originalExpressionsExceedOneHundredAndAreDistinct() {
        val types = SkyExpressionCatalog.Kind.entries
        val all = types.flatMap { SkyExpressionCatalog.variants(it) }
        assertEquals(10, types.size)
        assertTrue("Debe haber más de 100 expresiones", all.size > 100)
        assertEquals(all.size, SkyExpressionCatalog.total)
        assertEquals("No repetir textos", all.size, all.toSet().size)
        assertTrue(all.all { it.isNotBlank() && it.length < 320 })
        assertTrue(types.all { SkyExpressionCatalog.count(it) >= 12 })
    }

    @Test fun naturalRequestsRouteToTheirCategoriesWithoutNetwork() {
        assertEquals(SkyExpressionCatalog.Kind.SALUDO,
            SkyExpressionCatalog.requested("¡Hola, SKY!"))
        assertEquals(SkyExpressionCatalog.Kind.REFRAN,
            SkyExpressionCatalog.requested("SKY, decime un refrán"))
        assertEquals(SkyExpressionCatalog.Kind.TRABALENGUAS,
            SkyExpressionCatalog.requested("Dime un trabalenguas"))
        assertEquals(SkyExpressionCatalog.Kind.MOTIVACION,
            SkyExpressionCatalog.requested("Motívame"))
        assertEquals(SkyExpressionCatalog.Kind.ADIVINANZA,
            SkyExpressionCatalog.requested("Una adivinanza"))
        assertEquals(SkyExpressionCatalog.Kind.ESTUDIO,
            SkyExpressionCatalog.requested("Consejo para estudiar"))
    }

    @Test fun professionalTasksAreNotHijackedByChitchat() {
        val analytical = listOf(
            "Redacta una tesis doctoral con hipótesis y bibliografía",
            "Escribe un programa que salude al usuario",
            "Investiga el origen del refrán en la literatura",
            "Dame 20 chistes sobre teoría matemática con análisis cultural",
            "Ayúdame a diseñar una aplicación Android en Kotlin"
        )
        for (question in analytical) {
            assertNull(question, SkyExpressionCatalog.requested(question))
        }
    }

    @Test fun greetingsRotateOnlyWhenActuallyRequested() {
        assertTrue(SkyLocalConversation.handles("Hola"))
        val a = SkyLocalConversation.reply("Hola")
        assertTrue(SkyLocalConversation.handles("Hola"))
        val b = SkyLocalConversation.reply("Hola")
        assertNotEquals(a, b)
    }

    @Test fun companionUsesCatalogAndStillHonorsSafetyBoundaries() {
        val brain = SkyCompanionBrain()
        assertTrue(brain.answer("SKY contame un chiste")!!.spoken.isNotBlank())
        assertTrue(brain.answer("SKY decime un trabalenguas")!!.spoken.isNotBlank())
        assertTrue(brain.answer("SKY otra reflexión")!!.spoken.isNotBlank())
        assertNull(brain.answer("Hazme una investigación académica completa"))
    }
}
