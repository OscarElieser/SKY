package ni.sky.mobileagent
import org.junit.Assert.assertEquals
import org.junit.Test
class SkyActionEvidenceTest {
    @Test fun dispatchedIntentIsNeverRecordedAsCompleted() {
        assertEquals("ENVIADA_SIN_VERIFICAR", SkyActionEvidence.normalized("SENT"))
        assertEquals("ENVIADA_SIN_VERIFICAR", SkyActionEvidence.normalized("LAUNCHED"))
    }
    @Test fun onlyVerifiedLocalWriteIsMarkedVerified() {
        assertEquals("VERIFICADA_LOCAL", SkyActionEvidence.normalized("VERIFIED_LOCAL"))
        assertEquals("FALLIDA", SkyActionEvidence.normalized("FAILED"))
        assertEquals("RECHAZADA", SkyActionEvidence.normalized("REJECTED"))
        assertEquals("ESTADO_DESCONOCIDO", SkyActionEvidence.normalized("SUCCESS"))
    }
}
