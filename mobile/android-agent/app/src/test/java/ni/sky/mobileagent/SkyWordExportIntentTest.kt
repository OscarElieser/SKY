package ni.sky.mobileagent

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SkyWordExportIntentTest {
    @Test fun exportPreviousAnswerNotInstructionsForCopyPaste() {
        assertTrue(SkyWordExportIntent.wantsExistingWord("Necesito descargar el archivo Word"))
        assertTrue(SkyWordExportIntent.wantsExistingWord(
            "Pero quiero que lo haga tú me brindes el archivo Word"))
        assertTrue(SkyWordExportIntent.wantsExistingWord("Dame el DOCX para guardarlo"))
        assertFalse(SkyWordExportIntent.wantsExistingWord(
            "¿Cómo descargar archivos de Word desde internet?"))
        assertFalse(SkyWordExportIntent.wantsExistingWord(
            "Explica la historia de Microsoft Word"))
    }

    @Test fun longAcademicBriefStillAsksForRealWordCreation() {
        val brief = ("Comité académico de metodología, estadística y redacción. " +
            "Define el problema, las preguntas, las hipótesis, la muestra, " +
            "los instrumentos y una hoja de ruta por semanas. ").repeat(12) +
            "Ayúdame a redactar esta tesis en un documento Word."
        assertTrue(brief.length > 600)
        assertTrue(SkyWordExportIntent.wantsNewWord(brief))
        assertFalse(SkyWordExportIntent.wantsExistingWord(brief))
    }

    @Test fun newDocumentIsGeneratedBeforeExport() {
        assertTrue(SkyWordExportIntent.wantsNewWord(
            "SKY crea un documento Word sobre los volcanes de Nicaragua"))
        assertTrue(SkyWordExportIntent.wantsNewWord(
            "Redacta un archivo docx con la planificación didáctica"))
        assertFalse(SkyWordExportIntent.wantsNewWord(
            "¿Cómo crear un documento Word?"))
        assertFalse(SkyWordExportIntent.wantsNewWord(
            "Necesito descargar el archivo Word"))
    }
}
